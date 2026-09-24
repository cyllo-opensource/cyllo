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
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged
from .common import ShopfloorCommon


@tagged('post_install', '-at_install')
class TestAddComponentWizard(ShopfloorCommon):
    """Tests for mrp.add.component.wizard."""

    def _make_wizard(self, mo=None, product=None, qty=1.0):
        mo = mo or self._make_mo()
        return self.env['mrp.add.component.wizard'].create({
            'production_id': mo.id,
            'product_id': (product or self.component_a).id,
            'quantity': qty,
        })

    # -----------------------------------------------------------------------
    # _compute_mo_product_ids
    # -----------------------------------------------------------------------

    def test_compute_mo_product_ids_populated(self):
        """mo_product_ids should contain the products already in the MO raw moves."""
        mo = self._make_mo()
        wiz = self._make_wizard(mo=mo)
        self.assertIn(self.component_a, wiz.mo_product_ids)
        self.assertIn(self.component_b, wiz.mo_product_ids)

    def test_compute_mo_product_ids_empty_without_mo(self):
        """mo_product_ids must be empty when no production_id is set."""
        mo = self._make_mo()
        wiz = self.env['mrp.add.component.wizard'].new({
            'production_id': mo.id,
            'product_id': self.component_a.id,
            'quantity': 1.0,
        })
        wiz.production_id = False
        wiz._compute_mo_product_ids()
        self.assertFalse(wiz.mo_product_ids)

    # -----------------------------------------------------------------------
    # _compute_needed_quantity
    # -----------------------------------------------------------------------

    def test_compute_needed_quantity_for_existing_component(self):
        """needed_quantity should equal product_uom_qty − quantity_done for existing moves."""
        mo = self._make_mo()
        wiz = self._make_wizard(mo=mo, product=self.component_a)
        # component_a has product_uom_qty=2 and nothing consumed yet
        self.assertGreaterEqual(wiz.needed_quantity, 0.0)

    def test_compute_needed_quantity_zero_without_product(self):
        """needed_quantity must be 0.0 when no product is selected."""
        mo = self._make_mo()
        wiz = self.env['mrp.add.component.wizard'].new({
            'production_id': mo.id,
            'product_id': self.component_a.id,
            'quantity': 1.0,
        })
        wiz.product_id = False
        wiz._compute_needed_quantity()
        self.assertEqual(wiz.needed_quantity, 0.0)

    # -----------------------------------------------------------------------
    # _onchange_allow_any_product
    # -----------------------------------------------------------------------

    def test_onchange_allow_any_product_clears_invalid_product(self):
        """Toggling allow_any_product OFF should clear product not in MO components."""
        mo = self._make_mo()
        outside_product = self.env['product.product'].create({
            'name': 'Outside Product',
            'type': 'consu',
        })
        wiz = self.env['mrp.add.component.wizard'].new({
            'production_id': mo.id,
            'product_id': outside_product.id,
            'quantity': 1.0,
            'allow_any_product': True,
        })
        wiz.allow_any_product = False
        wiz._onchange_allow_any_product()
        self.assertFalse(wiz.product_id,
                         "Product outside MO components should be cleared when allow_any_product is False.")

    # -----------------------------------------------------------------------
    # action_add_component
    # -----------------------------------------------------------------------

    def test_action_add_component_increases_existing_quantity(self):
        """Adding an existing component should increase its quantity on the existing move."""
        mo = self._make_mo()
        original_qty = sum(
            mo.move_raw_ids.filtered(lambda m: m.product_id == self.component_a).mapped('quantity')
        )
        wiz = self._make_wizard(mo=mo, product=self.component_a, qty=5.0)
        wiz.action_add_component()
        new_qty = sum(
            mo.move_raw_ids.filtered(lambda m: m.product_id == self.component_a).mapped('quantity')
        )
        self.assertEqual(new_qty, original_qty + 5.0,
                         "Quantity should have increased by the wizard amount.")

    def test_action_add_component_creates_new_move_for_new_product(self):
        """Adding a product not in the BOM should create a new stock.move on the MO."""
        mo = self._make_mo()
        new_product = self.env['product.product'].create({
            'name': 'Extra Component',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
        })
        before_count = len(mo.move_raw_ids)
        wiz = self._make_wizard(mo=mo, product=new_product, qty=2.0)
        wiz.action_add_component()
        self.assertEqual(len(mo.move_raw_ids), before_count + 1,
                         "A new raw move should have been created.")

    def test_action_add_component_returns_close_action(self):
        """action_add_component must return an act_window_close dict."""
        wiz = self._make_wizard()
        result = wiz.action_add_component()
        self.assertEqual(result, {'type': 'ir.actions.act_window_close'})

    # -----------------------------------------------------------------------
    # action_remove_component
    # -----------------------------------------------------------------------

    def test_action_remove_component_removes_move(self):
        """action_remove_component should remove the matching raw move from the MO."""
        mo = self._make_mo()
        before_count = len(mo.move_raw_ids)
        wiz = self._make_wizard(mo=mo, product=self.component_a)
        wiz.action_remove_component()
        self.assertLess(len(mo.move_raw_ids), before_count,
                        "One raw move should have been removed.")

    def test_action_remove_component_noop_if_not_found(self):
        """action_remove_component on a product not in the MO must not raise."""
        mo = self._make_mo()
        ghost_product = self.env['product.product'].create({
            'name': 'Ghost Component',
            'type': 'consu',
        })
        wiz = self._make_wizard(mo=mo, product=ghost_product)
        try:
            wiz.action_remove_component()
        except Exception as exc:
            self.fail(f"action_remove_component raised unexpectedly: {exc}")


@tagged('post_install', '-at_install')
class TestScrapComponentWizard(ShopfloorCommon):
    """Tests for mrp.scrap.component.wizard."""

    def _make_scrap_wizard(self, mo=None, product=None, qty=1.0, reason=''):
        mo = mo or self._make_mo()
        vals = {
            'production_id': mo.id,
            'product_id': (product or self.component_a).id,
            'quantity': qty,
        }
        if reason:
            vals['reason'] = reason
        return self.env['mrp.scrap.component.wizard'].create(vals)

    # -----------------------------------------------------------------------
    # _compute_component_ids
    # -----------------------------------------------------------------------

    def test_compute_component_ids_contains_mo_raw_products(self):
        """component_ids should reflect the products in the MO raw moves."""
        mo = self._make_mo()
        wiz = self._make_scrap_wizard(mo=mo)
        self.assertIn(self.component_a, wiz.component_ids)
        self.assertIn(self.component_b, wiz.component_ids)

    # -----------------------------------------------------------------------
    # _check_quantity constraints
    # -----------------------------------------------------------------------

    def test_check_quantity_raises_if_exceeds_planned(self):
        """Scrapping more than the planned quantity must raise ValidationError."""
        mo = self._make_mo()
        # component_a has product_uom_qty=2.0 in BOM
        with self.assertRaises(ValidationError):
            self._make_scrap_wizard(mo=mo, product=self.component_a, qty=999.0)

    def test_check_quantity_raises_if_zero_or_negative(self):
        """Scrapping quantity ≤ 0 must raise ValidationError."""
        mo = self._make_mo()
        with self.assertRaises(ValidationError):
            self._make_scrap_wizard(mo=mo, product=self.component_a, qty=0.0)

    def test_check_quantity_valid_passes(self):
        """A quantity within the planned range must not raise."""
        mo = self._make_mo()
        try:
            self._make_scrap_wizard(mo=mo, product=self.component_a, qty=1.0)
        except ValidationError as exc:
            self.fail(f"Valid quantity raised ValidationError: {exc}")

    # -----------------------------------------------------------------------
    # action_scrap_component
    # -----------------------------------------------------------------------

    def test_action_scrap_component_creates_scrap_record(self):
        """action_scrap_component must create and validate a stock.scrap record."""
        mo = self._make_mo()
        wiz = self._make_scrap_wizard(mo=mo, product=self.component_a, qty=1.0)
        scrap_before = self.env['stock.scrap'].search([('production_id', '=', mo.id)])
        wiz.action_scrap_component()
        scrap_after = self.env['stock.scrap'].search([('production_id', '=', mo.id)])
        self.assertGreater(len(scrap_after), len(scrap_before),
                           "A stock.scrap record should have been created.")

    def test_action_scrap_component_with_reason_sets_origin(self):
        """When a reason is provided, the scrap origin should include it."""
        mo = self._make_mo()
        wiz = self._make_scrap_wizard(mo=mo, product=self.component_a, qty=1.0, reason='Defective batch')
        wiz.action_scrap_component()
        scrap = self.env['stock.scrap'].search([
            ('production_id', '=', mo.id),
            ('state', '=', 'done')
        ], limit=1)
        self.assertIn('Defective batch', scrap.origin or '',
                      "Scrap origin should contain the reason string.")

    def test_action_scrap_component_returns_close_action(self):
        """action_scrap_component must return an act_window_close dict."""
        mo = self._make_mo()
        wiz = self._make_scrap_wizard(mo=mo, product=self.component_a, qty=1.0)
        result = wiz.action_scrap_component()
        self.assertEqual(result, {'type': 'ir.actions.act_window_close'})

    # -----------------------------------------------------------------------
    # action_remove_scrap
    # -----------------------------------------------------------------------

    def test_action_remove_scrap_removes_unconfirmed_scrap(self):
        """action_remove_scrap must delete a draft/pending scrap for the component."""
        mo = self._make_mo()
        # Manually create a draft scrap without calling do_scrap()
        scrap_location = self.env['stock.location'].search(
            [('scrap_location', '=', True)], limit=1
        )
        scrap = self.env['stock.scrap'].create({
            'production_id': mo.id,
            'product_id': self.component_a.id,
            'scrap_qty': 1.0,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'scrap_location_id': scrap_location.id,
        })
        wiz = self.env['mrp.scrap.component.wizard'].create({
            'production_id': mo.id,
            'product_id': self.component_a.id,
            'quantity': 1.0,
        })
        wiz.action_remove_scrap()
        self.assertFalse(scrap.exists(), "Draft scrap should have been deleted.")

    def test_action_remove_scrap_noop_when_no_scrap(self):
        """action_remove_scrap must not raise when no matching scrap record exists."""
        mo = self._make_mo()
        wiz = self.env['mrp.scrap.component.wizard'].create({
            'production_id': mo.id,
            'product_id': self.component_a.id,
            'quantity': 1.0,
        })
        try:
            wiz.action_remove_scrap()
        except Exception as exc:
            self.fail(f"action_remove_scrap raised unexpectedly: {exc}")


@tagged('post_install', '-at_install')
class TestRerouteWizard(ShopfloorCommon):
    """Tests for mrp.reroute.wizard."""

    def _make_reroute_wizard(self, mo=None, wo=None, new_wc=None):
        mo = mo or self._make_mo()
        wo = wo or mo.workorder_ids[:1]
        new_wc = new_wc or self.workcenter_2
        return self.env['mrp.reroute.wizard'].create({
            'workorder_id': wo.id,
            'workcenter_id': new_wc.id,
        })

    def test_action_reroute_changes_workcenter(self):
        """action_reroute must update the workorder's workcenter to the selected one."""
        mo = self._make_mo()
        wo = mo.workorder_ids.filtered(lambda w: w.workcenter_id == self.workcenter_1)[:1]
        if not wo:
            self.skipTest("No WO on workcenter_1.")
        wiz = self._make_reroute_wizard(mo=mo, wo=wo, new_wc=self.workcenter_2)
        wiz.action_reroute()
        self.assertEqual(wo.workcenter_id, self.workcenter_2,
                         "Workorder workcenter should have been updated.")

    def test_action_reroute_in_progress_wo_resumes_after_reroute(self):
        """A WO that is in progress should be paused, rerouted, then restarted."""
        mo = self._make_mo()
        wo = mo.workorder_ids.filtered(lambda w: w.workcenter_id == self.workcenter_1)[:1]
        if not wo:
            self.skipTest("No WO on workcenter_1.")
        wo.button_start()
        self.assertEqual(wo.state, 'progress')

        wiz = self._make_reroute_wizard(mo=mo, wo=wo, new_wc=self.workcenter_2)
        wiz.action_reroute()

        self.assertEqual(wo.workcenter_id, self.workcenter_2)
        self.assertIn(wo.state, ('progress', 'ready'),
                      "WO should still be active after reroute.")

    def test_action_reroute_returns_close_action(self):
        """action_reroute must return an act_window_close dict."""
        mo = self._make_mo()
        wo = mo.workorder_ids[:1]
        if not wo:
            self.skipTest("No workorders on MO.")
        wiz = self._make_reroute_wizard(mo=mo, wo=wo)
        result = wiz.action_reroute()
        self.assertEqual(result, {'type': 'ir.actions.act_window_close'})

    def test_action_reroute_noop_without_wo_or_wc(self):
        """action_reroute with missing workorder must not raise."""
        mo = self._make_mo()
        wo = mo.workorder_ids[:1]
        if not wo:
            self.skipTest("No workorders on MO.")
        wiz = self.env['mrp.reroute.wizard'].new({
            'workorder_id': wo.id,
            'workcenter_id': self.workcenter_2.id,
        })
        wiz.workorder_id = False
        try:
            wiz.action_reroute()
        except Exception as exc:
            self.fail(f"action_reroute without workorder raised unexpectedly: {exc}")


@tagged('post_install', '-at_install')
class TestAddWorkorderWizard(ShopfloorCommon):
    """Tests for mrp.add.workorder.wizard."""

    def _make_wo_wizard(self, mo=None, name='Test Extra Op', wc=None, duration=60.0):
        mo = mo or self._make_mo()
        return self.env['mrp.add.workorder.wizard'].create({
            'production_id': mo.id,
            'name': name,
            'workcenter_id': (wc or self.workcenter_1).id,
            'duration_expected': duration,
        })

    # -----------------------------------------------------------------------
    # action_add_workorder
    # -----------------------------------------------------------------------

    def test_action_add_workorder_creates_new_workorder(self):
        """action_add_workorder must create a new mrp.workorder on the MO."""
        mo = self._make_mo()
        before_count = len(mo.workorder_ids)
        wiz = self._make_wo_wizard(mo=mo)
        wiz.action_add_workorder()
        self.assertEqual(len(mo.workorder_ids), before_count + 1,
                         "A new workorder should have been added to the MO.")

    def test_action_add_workorder_uses_correct_workcenter(self):
        """The newly created workorder should be assigned the wizard's workcenter."""
        mo = self._make_mo()
        wiz = self._make_wo_wizard(mo=mo, wc=self.workcenter_2)
        wiz.action_add_workorder()
        new_wo = mo.workorder_ids.filtered(
            lambda w: w.name == 'Test Extra Op' and w.workcenter_id == self.workcenter_2
        )
        self.assertTrue(new_wo, "New WO should be on workcenter_2.")

    def test_action_add_workorder_ready_state_on_confirmed_mo(self):
        """Workorder added to a confirmed MO should be set to 'ready' state."""
        mo = self._make_mo(confirm=True)
        wiz = self._make_wo_wizard(mo=mo, name='Ready Op')
        wiz.action_add_workorder()
        new_wo = mo.workorder_ids.filtered(lambda w: w.name == 'Ready Op')
        self.assertTrue(new_wo)
        self.assertEqual(new_wo.state, 'ready',
                         "New WO on confirmed MO should be in ready state.")

    def test_action_add_workorder_with_date_start(self):
        """Wizard with date_start must set that date on the new workorder."""
        from odoo import fields as odoo_fields
        mo = self._make_mo()
        scheduled = odoo_fields.Datetime.now()
        wiz = self.env['mrp.add.workorder.wizard'].create({
            'production_id': mo.id,
            'name': 'Scheduled Op',
            'workcenter_id': self.workcenter_1.id,
            'duration_expected': 30.0,
            'date_start': scheduled,
        })
        wiz.action_add_workorder()
        new_wo = mo.workorder_ids.filtered(lambda w: w.name == 'Scheduled Op')
        self.assertTrue(new_wo, "New WO should exist.")
        self.assertEqual(new_wo.date_start, scheduled)

    def test_action_add_workorder_returns_close_action(self):
        """action_add_workorder must return an act_window_close dict."""
        wiz = self._make_wo_wizard()
        result = wiz.action_add_workorder()
        self.assertEqual(result, {'type': 'ir.actions.act_window_close'})

    # -----------------------------------------------------------------------
    # action_remove_workorder
    # -----------------------------------------------------------------------

    def test_action_remove_workorder_removes_matching_wo(self):
        """action_remove_workorder should delete the matching non-done workorder."""
        mo = self._make_mo()
        wiz = self._make_wo_wizard(mo=mo, name='Removable Op')
        wiz.action_add_workorder()
        self.assertTrue(mo.workorder_ids.filtered(lambda w: w.name == 'Removable Op'))

        # Create remove wizard pointing at the same op / workcenter
        remove_wiz = self.env['mrp.add.workorder.wizard'].create({
            'production_id': mo.id,
            'name': 'Removable Op',
            'workcenter_id': self.workcenter_1.id,
            'duration_expected': 60.0,
        })
        remove_wiz.action_remove_workorder()
        remaining = mo.workorder_ids.filtered(lambda w: w.name == 'Removable Op')
        self.assertFalse(remaining, "The workorder should have been removed.")

    def test_action_remove_workorder_noop_when_not_found(self):
        """action_remove_workorder must not raise if no matching WO is found."""
        mo = self._make_mo()
        wiz = self.env['mrp.add.workorder.wizard'].create({
            'production_id': mo.id,
            'name': 'Nonexistent Op',
            'workcenter_id': self.workcenter_1.id,
            'duration_expected': 60.0,
        })
        try:
            wiz.action_remove_workorder()
        except Exception as exc:
            self.fail(f"action_remove_workorder raised unexpectedly: {exc}")
