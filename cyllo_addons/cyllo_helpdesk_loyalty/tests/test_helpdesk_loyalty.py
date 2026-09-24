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
from odoo.tests import tagged, TransactionCase
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestHelpdeskLoyalty(TransactionCase):
    """Test suite for the Cyllo Helpdesk Loyalty integration features."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a customer partner
        cls.customer = cls.env['res.partner'].create({
            'name': 'Loyalty Test Customer',
            'email': 'loyalty@test.com',
        })

        # Create a helpdesk team
        cls.team = cls.env['helpdesk.team'].create({
            'name': 'Loyalty Support Team',
        })

        # Create a coupon loyalty program
        cls.coupon_program = cls.env['loyalty.program'].create({
            'name': 'Test Coupon Program',
            'program_type': 'coupons',
        })

        # Create a gift card loyalty program
        cls.gift_card_program = cls.env['loyalty.program'].create({
            'name': 'Test Gift Card Program',
            'program_type': 'gift_card',
        })

    def _create_ticket(self, **kwargs):
        """Helper to create a helpdesk ticket with sensible defaults."""
        vals = {
            'name': 'Test Loyalty Ticket',
            'team_id': self.team.id,
            'customer_id': self.customer.id,
        }
        vals.update(kwargs)
        return self.env['helpdesk.ticket'].create(vals)

    # ── Coupon / Gift Card count compute ────────────────────────────

    def test_compute_counts_empty(self):
        """Test that coupon and gift card counts are zero when none are linked."""
        ticket = self._create_ticket()
        self.assertEqual(ticket.coupon_count, 0)
        self.assertEqual(ticket.gift_card_count, 0)

    def test_compute_counts_with_coupons(self):
        """Test coupon count after linking coupons to the ticket."""
        ticket = self._create_ticket()
        coupon = self.env['loyalty.card'].create({
            'program_id': self.coupon_program.id,
            'partner_id': self.customer.id,
            'points': 1,
        })
        ticket.coupon_ids = [(4, coupon.id)]
        self.assertEqual(ticket.coupon_count, 1)

    def test_compute_counts_with_gift_cards(self):
        """Test gift card count after linking gift cards to the ticket."""
        ticket = self._create_ticket()
        gift_card = self.env['loyalty.card'].create({
            'program_id': self.gift_card_program.id,
            'partner_id': self.customer.id,
            'points': 50,
        })
        ticket.gift_card_ids = [(4, gift_card.id)]
        self.assertEqual(ticket.gift_card_count, 1)

    # ── action_create_coupon ────────────────────────────────────────

    def test_action_create_coupon_no_program_raises(self):
        """Test that action_create_coupon raises UserError when no coupon program exists."""
        ticket = self._create_ticket()
        # Archive ALL coupon programs (including demo data) so search won't find any
        all_coupon_programs = self.env['loyalty.program'].search(
            [('program_type', '=', 'coupons')])
        all_coupon_programs.active = False
        with self.assertRaises(UserError):
            ticket.action_create_coupon()
        # Re-activate for other tests
        all_coupon_programs.active = True

    def test_action_create_coupon_returns_wizard_action(self):
        """Test that action_create_coupon returns the generate wizard action with correct context."""
        ticket = self._create_ticket()
        action = ticket.action_create_coupon()

        expected_program = self.env['loyalty.program'].search([('program_type', '=', 'coupons')], limit=1)
        self.assertEqual(action['context']['default_program_id'], expected_program.id)
        self.assertEqual(action['context']['default_helpdesk_ticket_id'], ticket.id)
        self.assertEqual(action['context']['default_mode'], 'selected')
        self.assertIn(self.customer.id, action['context']['default_customer_ids'][0][2])

    def test_action_create_coupon_anonymous_mode_without_customer(self):
        """Test that action_create_coupon uses anonymous mode when no customer is set."""
        ticket = self._create_ticket(customer_id=False)
        action = ticket.action_create_coupon()

        self.assertEqual(action['context']['default_mode'], 'anonymous')

    # ── action_send_gift_card ───────────────────────────────────────

    def test_action_send_gift_card_no_program_raises(self):
        """Test that action_send_gift_card raises UserError when no gift card program exists."""
        ticket = self._create_ticket()
        # Archive ALL gift card programs (including demo data) so search won't find any
        all_gift_card_programs = self.env['loyalty.program'].search(
            [('program_type', '=', 'gift_card')])
        all_gift_card_programs.active = False
        with self.assertRaises(UserError):
            ticket.action_send_gift_card()
        # Re-activate for other tests
        all_gift_card_programs.active = True

    def test_action_send_gift_card_returns_wizard_action(self):
        """Test that action_send_gift_card returns the generate wizard action with correct context."""
        ticket = self._create_ticket()
        action = ticket.action_send_gift_card()

        expected_program = self.env['loyalty.program'].search([('program_type', '=', 'gift_card')], limit=1)
        self.assertEqual(action['context']['default_program_id'], expected_program.id)
        self.assertEqual(action['context']['default_helpdesk_ticket_id'], ticket.id)
        self.assertEqual(action['context']['default_mode'], 'selected')

    # ── action_view_coupons / gift_cards ────────────────────────────

    def test_action_view_coupons(self):
        """Test that action_view_coupons returns an action filtered by coupon IDs."""
        ticket = self._create_ticket()
        coupon = self.env['loyalty.card'].create({
            'program_id': self.coupon_program.id,
            'partner_id': self.customer.id,
            'points': 1,
        })
        ticket.coupon_ids = [(4, coupon.id)]
        action = ticket.action_view_coupons()

        self.assertEqual(action['domain'], [('id', 'in', [coupon.id])])
        self.assertEqual(action['view_mode'], 'list,form')

    def test_action_view_gift_cards(self):
        """Test that action_view_gift_cards returns an action filtered by gift card IDs."""
        ticket = self._create_ticket()
        gift_card = self.env['loyalty.card'].create({
            'program_id': self.gift_card_program.id,
            'partner_id': self.customer.id,
            'points': 50,
        })
        ticket.gift_card_ids = [(4, gift_card.id)]
        action = ticket.action_view_gift_cards()

        self.assertEqual(action['domain'], [('id', 'in', [gift_card.id])])
        self.assertEqual(action['view_mode'], 'list,form')

    # ── LoyaltyCard create auto-link ────────────────────────────────

    def test_loyalty_card_create_autolinks_coupon_to_ticket(self):
        """Test that creating a loyalty.card with helpdesk_ticket_id auto-links it as a coupon."""
        ticket = self._create_ticket()
        coupon = self.env['loyalty.card'].create({
            'program_id': self.coupon_program.id,
            'partner_id': self.customer.id,
            'points': 1,
            'helpdesk_ticket_id': ticket.id,
        })
        self.assertIn(coupon, ticket.coupon_ids)

    def test_loyalty_card_create_autolinks_gift_card_to_ticket(self):
        """Test that creating a loyalty.card with helpdesk_ticket_id auto-links it as a gift card."""
        ticket = self._create_ticket()
        gift_card = self.env['loyalty.card'].create({
            'program_id': self.gift_card_program.id,
            'partner_id': self.customer.id,
            'points': 50,
            'helpdesk_ticket_id': ticket.id,
        })
        self.assertIn(gift_card, ticket.gift_card_ids)

    # ── LoyaltyGenerateWizard context injection ─────────────────────

    def test_generate_wizard_injects_ticket_id(self):
        """Test that _get_coupon_values passes helpdesk_ticket_id from context."""
        ticket = self._create_ticket()
        wizard = self.env['loyalty.generate.wizard'].with_context(
            default_helpdesk_ticket_id=ticket.id,
        ).create({
            'program_id': self.coupon_program.id,
            'mode': 'anonymous',
            'coupon_qty': 1,
        })
        values = wizard._get_coupon_values(self.customer)
        self.assertEqual(values.get('helpdesk_ticket_id'), ticket.id)

    def test_generate_wizard_no_ticket_id_in_context(self):
        """Test that _get_coupon_values works normally without helpdesk_ticket_id in context."""
        wizard = self.env['loyalty.generate.wizard'].create({
            'program_id': self.coupon_program.id,
            'mode': 'anonymous',
            'coupon_qty': 1,
        })
        values = wizard._get_coupon_values(self.customer)
        self.assertNotIn('helpdesk_ticket_id', values)
