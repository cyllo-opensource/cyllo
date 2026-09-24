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
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestCylloQualityRepair(TransactionCase):
    """Tests for the cyllo_quality_repair bridge module.

    Covers:
        - RepairOrder.action_validate: quality control point linking
        - RepairOrder.action_quality_check: quality check generation
        - RepairOrder._compute_quality_checks: computed field values
        - RepairOrder.action_repair_end: enforcement of complete quality checks
        - QualityCheck.repair_id: inverse link from quality.check to repair.order
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── product & category ──────────────────────────────────────────────
        cls.product_category = cls.env['product.category'].create({
            'name': 'Test Repair Category',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Test Repair Product',
            'categ_id': cls.product_category.id,
            'type': 'product',
        })

        # ── repair picking type (code = 'repair_operation') ─────────────────
        cls.company = cls.env.company
        cls.repair_picking_type = cls.env['stock.picking.type'].search(
            [('code', '=', 'repair_operation'),
             ('company_id', '=', cls.company.id)], limit=1
        )
        if not cls.repair_picking_type:
            warehouse = cls.env['stock.warehouse'].search(
                [('company_id', '=', cls.company.id)], limit=1)
            cls.repair_picking_type = cls.env['stock.picking.type'].create({
                'name': 'Repair Operations',
                'code': 'repair_operation',
                'warehouse_id': warehouse.id,
                'sequence_code': 'RO',
            })

        # ── quality team ────────────────────────────────────────────────────
        cls.quality_team = cls.env['quality.team'].create({
            'name': 'Test Quality Team',
        })

        # ── inspection action & type ─────────────────────────────────────────
        cls.inspection_action = cls.env['inspection.action'].search([], limit=1)
        cls.inspection_type = cls.env['inspection.type'].search([], limit=1)

        # ── quality control point (product-level, all-product) ───────────────
        cls.quality_control_point = cls.env['quality.control.point'].create({
            'qc_check_for': 'product',
            'control_type': 'product',
            'control_by': 'all',
            'quality_team_id': cls.quality_team.id,
            'operation_type_ids': [(4, cls.repair_picking_type.id)],
            'quality_inspection_ids': [(0, 0, {
                'inspection_action_id': cls.inspection_action.id,
                'inspection_type_id': cls.inspection_type.id,
                'instruction': 'Verify the repaired item visually.',
            })],
        })

        # ── quality control point filtered by product ────────────────────────
        cls.quality_control_point_product = cls.env['quality.control.point'].create({
            'qc_check_for': 'product',
            'control_type': 'quantity',
            'control_by': 'all',
            'quality_team_id': cls.quality_team.id,
            'operation_type_ids': [(4, cls.repair_picking_type.id)],
            'product_ids': [(4, cls.product.id)],
            'control_quantity': 50,
            'quality_inspection_ids': [(0, 0, {
                'inspection_action_id': cls.inspection_action.id,
                'inspection_type_id': cls.inspection_type.id,
                'instruction': 'Check quantity sample.',
            })],
        })

        # ── quality control point filtered by category ───────────────────────
        cls.quality_control_point_category = cls.env['quality.control.point'].create({
            'qc_check_for': 'product',
            'control_type': 'product',
            'control_by': 'all',
            'quality_team_id': cls.quality_team.id,
            'operation_type_ids': [(4, cls.repair_picking_type.id)],
            'product_category_ids': [(4, cls.product_category.id)],
            'quality_inspection_ids': [(0, 0, {
                'inspection_action_id': cls.inspection_action.id,
                'inspection_type_id': cls.inspection_type.id,
                'instruction': 'Category-based visual check.',
            })],
        })

    # ── helpers ──────────────────────────────────────────────────────────────

    def _create_repair_order(self, product_qty=1.0):
        """Return an unsaved (draft) repair.order for cls.product."""
        return self.env['repair.order'].create({
            'name': 'Test Repair',
            'product_id': self.product.id,
            'product_qty': product_qty,
            'picking_type_id': self.repair_picking_type.id,
        })

    def _mark_all_checks_done(self, repair):
        """Mark every quality check line on *repair* as checked."""
        for check in repair.quality_check_ids:
            check.quality_check_line_ids.write({'is_checked': True})

    # ── action_validate ───────────────────────────────────────────────────────

    def test_action_validate_links_quality_control_points(self):
        """action_validate should populate quality_control_point_ids."""
        repair = self._create_repair_order()
        repair.action_validate()
        self.assertTrue(
            repair.quality_control_point_ids,
            "quality_control_point_ids must be filled after action_validate."
        )

    def test_action_validate_links_correct_control_point(self):
        """The generic (no product/category filter) control point must be linked."""
        repair = self._create_repair_order()
        repair.action_validate()
        self.assertIn(
            self.quality_control_point,
            repair.quality_control_point_ids,
        )

    def test_action_validate_links_product_control_point(self):
        """A product-filtered control point matching the repair product must be linked."""
        repair = self._create_repair_order()
        repair.action_validate()
        self.assertIn(
            self.quality_control_point_product,
            repair.quality_control_point_ids,
        )

    def test_action_validate_links_category_control_point(self):
        """A category-filtered control point matching the product's category must be linked."""
        repair = self._create_repair_order()
        repair.action_validate()
        self.assertIn(
            self.quality_control_point_category,
            repair.quality_control_point_ids,
        )

    # ── action_quality_check ──────────────────────────────────────────────────

    def test_action_quality_check_creates_quality_checks(self):
        """action_quality_check should create quality.check records."""
        repair = self._create_repair_order()
        repair.action_validate()
        repair.action_quality_check()
        self.assertTrue(
            repair.quality_check_ids,
            "quality_check_ids must be populated after action_quality_check."
        )

    def test_action_quality_check_sets_is_quality_check_created(self):
        """is_quality_check_created must become True after the first call."""
        repair = self._create_repair_order()
        repair.action_validate()
        repair.action_quality_check()
        self.assertTrue(repair.is_quality_check_created)

    def test_action_quality_check_idempotent(self):
        """Calling action_quality_check twice must not duplicate checks."""
        repair = self._create_repair_order()
        repair.action_validate()
        repair.action_quality_check()
        first_count = len(repair.quality_check_ids)
        repair.action_quality_check()  # second call should be a no-op
        self.assertEqual(
            len(repair.quality_check_ids),
            first_count,
            "Repeated calls to action_quality_check must not create duplicate checks.",
        )

    def test_action_quality_check_zero_quantity_raises(self):
        """action_quality_check must raise UserError when product_qty is 0."""
        repair = self._create_repair_order(product_qty=0.0)
        with self.assertRaises(UserError):
            repair.action_validate()

    def test_action_quality_check_quantity_control_type(self):
        """For 'quantity' control type, check qty = (product_qty * control_quantity) / 100."""
        repair = self._create_repair_order(product_qty=10.0)
        repair.action_validate()
        repair.action_quality_check()

        quantity_checks = repair.quality_check_ids.filtered(
            lambda c: c.quality_control_id == self.quality_control_point_product
        )
        self.assertTrue(quantity_checks, "Should have a check for the quantity control point.")
        expected_qty = (10.0 * self.quality_control_point_product.control_quantity) / 100
        self.assertAlmostEqual(
            quantity_checks[0].quantity,
            expected_qty,
            places=4,
            msg="Quality check quantity must follow the percentage formula.",
        )

    def test_action_quality_check_repair_id_set(self):
        """Each generated quality.check must back-reference the repair order."""
        repair = self._create_repair_order()
        repair.action_validate()
        repair.action_quality_check()
        for check in repair.quality_check_ids:
            self.assertEqual(
                check.repair_id,
                repair,
                "quality.check.repair_id must point back to the repair order.",
            )

    # ── _compute_quality_checks ───────────────────────────────────────────────

    def test_compute_is_quality_check_true_when_checks_pending(self):
        """is_quality_check must be True when there are unchecked lines."""
        repair = self._create_repair_order()
        repair.action_validate()
        repair.action_quality_check()
        self.assertTrue(
            repair.is_quality_check,
            "is_quality_check must be True while checks are still pending.",
        )

    def test_compute_is_quality_check_false_when_all_done(self):
        """is_quality_check must be False when all check lines are marked done."""
        repair = self._create_repair_order()
        repair.action_validate()
        repair.action_quality_check()
        self._mark_all_checks_done(repair)
        self.assertFalse(
            repair.is_quality_check,
            "is_quality_check must be False once all check lines are checked.",
        )

    def test_compute_qc_count_and_checked_count(self):
        """qc_count and qc_checked_count must reflect actual line states."""
        repair = self._create_repair_order()
        repair.action_validate()
        repair.action_quality_check()

        total_lines = len(repair.quality_check_ids.quality_check_line_ids)
        self.assertEqual(repair.qc_count, total_lines)
        self.assertEqual(repair.qc_checked_count, 0)

        self._mark_all_checks_done(repair)
        self.assertEqual(repair.qc_checked_count, total_lines)

    def test_compute_is_quality_check_false_without_control_points(self):
        """is_quality_check must be False when no control points are linked."""
        repair = self._create_repair_order()
        # Do NOT call action_validate — no control points linked.
        self.assertFalse(
            repair.is_quality_check,
            "is_quality_check must be False when quality_control_point_ids is empty.",
        )

    # ── action_repair_end ─────────────────────────────────────────────────────

    def test_action_repair_end_raises_when_checks_pending(self):
        """action_repair_end must raise UserError when quality checks are incomplete."""
        repair = self._create_repair_order()
        repair.action_validate()
        repair.action_quality_check()
        with self.assertRaises(UserError):
            repair.action_repair_end()

    def test_action_repair_end_raises_when_checks_not_generated(self):
        """action_repair_end must raise UserError when control points exist but no checks generated."""
        repair = self._create_repair_order()
        repair.action_validate()
        # quality checks NOT generated yet
        with self.assertRaises(UserError):
            repair.action_repair_end()

    def test_action_repair_end_succeeds_when_checks_complete(self):
        """action_repair_end must NOT raise when all quality checks are completed."""
        repair = self._create_repair_order()
        repair.action_validate()
        repair.action_quality_check()
        self._mark_all_checks_done(repair)
        try:
            repair.action_repair_end()
        except UserError as exc:
            self.fail(
                f"action_repair_end raised UserError unexpectedly: {exc}"
            )

    # ── action_view_quality_check ─────────────────────────────────────────────

    def test_action_view_quality_check_returns_act_window(self):
        """action_view_quality_check must return a window action for quality.check."""
        repair = self._create_repair_order()
        repair.action_validate()
        repair.action_quality_check()
        action = repair.action_view_quality_check()
        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'quality.check')
        domain_ids = dict(action.get('domain', []))
        self.assertIn('id', domain_ids)

    # ── quality.check.repair_id ───────────────────────────────────────────────

    def test_quality_check_repair_id_field_exists(self):
        """quality.check must expose a repair_id Many2one field."""
        QualityCheck = self.env['quality.check']
        self.assertIn(
            'repair_id',
            QualityCheck._fields,
            "quality.check must have a repair_id field.",
        )

    def test_quality_check_repair_id_writable(self):
        """repair_id on quality.check must be writable directly."""
        repair = self._create_repair_order()
        repair.action_validate()
        repair.action_quality_check()
        check = repair.quality_check_ids[:1]
        check.write({'repair_id': repair.id})
        self.assertEqual(check.repair_id, repair)
