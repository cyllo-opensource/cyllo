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
from odoo.tests import common


class TestOcrDigitization(common.TransactionCase):
    """Tests for the OCR keyword mapping used by document digitization."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.keyword_qty = cls.env['ocr.keyword'].create({'name': 'Quantity'})
        cls.keyword_qty_alt = cls.env['ocr.keyword'].create({'name': 'Qty'})
        cls.field_product_qty = cls.env['ir.model.fields']._get(
            'purchase.order.line', 'product_qty')
        cls.field_price_unit = cls.env['ir.model.fields']._get(
            'purchase.order.line', 'price_unit')

    # -------------------------------------------------------------------------
    # ocr.keyword
    # -------------------------------------------------------------------------
    def test_keyword_creation(self):
        """A keyword stores the label read from the scanned document."""
        self.assertEqual(self.keyword_qty.name, 'Quantity')

    def test_keyword_is_searchable(self):
        """Keywords can be looked up by name."""
        found = self.env['ocr.keyword'].search([('name', '=', 'Qty')])
        self.assertIn(self.keyword_qty_alt, found)

    # -------------------------------------------------------------------------
    # purchase.line.field.details
    # -------------------------------------------------------------------------
    def test_mapping_links_field_and_keywords(self):
        """A mapping ties one purchase line field to several keywords."""
        mapping = self.env['purchase.line.field.details'].create({
            'purchase_line_field_id': self.field_product_qty.id,
            'line_field_keyword_ids': [
                (6, 0, (self.keyword_qty | self.keyword_qty_alt).ids)],
        })
        self.assertEqual(mapping.purchase_line_field_id, self.field_product_qty)
        self.assertEqual(len(mapping.line_field_keyword_ids), 2)
        self.assertIn(self.keyword_qty, mapping.line_field_keyword_ids)

    def test_mapping_field_domain_targets_purchase_lines(self):
        """The field selector is restricted to mappable purchase line fields."""
        domain = self.env['purchase.line.field.details']._fields[
            'purchase_line_field_id'].domain
        self.assertIn("'purchase.order.line'", domain)
        for fname in ('product_id', 'product_qty', 'price_unit', 'taxes_id',
                      'discount', 'default_code'):
            self.assertIn(f"'{fname}'", domain)

    def test_several_fields_can_be_mapped(self):
        """Each purchase line field gets its own mapping record."""
        self.env['purchase.line.field.details'].create({
            'purchase_line_field_id': self.field_product_qty.id,
            'line_field_keyword_ids': [(6, 0, self.keyword_qty.ids)],
        })
        price_keyword = self.env['ocr.keyword'].create({'name': 'Unit Price'})
        self.env['purchase.line.field.details'].create({
            'purchase_line_field_id': self.field_price_unit.id,
            'line_field_keyword_ids': [(6, 0, price_keyword.ids)],
        })
        mappings = self.env['purchase.line.field.details'].search([
            ('purchase_line_field_id', 'in',
             (self.field_product_qty | self.field_price_unit).ids),
        ])
        self.assertEqual(len(mappings), 2)

    # -------------------------------------------------------------------------
    # product.template
    # -------------------------------------------------------------------------
    def test_product_ocr_flag_defaults_to_false(self):
        """Manually created products are not flagged as OCR generated."""
        product = self.env['product.template'].create({'name': 'Manual Product'})
        self.assertFalse(product.ocr_product)

    def test_product_ocr_flag_can_be_set(self):
        """Products created by the digitization flow can be flagged."""
        product = self.env['product.template'].create({
            'name': 'Scanned Product',
            'ocr_product': True,
        })
        self.assertTrue(product.ocr_product)
        self.assertIn(product, self.env['product.template'].search([
            ('ocr_product', '=', True),
        ]))
