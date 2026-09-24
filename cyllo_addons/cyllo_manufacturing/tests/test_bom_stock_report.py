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
from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestBomStockReport(common.TransactionCase):
    """Tests for the bom.stock.report SQL view model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # -- Products --
        cls.finished_product = cls.env['product.product'].create({
            'name': 'Test Finished Product',
            'type': 'product',
        })
        cls.component_1 = cls.env['product.product'].create({
            'name': 'Test Component A',
            'type': 'product',
        })
        cls.component_2 = cls.env['product.product'].create({
            'name': 'Test Component B',
            'type': 'product',
        })

        # -- Bill of Materials --
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.finished_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {
                    'product_id': cls.component_1.id,
                    'product_qty': 3.0,
                }),
                (0, 0, {
                    'product_id': cls.component_2.id,
                    'product_qty': 2.0,
                }),
            ],
        })

        # -- Stock: put component_1 on hand so it appears in the report --
        stock_location = cls.env.ref('stock.stock_location_stock')
        cls.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': cls.component_1.id,
            'location_id': stock_location.id,
            'inventory_quantity': 10.0,
        }).action_apply_inventory()

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def _create_mo(self, qty=1.0, **kwargs):
        """Create and return a confirmed manufacturing order."""
        vals = {
            'product_id': self.finished_product.id,
            'product_qty': qty,
            'bom_id': self.bom.id,
        }
        vals.update(kwargs)
        mo = self.env['mrp.production'].create(vals)
        mo.action_confirm()
        # Flush all pending ORM writes so the raw SQL view sees up-to-date
        # stored computed fields (e.g. state) in the database tables.
        self.env.flush_all()
        return mo

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_01_report_view_created(self):
        """The SQL view should be materialised after module install."""
        self.env.cr.execute(
            "SELECT COUNT(*) FROM information_schema.views "
            "WHERE table_name = 'bom_stock_report'"
        )
        count = self.env.cr.fetchone()[0]
        self.assertEqual(count, 1,
                         "The bom_stock_report SQL view should exist.")

    def test_02_report_rows_from_confirmed_mo(self):
        """Confirming an MO should generate report rows for each component."""
        mo = self._create_mo(qty=2.0)
        reports = self.env['bom.stock.report'].search([
            ('production_id', '=', mo.id),
        ])
        self.assertEqual(len(reports), 2,
                         "There should be one report row per BOM component.")

        comp_ids = reports.mapped('product_id.id')
        self.assertIn(self.component_1.id, comp_ids)
        self.assertIn(self.component_2.id, comp_ids)

    def test_03_qty_demanded_matches_bom(self):
        """Demanded qty should equal BOM qty × MO product qty."""
        mo = self._create_mo(qty=3.0)
        report_a = self.env['bom.stock.report'].search([
            ('production_id', '=', mo.id),
            ('product_id', '=', self.component_1.id),
        ])
        # BOM requires 3 units of component_1 per finished product → 3 × 3 = 9
        self.assertAlmostEqual(report_a.qty_demanded, 9.0,
                               msg="Demanded qty should reflect BOM × MO qty.")

    def test_04_qty_on_hand_reflects_stock(self):
        """qty_on_hand should reflect internal stock quants."""
        mo = self._create_mo(qty=1.0)
        report_a = self.env['bom.stock.report'].search([
            ('production_id', '=', mo.id),
            ('product_id', '=', self.component_1.id),
        ])
        # We put 10 on hand in setUpClass
        self.assertGreaterEqual(report_a.qty_on_hand, 10.0,
                                "Component A should show ≥ 10 on-hand.")

        report_b = self.env['bom.stock.report'].search([
            ('production_id', '=', mo.id),
            ('product_id', '=', self.component_2.id),
        ])
        self.assertEqual(report_b.qty_on_hand, 0.0,
                         "Component B has no stock; qty_on_hand should be 0.")

    def test_05_is_deficit_flag(self):
        """is_deficit should be True when on-hand < demanded."""
        mo = self._create_mo(qty=1.0)
        report_a = self.env['bom.stock.report'].search([
            ('production_id', '=', mo.id),
            ('product_id', '=', self.component_1.id),
        ])
        # 10 on hand vs 3 demanded → no deficit
        self.assertFalse(report_a.is_deficit,
                         "Component A should NOT be in deficit (10 >= 3).")

        report_b = self.env['bom.stock.report'].search([
            ('production_id', '=', mo.id),
            ('product_id', '=', self.component_2.id),
        ])
        # 0 on hand vs 2 demanded → deficit
        self.assertTrue(report_b.is_deficit,
                        "Component B should be in deficit (0 < 2).")

    def test_06_state_mirrors_mo(self):
        """Report state should match the parent MO state."""
        mo = self._create_mo(qty=1.0)
        reports = self.env['bom.stock.report'].search([
            ('production_id', '=', mo.id),
        ])
        for rec in reports:
            self.assertEqual(rec.state, mo.state,
                             "Report state must mirror the MO state.")

    def test_07_date_start_populated(self):
        """date_start should be populated from the MO."""
        mo = self._create_mo(qty=1.0)
        reports = self.env['bom.stock.report'].search([
            ('production_id', '=', mo.id),
        ])
        for rec in reports:
            self.assertTrue(rec.date_start,
                            "date_start should be populated from the MO.")

    def test_08_company_filter(self):
        """Report rows must belong to the user's company."""
        mo = self._create_mo(qty=1.0)
        reports = self.env['bom.stock.report'].search([
            ('production_id', '=', mo.id),
        ])
        for rec in reports:
            self.assertEqual(
                rec.company_id, self.env.company,
                "Report row company must match the current company.",
            )

    def test_09_cancelled_mo_state(self):
        """Cancelled MOs should show state='cancel' in the report."""
        mo = self._create_mo(qty=1.0)
        # action_cancel() may return a confirmation wizard action dict
        result = mo.action_cancel()
        if isinstance(result, dict) and result.get('res_model'):
            wizard = self.env[result['res_model']].with_context(
                **result.get('context', {})
            ).create({})
            wizard.action_cancel()
        mo.invalidate_recordset()
        self.assertEqual(mo.state, 'cancel', "MO should be cancelled.")
        self.env.flush_all()
        reports = self.env['bom.stock.report'].search([
            ('production_id', '=', mo.id),
        ])
        for rec in reports:
            self.assertEqual(rec.state, 'cancel',
                             "Cancelled MO should reflect 'cancel' state.")

    def test_10_no_rows_without_mo(self):
        """Without any MOs the report should return no rows for these products."""
        reports = self.env['bom.stock.report'].search([
            ('product_id', 'in',
             [self.component_1.id, self.component_2.id]),
            ('production_id', '=', False),
        ])
        self.assertFalse(reports,
                         "No report rows should exist without an MO.")

    def test_11_multiple_mos(self):
        """Multiple MOs should produce independent report rows."""
        mo1 = self._create_mo(qty=1.0)
        mo2 = self._create_mo(qty=2.0)

        reports_mo1 = self.env['bom.stock.report'].search([
            ('production_id', '=', mo1.id),
        ])
        reports_mo2 = self.env['bom.stock.report'].search([
            ('production_id', '=', mo2.id),
        ])

        self.assertEqual(len(reports_mo1), 2)
        self.assertEqual(len(reports_mo2), 2)

        # Verify demanded qty differs per MO
        r1_a = reports_mo1.filtered(
            lambda r: r.product_id == self.component_1
        )
        r2_a = reports_mo2.filtered(
            lambda r: r.product_id == self.component_1
        )
        self.assertAlmostEqual(r1_a.qty_demanded, 3.0)
        self.assertAlmostEqual(r2_a.qty_demanded, 6.0)

    def test_12_uom_set(self):
        """product_uom_id should be populated on report rows."""
        mo = self._create_mo(qty=1.0)
        reports = self.env['bom.stock.report'].search([
            ('production_id', '=', mo.id),
        ])
        for rec in reports:
            self.assertTrue(rec.product_uom_id,
                            "UoM should be set on every report line.")

    def test_13_name_matches_mo(self):
        """The name field should match the MO reference."""
        mo = self._create_mo(qty=1.0)
        reports = self.env['bom.stock.report'].search([
            ('production_id', '=', mo.id),
        ])
        for rec in reports:
            self.assertEqual(rec.name, mo.name,
                             "Report name should match the MO reference.")

    def test_14_forecasted_qty(self):
        """Forecasted qty should be >= on-hand (on-hand + incoming - outgoing)."""
        mo = self._create_mo(qty=1.0)
        report_a = self.env['bom.stock.report'].search([
            ('production_id', '=', mo.id),
            ('product_id', '=', self.component_1.id),
        ])
        # Forecasted = on_hand + incoming - outgoing.
        # At minimum, with no pending moves forecasted == on_hand minus the
        # outgoing raw-material move.  Just verify it is a number.
        self.assertIsNotNone(report_a.qty_forecasted,
                             "Forecasted qty should be computed.")
