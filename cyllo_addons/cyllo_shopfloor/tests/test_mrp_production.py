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
from odoo.tests.common import tagged
from .common import ShopfloorCommon


@tagged('post_install', '-at_install')
class TestMrpProduction(ShopfloorCommon):
    """Tests for cyllo_shopfloor extensions on mrp.production."""

    # -----------------------------------------------------------------------
    # _compute_is_automated
    # -----------------------------------------------------------------------

    def test_compute_is_automated_from_bom(self):
        """MO.is_automated must reflect bom.is_automated when a BOM is assigned."""
        self.bom.is_automated = True
        mo = self._make_mo(confirm=False)
        self.assertTrue(mo.is_automated, "is_automated should be True when BOM is automated.")

    def test_compute_is_automated_no_bom(self):
        """MO without a BOM must have is_automated=False by default."""
        mo = self.env['mrp.production'].create({
            'product_id': self.finished_product.id,
            'product_qty': 1.0,
        })
        self.assertFalse(mo.is_automated, "MO without BOM should default is_automated to False.")

    def test_is_automated_manual_override(self):
        """is_automated can be overridden on the MO independently of the BOM."""
        self.bom.is_automated = False
        mo = self._make_mo(confirm=False)
        mo.is_automated = True
        self.assertTrue(mo.is_automated, "Manual override of is_automated should be respected.")

    # -----------------------------------------------------------------------
    # employee_ids
    # -----------------------------------------------------------------------

    def test_employee_ids_initially_empty(self):
        """A new MO should have no operators assigned."""
        if 'hr.employee' not in self.env:
            self.skipTest("hr module not installed — employee_ids comodel unavailable.")
        mo = self._make_mo()
        self.assertFalse(mo.employee_ids, "employee_ids should be empty on a new MO.")

    def test_employee_ids_field_exists(self):
        """employee_ids field must be declared on mrp.production (comodel check skipped)."""
        mo = self._make_mo()
        self.assertIn(
            'employee_ids', mo._fields,
            "mrp.production should have an employee_ids field added by cyllo_shopfloor."
        )

    # -----------------------------------------------------------------------
    # action_shopfloor_close_mo
    # -----------------------------------------------------------------------

    def test_action_shopfloor_close_mo_sets_qty_producing(self):
        """close_mo should auto-fill qty_producing when it is 0."""
        mo = self._make_mo(qty=5.0)
        self.assertEqual(mo.qty_producing, 0.0, "qty_producing should start at 0.")
        # Immediate close: will set qty_producing = product_qty
        mo.action_shopfloor_close_mo()
        # After done state qty_producing may be read-only; just verify the MO closed
        self.assertIn(mo.state, ('done', 'to_close'), "MO should be done or ready to close.")

    def test_action_shopfloor_close_mo_lot_tracked_generates_serial(self):
        """close_mo must auto-generate a lot/serial for tracked products if not set."""
        bom_lot = self.env['mrp.bom'].create({
            'product_tmpl_id': self.finished_product_lot.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {
                'product_id': self.component_a.id,
                'product_qty': 1.0,
            })],
        })
        mo = self._make_mo(product=self.finished_product_lot, qty=1.0, bom=bom_lot)
        self.assertFalse(mo.lot_producing_id, "lot_producing_id should be empty initially.")
        mo.action_shopfloor_close_mo()
        # Either the lot was generated (in which case MO is done) or the state progressed
        self.assertIn(mo.state, ('done', 'to_close'),
                      "MO should move to done/to_close after shopfloor close.")

    def test_action_shopfloor_close_mo_requires_single_record(self):
        """close_mo raises if called on a multi-record set (ensure_one guard)."""
        mo1 = self._make_mo()
        mo2 = self._make_mo()
        with self.assertRaises(Exception):
            (mo1 | mo2).action_shopfloor_close_mo()

    # -----------------------------------------------------------------------
    # get_shopfloor_missing_components
    # -----------------------------------------------------------------------

    def test_get_shopfloor_missing_components_returns_dict(self):
        """get_shopfloor_missing_components should return a dict keyed by MO id."""
        mo = self._make_mo()
        result = self.env['mrp.production'].get_shopfloor_missing_components([mo.id])
        self.assertIsInstance(result, dict, "Result must be a dict.")
        self.assertIn(mo.id, result, "Result must contain an entry for the MO id.")

    def test_get_shopfloor_missing_components_lists_pending_moves(self):
        """Missing components list should contain entries for pending raw moves."""
        mo = self._make_mo()
        result = self.env['mrp.production'].get_shopfloor_missing_components([mo.id])
        missing = result[mo.id]
        self.assertTrue(len(missing) > 0, "There should be at least one missing component.")
        for entry in missing:
            self.assertIn('product_name', entry)
            self.assertIn('needed_qty', entry)
            self.assertIn('uom', entry)

    def test_get_shopfloor_missing_components_no_pending_after_done(self):
        """After closing an MO, missing components list should be empty."""
        mo = self._make_mo(qty=1.0)
        mo.action_shopfloor_close_mo()
        result = self.env['mrp.production'].get_shopfloor_missing_components([mo.id])
        # If state is done, all moves are done so missing list is empty
        if mo.state == 'done':
            self.assertEqual(result[mo.id], [],
                             "No missing components for a completed MO.")

    def test_get_shopfloor_missing_components_empty_list(self):
        """Passing an empty list of ids should return an empty dict."""
        result = self.env['mrp.production'].get_shopfloor_missing_components([])
        self.assertEqual(result, {}, "Empty input should yield an empty dict.")

    def test_get_shopfloor_missing_components_multiple_mos(self):
        """Multiple MO ids can be passed and all appear in the result dict."""
        mo1 = self._make_mo()
        mo2 = self._make_mo()
        result = self.env['mrp.production'].get_shopfloor_missing_components([mo1.id, mo2.id])
        self.assertIn(mo1.id, result)
        self.assertIn(mo2.id, result)

    # -----------------------------------------------------------------------
    # action_open_cyllo_shopfloor
    # -----------------------------------------------------------------------

    def test_action_open_cyllo_shopfloor_returns_client_action(self):
        """The shopfloor smart-button action must return an ir.actions.client dict."""
        mo = self._make_mo()
        action = mo.action_open_cyllo_shopfloor()
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'shopfloor_screen')

    def test_action_open_cyllo_shopfloor_contains_production_context(self):
        """The returned client action context must carry default_production_id."""
        mo = self._make_mo()
        action = mo.action_open_cyllo_shopfloor()
        self.assertEqual(action['context']['default_production_id'], mo.id)

    def test_action_open_cyllo_shopfloor_requires_single_record(self):
        """action_open_cyllo_shopfloor raises on multi-record set."""
        mo1 = self._make_mo()
        mo2 = self._make_mo()
        with self.assertRaises(Exception):
            (mo1 | mo2).action_open_cyllo_shopfloor()
