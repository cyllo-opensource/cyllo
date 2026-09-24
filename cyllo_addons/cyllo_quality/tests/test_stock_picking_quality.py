# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import QualityCommon


@tagged('post_install', '-at_install', 'cyllo_quality')
class TestStockPickingQuality(QualityCommon):
    """Integration tests for quality checks on stock.picking."""

    # ── action_confirm populates control points ───────────────────────────

    def test_confirm_picking_links_matching_qcp(self):
        """Confirming a picking should detect matching QCPs and mark quality check required."""
        qcp = self._make_qcp(control_type='operation')
        picking = self._make_picking()
        picking.action_confirm()
        self.assertIn(qcp, picking.quality_control_point_ids)
        self.assertTrue(picking.is_quality_check)

    def test_confirm_picking_without_matching_qcp(self):
        """A picking with no matching QCP should not set is_quality_check."""
        # Use out-picking type; QCP is on in-picking type
        self._make_qcp(control_type='operation')  # bound to picking_type_in
        picking = self._make_picking(picking_type=self.picking_type_out)
        picking.action_confirm()
        self.assertFalse(picking.is_quality_check)

    def test_confirm_picking_qcp_scoped_to_product(self):
        """A product-scoped QCP must link only when the picking contains that product."""
        other_product = self.env['product.product'].create({
            'name': 'Other Product',
            'type': 'consu',
        })
        qcp = self._make_qcp(
            qc_check_for='product',
            product_ids=[(6, 0, [other_product.id])],
        )
        picking = self._make_picking(product=self.product)  # different product
        picking.action_confirm()
        self.assertNotIn(qcp, picking.quality_control_point_ids)

    def test_confirm_picking_qcp_product_match(self):
        """A product-scoped QCP should link when picking has that product."""
        qcp = self._make_qcp(
            qc_check_for='product',
            product_ids=[(6, 0, [self.product.id])],
        )
        picking = self._make_picking(product=self.product)
        picking.action_confirm()
        self.assertIn(qcp, picking.quality_control_point_ids)

    def test_confirm_picking_qcp_category_match(self):
        """A category-scoped QCP should link when picking product belongs to that category."""
        qcp = self._make_qcp(
            qc_check_for='category',
            product_category_ids=[(6, 0, [self.product_category.id])],
        )
        picking = self._make_picking(product=self.product)
        picking.action_confirm()
        self.assertIn(qcp, picking.quality_control_point_ids)

    # ── action_quality_check creates quality.check records ────────────────

    def test_action_quality_check_creates_checks(self):
        """action_quality_check must create quality.check records for the picking."""
        self._make_qcp(control_type='product')
        picking = self._make_picking()
        picking.action_confirm()
        # Set qty_done so product-type QCP can proceed
        for move in picking.move_ids_without_package:
            move.quantity = 5.0
        picking.action_quality_check()
        self.assertTrue(picking.quality_check_ids)

    def test_action_quality_check_idempotent(self):
        """Calling action_quality_check twice should not create duplicate checks."""
        self._make_qcp(control_type='operation')
        picking = self._make_picking()
        picking.action_confirm()
        picking.action_quality_check()
        count_after_first = len(picking.quality_check_ids)
        picking.action_quality_check()
        self.assertEqual(len(picking.quality_check_ids), count_after_first)

    def test_action_quality_check_sets_flag(self):
        """is_quality_check_created must be True after action_quality_check."""
        self._make_qcp(control_type='operation')
        picking = self._make_picking()
        picking.action_confirm()
        picking.action_quality_check()
        self.assertTrue(picking.is_quality_check_created)

    def test_action_quality_check_zero_qty_raises(self):
        """action_quality_check must raise UserError for zero-quantity moves on product QCP."""
        self._make_qcp(control_type='product')
        picking = self._make_picking(qty=0.0)
        with self.assertRaises(UserError):
            picking.action_confirm()

    # ── button_validate blocks if checks not yet completed ────────────────

    def test_button_validate_blocks_without_checks(self):
        """button_validate must raise UserError if QCPs exist but checks not completed."""
        self._make_qcp(control_type='operation')
        picking = self._make_picking()
        picking.action_confirm()
        # Quality check lines exist but are not yet completed
        with self.assertRaises(UserError):
            picking.button_validate()

    def test_button_validate_allowed_when_no_qcps(self):
        """button_validate should NOT raise when no quality control points are linked."""
        # No QCP for this picking type
        picking = self._make_picking(picking_type=self.picking_type_out)
        picking.action_confirm()
        # Should not raise (just call super) — we catch nothing here
        try:
            picking.button_validate()
        except UserError as e:
            # A UserError about QC is a failure; stock-level errors are acceptable
            if 'quality check' in str(e).lower():
                self.fail("button_validate raised quality UserError with no QCPs.")

    # ── qc_count / qc_checked_count ───────────────────────────────────────

    def test_qc_count_computed_before_checks_created(self):
        """qc_count should reflect expected count from inspection templates."""
        self._make_qcp(control_type='operation')
        picking = self._make_picking()
        picking.action_confirm()
        # Before generating checks, count is estimated from QCP inspection lines
        self.assertGreater(picking.qc_count, 0)

    def test_qc_checked_count_increments(self):
        """qc_checked_count should increase as check lines are validated."""
        self._make_qcp(control_type='operation')
        picking = self._make_picking()
        picking.action_confirm()
        picking.action_quality_check()
        self.assertEqual(picking.qc_checked_count, 0)
        # Check one line
        first_line = picking.quality_check_ids[0].quality_check_line_ids[0]
        first_line.write({'is_checked': True, 'status': 'pass'})
        self.assertEqual(picking.qc_checked_count, 1)

    def test_is_quality_check_cleared_when_all_lines_done(self):
        """is_quality_check should become False once every line is checked."""
        self._make_qcp(control_type='operation')
        picking = self._make_picking()
        picking.action_confirm()
        picking.action_quality_check()
        # Mark every line as checked
        for qc in picking.quality_check_ids:
            for line in qc.quality_check_line_ids:
                line.write({'is_checked': True, 'status': 'pass'})
        # Trigger recompute
        picking._compute_quality_checks()
        self.assertFalse(picking.is_quality_check)

    # ── action_view_quality_check ─────────────────────────────────────────

    def test_action_view_quality_check_returns_act_window(self):
        """action_view_quality_check must return an act_window for quality.check."""
        self._make_qcp(control_type='operation')
        picking = self._make_picking()
        picking.action_confirm()
        picking.action_quality_check()
        action = picking.action_view_quality_check()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'quality.check')

    # ── create_quality_checks helper ──────────────────────────────────────

    def test_create_quality_checks_for_quantity_type(self):
        """create_quality_checks should compute percentage qty for 'quantity' QCPs."""
        qcp = self._make_qcp(
            control_type='quantity',
            control_quantity=50,  # 50 %
        )
        picking = self._make_picking(qty=10.0)
        picking.action_confirm()
        move = picking.move_ids_without_package[0]
        move.quantity = 10.0
        qc = picking.create_quality_checks(move, qcp)
        self.assertEqual(qc.quantity, 5)  # 50% of 10
