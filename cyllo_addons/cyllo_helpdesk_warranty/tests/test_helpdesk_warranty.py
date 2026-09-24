# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestHelpdeskWarranty(TransactionCase):
    """Tests for cyllo_helpdesk_warranty — warranty-status bridge on
    helpdesk.ticket. Covers:
    - _compute_warranty_status logic (all four outcome paths)
    - use_product_warranty relay from helpdesk.team
    - is_under_warranty_evaluation relay from sale.order.line
    - Recompute when sale_order_line_id or use_product_warranty changes
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Company / Users ──────────────────────────────────────────────
        cls.company = cls.env.ref('base.main_company')

        # ── Partner / Customer ───────────────────────────────────────────
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Warranty Customer',
            'company_type': 'person',
        })

        # ── Product with warranty ────────────────────────────────────────
        cls.product = cls.env['product.product'].create({
            'name': 'Warranty Product',
            'type': 'consu',
        })

        # ── Helpdesk Stage ───────────────────────────────────────────────
        cls.stage = cls.env['helpdesk.stage'].search([], limit=1)
        if not cls.stage:
            cls.stage = cls.env['helpdesk.stage'].create({
                'name': 'New',
                'sequence': 1,
                'is_closed': False,
            })

        # ── Helpdesk Team with warranty enabled ──────────────────────────
        cls.team_warranty = cls.env['helpdesk.team'].create({
            'name': 'Warranty Team',
            'use_product_warranty': True,
        })

        # ── Helpdesk Team without warranty ───────────────────────────────
        cls.team_no_warranty = cls.env['helpdesk.team'].create({
            'name': 'No Warranty Team',
            'use_product_warranty': False,
        })

        # ── Sale Order ───────────────────────────────────────────────────
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'state': 'sale',
        })

    # ── Helpers ──────────────────────────────────────────────────────────

    def _make_order_line(self, expiration_date=None):
        """Create a sale.order.line and optionally set warranty_expiration_date
        directly (bypasses compute for deterministic testing)."""
        line = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'price_unit': 100.0,
        })
        if expiration_date is not None:
            # Write directly so tests are date-deterministic
            line.write({'warranty_expiration_date': expiration_date})
        return line

    def _make_ticket(self, team, sale_order_line=None):
        """Create a helpdesk.ticket linked to *team* and optionally to a
        sale.order.line."""
        vals = {
            'name': 'Test Ticket',
            'team_id': team.id,
            'customer_id': self.partner.id,
            'stage_id': self.stage.id,
        }
        if sale_order_line:
            vals['sale_order_id'] = sale_order_line.order_id.id
            vals['sale_order_line_id'] = sale_order_line.id
        return self.env['helpdesk.ticket'].create(vals)

    # ── use_product_warranty relay ────────────────────────────────────────

    def test_use_product_warranty_relayed_from_team_true(self):
        """use_product_warranty reflects team_id.use_product_warranty = True."""
        ticket = self._make_ticket(self.team_warranty)
        self.assertTrue(
            ticket.use_product_warranty,
            "use_product_warranty should be True when team has warranty enabled.",
        )

    def test_use_product_warranty_relayed_from_team_false(self):
        """use_product_warranty reflects team_id.use_product_warranty = False."""
        ticket = self._make_ticket(self.team_no_warranty)
        self.assertFalse(
            ticket.use_product_warranty,
            "use_product_warranty should be False when team has warranty disabled.",
        )

    def test_use_product_warranty_updates_on_team_change(self):
        """use_product_warranty re-evaluates when team_id is changed."""
        ticket = self._make_ticket(self.team_warranty)
        self.assertTrue(ticket.use_product_warranty)

        ticket.team_id = self.team_no_warranty
        self.assertFalse(
            ticket.use_product_warranty,
            "use_product_warranty must update when team changes to one without warranty.",
        )

    # ── warranty_status: False path ───────────────────────────────────────

    def test_warranty_status_false_when_warranty_disabled(self):
        """warranty_status is False when use_product_warranty is False,
        even if an order line exists."""
        future_date = fields.Date.today() + timedelta(days=30)
        line = self._make_order_line(expiration_date=future_date)
        ticket = self._make_ticket(self.team_no_warranty, sale_order_line=line)

        self.assertFalse(
            ticket.warranty_status,
            "warranty_status must be False when the team does not use product warranty.",
        )

    def test_warranty_status_false_when_no_order_line(self):
        """warranty_status is False when warranty is enabled but no order line
        is linked."""
        ticket = self._make_ticket(self.team_warranty)
        self.assertFalse(
            ticket.warranty_status,
            "warranty_status must be False when sale_order_line_id is not set.",
        )

    # ── warranty_status: 'none' path ──────────────────────────────────────

    def test_warranty_status_none_when_no_expiration_date(self):
        """warranty_status is 'none' when order line has no expiration date."""
        line = self._make_order_line(expiration_date=False)
        ticket = self._make_ticket(self.team_warranty, sale_order_line=line)

        self.assertEqual(
            ticket.warranty_status,
            'none',
            "warranty_status should be 'none' when warranty_expiration_date is absent.",
        )

    # ── warranty_status: 'under_warranty' path ────────────────────────────

    def test_warranty_status_under_warranty_when_future_expiration(self):
        """warranty_status is 'under_warranty' when expiration is in the future."""
        future_date = fields.Date.today() + timedelta(days=90)
        line = self._make_order_line(expiration_date=future_date)
        ticket = self._make_ticket(self.team_warranty, sale_order_line=line)

        self.assertEqual(
            ticket.warranty_status,
            'under_warranty',
            "warranty_status should be 'under_warranty' for a future expiration date.",
        )

    def test_warranty_status_under_warranty_boundary_tomorrow(self):
        """warranty_status is 'under_warranty' when expiration is tomorrow
        (boundary: expiration_date > today must hold)."""
        tomorrow = fields.Date.today() + timedelta(days=1)
        line = self._make_order_line(expiration_date=tomorrow)
        ticket = self._make_ticket(self.team_warranty, sale_order_line=line)

        self.assertEqual(
            ticket.warranty_status,
            'under_warranty',
            "warranty_status should be 'under_warranty' when expiration is tomorrow.",
        )

    # ── warranty_status: 'expired' path ───────────────────────────────────

    def test_warranty_status_expired_when_past_expiration(self):
        """warranty_status is 'expired' when expiration date is in the past."""
        past_date = fields.Date.today() - timedelta(days=10)
        line = self._make_order_line(expiration_date=past_date)
        ticket = self._make_ticket(self.team_warranty, sale_order_line=line)

        self.assertEqual(
            ticket.warranty_status,
            'expired',
            "warranty_status should be 'expired' when expiration date has passed.",
        )

    def test_warranty_status_expired_boundary_today(self):
        """warranty_status is 'expired' when expiration equals today
        (boundary: condition is expiration_date > today, so today itself = expired)."""
        today = fields.Date.today()
        line = self._make_order_line(expiration_date=today)
        ticket = self._make_ticket(self.team_warranty, sale_order_line=line)

        self.assertEqual(
            ticket.warranty_status,
            'expired',
            "warranty_status should be 'expired' when expiration equals today.",
        )

    # ── Recompute on sale_order_line change ───────────────────────────────

    def test_warranty_status_recomputes_on_line_change(self):
        """warranty_status recomputes correctly when sale_order_line_id is
        swapped for one with a different expiration date."""
        future_date = fields.Date.today() + timedelta(days=60)
        past_date = fields.Date.today() - timedelta(days=5)

        line_future = self._make_order_line(expiration_date=future_date)
        line_past = self._make_order_line(expiration_date=past_date)

        ticket = self._make_ticket(self.team_warranty, sale_order_line=line_future)
        self.assertEqual(ticket.warranty_status, 'under_warranty')

        # Swap to the expired line
        ticket.sale_order_line_id = line_past
        self.assertEqual(
            ticket.warranty_status,
            'expired',
            "warranty_status must recompute to 'expired' after line is changed.",
        )

    def test_warranty_status_recomputes_on_line_removed(self):
        """warranty_status reverts to False when sale_order_line_id is cleared."""
        future_date = fields.Date.today() + timedelta(days=30)
        line = self._make_order_line(expiration_date=future_date)
        ticket = self._make_ticket(self.team_warranty, sale_order_line=line)
        self.assertEqual(ticket.warranty_status, 'under_warranty')

        ticket.sale_order_line_id = False
        self.assertFalse(
            ticket.warranty_status,
            "warranty_status must be False after sale_order_line_id is cleared.",
        )

    # ── is_under_warranty_evaluation relay ───────────────────────────────

    def test_is_under_warranty_evaluation_true_when_under_warranty(self):
        """is_under_warranty_evaluation relays True from a line that is under
        warranty (is_under_warranty = True on sale.order.line)."""
        future_date = fields.Date.today() + timedelta(days=30)
        line = self._make_order_line(expiration_date=future_date)
        ticket = self._make_ticket(self.team_warranty, sale_order_line=line)

        # is_under_warranty on the line drives the relay
        self.assertEqual(
            ticket.is_under_warranty_evaluation,
            line.is_under_warranty,
            "is_under_warranty_evaluation must relay sale_order_line_id.is_under_warranty.",
        )

    def test_is_under_warranty_evaluation_false_when_expired(self):
        """is_under_warranty_evaluation relays False from an expired line."""
        past_date = fields.Date.today() - timedelta(days=10)
        line = self._make_order_line(expiration_date=past_date)
        ticket = self._make_ticket(self.team_warranty, sale_order_line=line)

        self.assertFalse(
            ticket.is_under_warranty_evaluation,
            "is_under_warranty_evaluation should be False for an expired order line.",
        )

    def test_is_under_warranty_evaluation_false_when_no_line(self):
        """is_under_warranty_evaluation is False when no order line is set."""
        ticket = self._make_ticket(self.team_warranty)
        self.assertFalse(
            ticket.is_under_warranty_evaluation,
            "is_under_warranty_evaluation should be False when sale_order_line_id is empty.",
        )

    # ── Combined: toggle use_product_warranty at team level ──────────────

    def test_warranty_status_resets_when_team_warranty_toggled_off(self):
        """Disabling use_product_warranty on the team resets warranty_status
        to False even when a valid order line with future expiration is set."""
        future_date = fields.Date.today() + timedelta(days=45)
        line = self._make_order_line(expiration_date=future_date)
        ticket = self._make_ticket(self.team_warranty, sale_order_line=line)
        self.assertEqual(ticket.warranty_status, 'under_warranty')

        # Disable warranty at team level
        self.team_warranty.use_product_warranty = False
        ticket.invalidate_recordset()

        self.assertFalse(
            ticket.warranty_status,
            "warranty_status must be False after warranty is disabled on the team.",
        )

        # Restore for other tests
        self.team_warranty.use_product_warranty = True
