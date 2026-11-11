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

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

EXTEND_PARAM = 'cyllo_purchase.is_extend_warranty_purchase'


@tagged('post_install', '-at_install')
class TestPurchaseWarranty(TransactionCase):
    """Tests for Warranty Purchase: purchase lines, receipts and the wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Vendor',
            'email': 'vendor@test.com',
        })
        cls.category_warranty = cls.env['product.category'].create({
            'name': 'Category with Warranty',
            'warranty_period': 12,
            'warranty_period_unit': 'month',
        })
        cls.category_no_warranty = cls.env['product.category'].create({
            'name': 'Category no Warranty',
            'warranty_period': 0,
            'warranty_period_unit': 'month',
        })
        cls.product_warranty = cls.env['product.product'].create({
            'name': 'Product with Warranty',
            'type': 'product',
            'categ_id': cls.category_warranty.id,
        })
        cls.product_no_warranty = cls.env['product.product'].create({
            'name': 'Product no Warranty',
            'type': 'product',
            'categ_id': cls.category_no_warranty.id,
        })

    def setUp(self):
        super().setUp()
        self.now = fields.Datetime.now()
        self.today = fields.Date.today()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _create_po(self, products=None, **po_vals):
        """Create a draft PO with one line (qty 1) per given product."""
        products = products or [self.product_warranty]
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'date_order': self.now,
            **po_vals,
        })
        lines = self.env['purchase.order.line']
        for product in products:
            lines |= self.env['purchase.order.line'].create({
                'order_id': po.id,
                'product_id': product.id,
                'product_qty': 1,
                'price_unit': 100.0,
            })
        return po, lines

    def _base_expiration(self, date):
        """Warranty expiration of the warranty product, without extension."""
        return fields.Date.to_date(
            self.product_warranty._get_warranty_expiration_date(date))

    # ------------------------------------------------------------------
    # purchase order line
    # ------------------------------------------------------------------
    def test_purchase_order_line_warranty_expiration_date(self):
        """Draft uses date_order, confirmed/approved uses date_approve."""
        po, lines = self._create_po(
            [self.product_warranty, self.product_no_warranty])
        line_warranty, line_no_warranty = lines

        # Draft: date_approve is empty, so date_order is used.
        self.assertFalse(po.date_approve)
        self.assertEqual(
            line_warranty.purchase_warranty_expiration_date,
            self._base_expiration(po.date_order))
        self.assertFalse(line_no_warranty.purchase_warranty_expiration_date)

        # date_approve takes precedence once set.
        approve_date = self.now - timedelta(days=10)
        po.write({'date_approve': approve_date, 'state': 'purchase'})
        self.assertEqual(
            line_warranty.purchase_warranty_expiration_date,
            self._base_expiration(approve_date))
        self.assertFalse(line_no_warranty.purchase_warranty_expiration_date)

    def test_purchase_order_line_warranty_extension(self):
        """Extension days are added on top of the base warranty."""
        po, lines = self._create_po()
        line = lines
        base_exp = self._base_expiration(po.date_order)
        self.assertEqual(line.purchase_warranty_expiration_date, base_exp)

        # The extension is stored in days and added with relativedelta(days=N).
        for extension_days in (182, 182 + 730, 182 + 730 + 15):
            line.warranty_extension_days = extension_days
            self.assertEqual(
                line.purchase_warranty_expiration_date,
                base_exp + relativedelta(days=extension_days))

        # No extension -> back to the base date.
        line.warranty_extension_days = 0
        self.assertEqual(line.purchase_warranty_expiration_date, base_exp)

    def test_purchase_order_line_no_warranty_ignores_extension(self):
        """A product without warranty never gets an expiration date."""
        _po, lines = self._create_po([self.product_no_warranty])
        lines.warranty_extension_days = 90
        self.assertFalse(lines.purchase_warranty_expiration_date)
        self.assertFalse(lines.is_under_warranty)

    def test_purchase_order_line_is_under_warranty_and_search(self):
        """is_under_warranty compute and its custom search method."""
        po, lines = self._create_po()
        line = lines

        # Expires in ~12 months -> under warranty.
        self.assertTrue(line.is_under_warranty)
        self.assertIn(line, self.env['purchase.order.line'].search([
            ('id', '=', line.id), ('is_under_warranty', '=', True)]))

        # 500 days ago + 12 months expired about 135 days ago.
        po.write({
            'date_approve': self.now - timedelta(days=500),
            'state': 'purchase',
        })
        self.assertFalse(line.is_under_warranty)
        self.assertNotIn(line, self.env['purchase.order.line'].search([
            ('id', '=', line.id), ('is_under_warranty', '=', True)]))
        self.assertIn(line, self.env['purchase.order.line'].search([
            ('id', '=', line.id), ('is_under_warranty', '=', False)]))

        # An extension long enough brings it back under warranty.
        line.warranty_extension_days = 400
        self.assertTrue(line.is_under_warranty)

    # ------------------------------------------------------------------
    # purchase order
    # ------------------------------------------------------------------
    def test_purchase_order_display_extend_warranty(self):
        """The button flag depends on the setting and on warranty lines."""
        params = self.env['ir.config_parameter'].sudo()
        po, _lines = self._create_po()

        params.set_param(EXTEND_PARAM, False)
        po._compute_display_extend_warranty()
        self.assertFalse(po.display_extend_warranty)

        params.set_param(EXTEND_PARAM, True)
        po._compute_display_extend_warranty()
        self.assertTrue(po.display_extend_warranty)

        # Setting on, but no line under warranty -> no button.
        po_no_war, _l = self._create_po([self.product_no_warranty])
        po_no_war._compute_display_extend_warranty()
        self.assertFalse(po_no_war.display_extend_warranty)

    def test_purchase_order_action_extend_warranty_and_wizard(self):
        """Action guards and the wizard adding extension days."""
        po_no_war, _l = self._create_po([self.product_no_warranty])
        with self.assertRaises(UserError):
            po_no_war.action_extend_warranty()

        po_war, lines = self._create_po()
        po_line = lines
        action = po_war.action_extend_warranty()
        self.assertEqual(action.get('res_model'), 'warranty.extension.wizard')
        # A single warranty line is preselected.
        self.assertEqual(
            action['context'].get('default_purchase_line_ids'),
            [(6, 0, po_line.ids)])

        wizard = self.env['warranty.extension.wizard'].with_context(
            action.get('context')).create({
                'purchase_order_id': po_war.id,
                'purchase_line_ids': [(6, 0, po_line.ids)],
                'extension_period': 3,
                'extension_unit': 'month',
            })
        initial_extension = po_line.warranty_extension_days
        wizard.action_confirm()
        # 3 months are converted to 90 days by cyllo_warranty_base.
        self.assertEqual(po_line.warranty_extension_days, initial_extension + 90)

        # Extending again accumulates.
        wizard.action_confirm()
        self.assertEqual(po_line.warranty_extension_days, initial_extension + 180)

    def test_wizard_only_changes_selected_lines(self):
        """Lines not selected in the wizard keep their extension."""
        po, lines = self._create_po(
            [self.product_warranty, self.product_warranty])
        line_a, line_b = lines
        wizard = self.env['warranty.extension.wizard'].create({
            'purchase_order_id': po.id,
            'purchase_line_ids': [(6, 0, line_a.ids)],
            'extension_period': 3,
            'extension_unit': 'month',
        })
        wizard.action_confirm()
        self.assertEqual(line_a.warranty_extension_days, 90)
        self.assertEqual(line_b.warranty_extension_days, 0)

    # ------------------------------------------------------------------
    # stock move line
    # ------------------------------------------------------------------
    def _get_receipt_move_line(self, po, po_line):
        po.button_confirm()
        picking = po.picking_ids
        self.assertTrue(picking)
        move = picking.move_ids.filtered(lambda m: m.purchase_line_id == po_line)
        self.assertTrue(move)
        move_line = move.move_line_ids[:1] or self.env['stock.move.line'].create({
            'move_id': move.id,
            'product_id': self.product_warranty.id,
            'product_uom_id': self.product_warranty.uom_id.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'quantity': 1.0,
        })
        return move_line

    def test_stock_move_line_warranty_propagation(self):
        """The PO line expiration date is copied to the receipt move line."""
        po, lines = self._create_po()
        po_line = lines
        move_line = self._get_receipt_move_line(po, po_line)
        self.assertTrue(po_line.purchase_warranty_expiration_date)
        self.assertEqual(
            move_line.purchase_warranty_expiration_date,
            po_line.purchase_warranty_expiration_date)

    def test_stock_move_line_follows_extension(self):
        """Extending the warranty updates the already created move line."""
        po, lines = self._create_po()
        po_line = lines
        move_line = self._get_receipt_move_line(po, po_line)
        before = move_line.purchase_warranty_expiration_date

        po_line.warranty_extension_days = 30
        self.assertEqual(
            move_line.purchase_warranty_expiration_date,
            before + relativedelta(days=30))
        self.assertEqual(
            move_line.purchase_warranty_expiration_date,
            po_line.purchase_warranty_expiration_date)