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
"""
Tests for cyllo_quality_mrp — the bridge module that integrates
cyllo_quality Quality Checks into mrp.production Manufacturing Orders.

Covered areas
─────────────
1.  quality.check.mo_id back-link field
2.  mrp.production.action_confirm — QCP detection (no restriction, product,
    category, "all categories", no match on wrong operation type)
3.  mrp.production.action_quality_check — check creation, idempotency,
    zero-qty guard, quantity-type percentage, is_quality_check_created flag
4.  mrp.production._compute_quality_checks — qc_count / qc_checked_count
    before and after check creation, is_quality_check auto-cleared on completion
5.  mrp.production.action_view_quality_check — correct act_window returned
"""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'cyllo_quality_mrp')
class TestQualityMrp(TransactionCase):
    """Integration tests for cyllo_quality_mrp."""

    # ── Shared fixtures ───────────────────────────────────────────────────

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Inspection lookup data (seeded by cyllo_quality data files) ───
        cls.inspection_type_pass_fail = cls.env['inspection.type'].search(
            [('name', '=', 'Pass/Fail')], limit=1
        )
        cls.inspection_type_measure = cls.env.ref(
            'cyllo_quality.inspection_type_measure'
        )
        cls.inspection_action = cls.env['inspection.action'].search([], limit=1)
        if not cls.inspection_action:
            cls.inspection_action = cls.env['inspection.action'].create(
                {'name': 'Visual Check'}
            )

        # ── UoM ───────────────────────────────────────────────────────────
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # ── Product categories ────────────────────────────────────────────
        cls.product_category = cls.env['product.category'].create(
            {'name': 'MRP Quality Category'}
        )
        cls.product_category_other = cls.env['product.category'].create(
            {'name': 'Other MRP Category'}
        )

        # ── Products ──────────────────────────────────────────────────────
        cls.product = cls.env['product.product'].create({
            'name': 'MRP Quality Product',
            'categ_id': cls.product_category.id,
            'type': 'consu',
        })
        cls.product_other = cls.env['product.product'].create({
            'name': 'Other MRP Product',
            'categ_id': cls.product_category_other.id,
            'type': 'consu',
        })

        # ── Warehouse / picking type ──────────────────────────────────────
        cls.warehouse = cls.env.ref('stock.warehouse0')
        # Manufacturing operation type lives on the warehouse's mfg picking type
        cls.picking_type_mfg = cls.env['stock.picking.type'].search(
            [('code', '=', 'mrp_operation'),
             ('warehouse_id', '=', cls.warehouse.id)],
            limit=1,
        )
        cls.picking_type_in = cls.warehouse.in_type_id  # unrelated type

        # ── Quality team (no email to avoid SMTP in tests) ─────────────────
        cls.employee = cls.env['hr.employee'].create(
            {'name': 'MRP Quality Inspector'}
        )
        cls.quality_team = cls.env['quality.team'].create({
            'name': 'MRP Quality Team',
            'leader_id': cls.employee.id,
            'is_mail': False,
        })

        # ── BoM for the product (required for mrp.production) ─────────────
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
        })

    # ── Helpers ───────────────────────────────────────────────────────────

    def _make_qcp(self, picking_type=None, extra_inspections=None, **kwargs):
        """Create a minimal valid quality.control.point bound to the MFG picking type."""
        picking_type = picking_type or self.picking_type_mfg
        inspections = extra_inspections or [{
            'inspection_action_id': self.inspection_action.id,
            'inspection_type_id': self.inspection_type_pass_fail.id,
        }]
        vals = {
            'operation_type_ids': [(6, 0, [picking_type.id])],
            'quality_team_id': self.quality_team.id,
            'control_type': 'operation',
            'control_by': 'all',
            'quality_inspection_ids': [
                (0, 0, {
                    'inspection_action_id': self.inspection_action.id,
                    'inspection_type_id': self.inspection_type_pass_fail.id,
                    **insp,
                })
                for insp in inspections
            ],
        }
        vals.update(kwargs)
        return self.env['quality.control.point'].create(vals)

    def _make_mo(self, product=None, qty=5.0):
        """Create an unconfirmed mrp.production for the given product."""
        product = product or self.product
        return self.env['mrp.production'].create({
            'product_id': product.id,
            'product_qty': qty,
            'product_uom_id': self.uom_unit.id,
            'bom_id': self.bom.id,
        })

    # ════════════════════════════════════════════════════════════════════
    # 1. quality.check.mo_id field
    # ════════════════════════════════════════════════════════════════════

    def test_quality_check_has_mo_id_field(self):
        """quality.check must have an mo_id Many2one to mrp.production."""
        qc = self.env['quality.check'].create({
            'quality_control_id': self._make_qcp().id,
            'control_type': 'operation',
        })
        self.assertIn('mo_id', qc._fields)
        self.assertEqual(
            qc._fields['mo_id'].comodel_name, 'mrp.production'
        )

    def test_quality_check_mo_id_writable(self):
        """mo_id should be settable on a quality.check record."""
        qcp = self._make_qcp()
        mo = self._make_mo()
        mo.action_confirm()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
            'mo_id': mo.id,
        })
        self.assertEqual(qc.mo_id, mo)

    # ════════════════════════════════════════════════════════════════════
    # 2. action_confirm — QCP detection
    # ════════════════════════════════════════════════════════════════════

    def test_confirm_links_unrestricted_qcp(self):
        """An unrestricted QCP (no product / category filter) must be linked on confirm."""
        qcp = self._make_qcp(control_type='operation')
        mo = self._make_mo()
        mo.action_confirm()
        self.assertIn(qcp, mo.quality_control_point_ids)
        self.assertTrue(mo.is_quality_check)

    def test_confirm_links_product_matched_qcp(self):
        """A product-scoped QCP must link when the MO's product matches."""
        qcp = self._make_qcp(
            product_ids=[(6, 0, [self.product.id])],
        )
        mo = self._make_mo(product=self.product)
        mo.action_confirm()
        self.assertIn(qcp, mo.quality_control_point_ids)

    def test_confirm_skips_product_mismatch_qcp(self):
        """A product-scoped QCP must NOT link when the MO uses a different product."""
        qcp = self._make_qcp(
            product_ids=[(6, 0, [self.product_other.id])],
        )
        mo = self._make_mo(product=self.product)
        mo.action_confirm()
        self.assertNotIn(qcp, mo.quality_control_point_ids)

    def test_confirm_links_category_matched_qcp(self):
        """A category-scoped QCP must link when the product belongs to that category."""
        qcp = self._make_qcp(
            product_category_ids=[(6, 0, [self.product_category.id])],
        )
        mo = self._make_mo(product=self.product)
        mo.action_confirm()
        self.assertIn(qcp, mo.quality_control_point_ids)

    def test_confirm_skips_category_mismatch_qcp(self):
        """A category-scoped QCP must NOT link when the product is in a different category."""
        qcp = self._make_qcp(
            product_category_ids=[(6, 0, [self.product_category_other.id])],
        )
        # product belongs to product_category, not product_category_other
        mo = self._make_mo(product=self.product)
        mo.action_confirm()
        self.assertNotIn(qcp, mo.quality_control_point_ids)

    def test_confirm_links_all_category_qcp(self):
        """A QCP scoped to the 'All' category must match any product."""
        all_category = self.env.ref('product.product_category_all')
        qcp = self._make_qcp(
            product_category_ids=[(6, 0, [all_category.id])],
        )
        mo = self._make_mo(product=self.product)
        mo.action_confirm()
        self.assertIn(qcp, mo.quality_control_point_ids)

    def test_confirm_skips_wrong_operation_type(self):
        """A QCP bound to a different picking type must not be detected."""
        qcp = self._make_qcp(picking_type=self.picking_type_in)
        mo = self._make_mo()
        mo.action_confirm()
        self.assertNotIn(qcp, mo.quality_control_point_ids)

    def test_confirm_no_qcp_leaves_is_quality_check_false(self):
        """When no matching QCP exists, is_quality_check must remain False."""
        # Ensure no QCPs exist for the mfg picking type
        self.env['quality.control.point'].search(
            [('operation_type_ids', 'in', self.picking_type_mfg.id)]
        ).write({'active': False})
        mo = self._make_mo()
        mo.action_confirm()
        self.assertFalse(mo.is_quality_check)

    def test_confirm_multiple_qcps_all_linked(self):
        """All matching QCPs should be linked when multiple qualify."""
        action2 = self.env['inspection.action'].create({'name': 'Step B'})
        qcp1 = self._make_qcp(control_type='operation')
        qcp2 = self._make_qcp(
            extra_inspections=[{
                'inspection_action_id': action2.id,
                'inspection_type_id': self.inspection_type_pass_fail.id,
            }],
            control_type='operation',
        )
        mo = self._make_mo()
        mo.action_confirm()
        self.assertIn(qcp1, mo.quality_control_point_ids)
        self.assertIn(qcp2, mo.quality_control_point_ids)

    # ════════════════════════════════════════════════════════════════════
    # 3. action_quality_check — check creation
    # ════════════════════════════════════════════════════════════════════

    def test_action_quality_check_creates_checks(self):
        """action_quality_check must create quality.check records for the MO."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo()
        mo.action_confirm()
        mo.qty_producing = 3.0
        mo.action_quality_check()
        self.assertTrue(mo.quality_check_ids)

    def test_action_quality_check_links_mo_id(self):
        """Created quality.check records must back-link to the MO via mo_id."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo()
        mo.action_confirm()
        mo.qty_producing = 2.0
        mo.action_quality_check()
        for qc in mo.quality_check_ids:
            self.assertEqual(qc.mo_id, mo)

    def test_action_quality_check_sets_created_flag(self):
        """is_quality_check_created must be True after action_quality_check."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo()
        mo.action_confirm()
        mo.qty_producing = 1.0
        mo.action_quality_check()
        self.assertTrue(mo.is_quality_check_created)

    def test_action_quality_check_idempotent(self):
        """Calling action_quality_check twice must not duplicate check records."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo()
        mo.action_confirm()
        mo.qty_producing = 4.0
        mo.action_quality_check()
        count_first = len(mo.quality_check_ids)
        mo.action_quality_check()
        self.assertEqual(len(mo.quality_check_ids), count_first)

    def test_action_quality_check_raises_on_zero_qty(self):
        """action_quality_check must raise UserError when product quantity is zero."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo(qty=0.0)
        with self.assertRaises(UserError):
            mo.action_confirm()

    def test_action_quality_check_quantity_type_percentage(self):
        """For control_type='quantity', check qty must be a percentage of qty_producing."""
        self._make_qcp(control_type='quantity', control_quantity=50)  # 50 %
        mo = self._make_mo(qty=10.0)
        mo.action_confirm()
        mo.qty_producing = 10.0
        mo.action_quality_check()
        self.assertTrue(mo.quality_check_ids)
        # At 50 % of 10 the expected quantity is 5
        qc = mo.quality_check_ids[0]
        self.assertEqual(qc.quantity, 5)

    def test_action_quality_check_copies_product(self):
        """Created quality.check must record the MO's product."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo(product=self.product)
        mo.action_confirm()
        mo.qty_producing = 1.0
        mo.action_quality_check()
        qc = mo.quality_check_ids[0]
        self.assertEqual(qc.product_id, self.product)

    def test_action_quality_check_copies_uom(self):
        """Created quality.check must inherit the MO's product UoM."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo()
        mo.action_confirm()
        mo.qty_producing = 2.0
        mo.action_quality_check()
        qc = mo.quality_check_ids[0]
        self.assertEqual(qc.uom_id, self.uom_unit)

    def test_action_quality_check_skips_non_matching_product(self):
        """A product-scoped QCP for a different product must not generate checks."""
        self._make_qcp(
            product_ids=[(6, 0, [self.product_other.id])],
            control_type='operation',
        )
        mo = self._make_mo(product=self.product)
        mo.action_confirm()
        mo.qty_producing = 3.0
        mo.action_quality_check()
        # No checks expected because the QCP product doesn't match the MO product
        self.assertFalse(mo.quality_check_ids)

    # ════════════════════════════════════════════════════════════════════
    # 4. _compute_quality_checks — counters and is_quality_check flag
    # ════════════════════════════════════════════════════════════════════

    def test_qc_count_estimated_before_checks_created(self):
        """qc_count should reflect inspection template count before checks are created."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo()
        mo.action_confirm()
        # Before action_quality_check, count is estimated from QCP inspection lines
        self.assertGreater(mo.qc_count, 0)

    def test_qc_checked_count_zero_initially(self):
        """qc_checked_count must be 0 right after MO confirmation (no checks yet)."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo()
        mo.action_confirm()
        self.assertEqual(mo.qc_checked_count, 0)

    def test_qc_count_reflects_actual_lines_after_creation(self):
        """After action_quality_check, qc_count should equal total check line count."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo()
        mo.action_confirm()
        mo.qty_producing = 1.0
        mo.action_quality_check()
        expected = sum(len(qc.quality_check_line_ids) for qc in mo.quality_check_ids)
        self.assertEqual(mo.qc_count, expected)

    def test_qc_checked_count_increments_as_lines_checked(self):
        """qc_checked_count must increase when a check line is marked is_checked."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo()
        mo.action_confirm()
        mo.qty_producing = 1.0
        mo.action_quality_check()
        self.assertEqual(mo.qc_checked_count, 0)
        first_line = mo.quality_check_ids[0].quality_check_line_ids[0]
        first_line.write({'is_checked': True, 'status': 'pass'})
        self.assertEqual(mo.qc_checked_count, 1)

    def test_is_quality_check_cleared_when_all_lines_done(self):
        """is_quality_check must become False once every check line is completed."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo()
        mo.action_confirm()
        mo.qty_producing = 1.0
        mo.action_quality_check()
        # Mark every line checked
        for qc in mo.quality_check_ids:
            for line in qc.quality_check_line_ids:
                line.write({'is_checked': True, 'status': 'pass'})
        # Force recompute
        mo._compute_quality_checks()
        self.assertFalse(mo.is_quality_check)

    def test_qc_count_zero_with_no_qcps(self):
        """An MO with no linked QCPs must have qc_count = 0."""
        mo = self._make_mo()
        mo.action_confirm()
        self.assertEqual(mo.qc_count, 0)

    # ════════════════════════════════════════════════════════════════════
    # 5. action_view_quality_check
    # ════════════════════════════════════════════════════════════════════

    def test_action_view_quality_check_returns_act_window(self):
        """action_view_quality_check must return an ir.actions.act_window."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo()
        mo.action_confirm()
        mo.qty_producing = 1.0
        mo.action_quality_check()
        action = mo.action_view_quality_check()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'quality.check')
        self.assertIn('tree', action['view_mode'])

    def test_action_view_quality_check_domain_filters_to_mo(self):
        """The act_window domain must be restricted to this MO's quality_check_ids."""
        self._make_qcp(control_type='operation')
        mo = self._make_mo()
        mo.action_confirm()
        mo.qty_producing = 1.0
        mo.action_quality_check()
        action = mo.action_view_quality_check()
        domain_ids = action['domain'][0][2]
        for qc in mo.quality_check_ids:
            self.assertIn(qc.id, domain_ids)

    def test_action_view_quality_check_empty_domain_when_no_checks(self):
        """action_view_quality_check on a fresh MO (no checks) returns empty domain."""
        mo = self._make_mo()
        mo.action_confirm()
        action = mo.action_view_quality_check()
        # domain should be [('id', 'in', [])]
        self.assertEqual(action['domain'][0][2], [])
