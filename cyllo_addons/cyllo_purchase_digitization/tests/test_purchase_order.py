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
import base64
import json
from unittest.mock import MagicMock, patch

import pandas as pd
from odoo.tests.common import TransactionCase


class TestPurchaseOrderDigitization(TransactionCase):
    """
    Test suite for Cyllo Purchase Digitization functionality.
    Covers:
        • OCR enabling/disabling logic
        • OCR PDF processing logic (manual/AI)
        • Partner extraction logic (keyword + AI)
        . Get Partner Details AI logic
    """

    def setUp(self):
        """
        Shared setup for all tests.

        Creates:
            - Dummy vendor (required for purchase.order)
            - Partner "ABC Traders" for window/full-text tests
            - Active digitization config
            - Field details for partner_id
            - Keyword "Vendor"
            - Sample PDF attachment
        """
        super().setUp()

        self.dummy_partner = self.env['res.partner'].create({
            'name': 'Dummy Vendor'
        })
        self.partner_abc = self.env['res.partner'].create({
            'name': 'ABC Traders'
        })
        self.config = self.env['purchase.digitization'].create({
            'name': 'Config',
            'active_configuration': True
        })
        field_details = self.env['purchase.field.details'].create({
            'purchase_digitization_id': self.config.id,
            'purchase_field_id': self.env['ir.model.fields']._get(
                'purchase.order', 'partner_id'
            ).id,
        })
        keyword = self.env['ocr.keyword'].create({'name': 'Vendor'})
        field_details.write({'field_keyword_ids': [(4, keyword.id)]})
        self.attachment = self.env['ir.attachment'].create({
            'name': 'test.pdf',
            'datas': base64.b64encode(b"PDF DATA"),
            'mimetype': 'application/pdf'
        })

        self.po = self.env['purchase.order'].create({
            'partner_id': self.dummy_partner.id,
        })

        self.test_product = self.env['product.product'].create({
            'name': 'Laptop',
            'default_code': 'LP100',
            'standard_price': 0.0,
            'list_price': 1200.0,
        })

        self.sample_purchase_line_values = {
            "product_qty": ['2'],
            "price_unit": ['1200'],
            "discount": ['10'],
            "taxes_id": ['18%']
        }

    def test_compute_ocr_digitize_enabled(self):
        """
        Validate _compute_ocr_digitize_enabled() for:
            - request_digitize
            - not_digitize
            - auto_digitize (calls action_send_digitization)
        """

        fake_config = MagicMock()
        fake_config.automation_type = 'request_digitize'

        with patch(
                'odoo.addons.cyllo_purchase_digitization.models.purchase_order.models.Model.search',
                return_value=fake_config
        ):
            self.po._compute_ocr_digitize_enabled()
            self.assertTrue(self.po.ocr_digitize_enabled)

        fake_config.automation_type = 'not_digitize'
        with patch(
                'odoo.addons.cyllo_purchase_digitization.models.purchase_order.models.Model.search',
                return_value=fake_config
        ):
            self.po._compute_ocr_digitize_enabled()
            self.assertFalse(self.po.ocr_digitize_enabled)

        fake_config.automation_type = 'auto_digitize'
        self.po.message_main_attachment_id = self.attachment.id

        with patch(
                'odoo.addons.cyllo_purchase_digitization.models.purchase_order.models.Model.search',
                return_value=fake_config
        ), patch.object(
            type(self.po),
            'action_send_digitization',
            return_value=True
        ) as mock_action:
            self.po._compute_ocr_digitize_enabled()
            mock_action.assert_called_once()

    def test_action_send_digitization(self):
        """
        Test action_send_digitization():

            1. Non-PDF → fail
            2. PDF but OCR exception → return wizard
            3. Manual digitization → all manual helpers called
            4. AI digitization → all AI helpers called
        """

        non_pdf = self.env['ir.attachment'].create({
            'name': 'file.png',
            'datas': base64.b64encode(b"PNG"),
            'mimetype': 'image/png'
        })

        self.po.message_main_attachment_id = non_pdf.id
        self.po.action_send_digitization()
        self.assertTrue(self.po.ocr_digitize_failed)
        self.assertIn("PDF", self.po.ocr_digitize_message)

        self.po.message_main_attachment_id = self.attachment.id
        with patch("fitz.open", side_effect=Exception("OCR error")):
            result = self.po.action_send_digitization()
        self.assertTrue(self.po.ocr_digitize_failed)
        self.assertIsInstance(result, dict)

        self.config.write({'automation_method': 'manual_digitization'})

        with patch("fitz.open"), \
                patch("camelot.read_pdf"), \
                patch.object(type(self.po), "find_partner") as f1, \
                patch.object(type(self.po), "action_find_field_values") as f2, \
                patch.object(type(self.po), "action_get_purchase_line_columns", return_value={}) as f3, \
                patch.object(type(self.po), "action_create_products", return_value=[]) as f4, \
                patch.object(type(self.po), "get_order_line") as f5:
            self.po.action_send_digitization()
            f1.assert_called_once()
            f2.assert_called_once()
            f3.assert_called_once()
            f4.assert_called_once()
            f5.assert_called_once()

        self.config.write({'automation_method': 'ai_digitization'})
        mock_page = MagicMock()
        mock_page.get_text.return_value = "OCR text"

        with patch("fitz.open", MagicMock(return_value=[mock_page])), \
                patch.object(type(self.po), "get_details_ai", return_value={"ok": True}) as a1, \
                patch.object(type(self.po), "get_quotation_details", return_value={"q": True}) as a2, \
                patch.object(type(self.po), "get_product_details", return_value={"p": True}) as a3, \
                patch.object(type(self.po), "find_partner_ai") as a4, \
                patch.object(type(self.po), "action_find_field_values_ai") as a5, \
                patch.object(type(self.po), "action_find_product") as a6:
            self.po.action_send_digitization()
            a1.assert_called_once()
            a2.assert_called_once()
            a3.assert_called_once()
            a4.assert_called_once()
            a5.assert_called_once()
            a6.assert_called_once()

    def test_find_partner(self):
        """
        Test find_partner() logic:
            1. Partner found in text window
            2. Partner found in full text
            3. No match → AI fallback → partner created
            4. No match & AI returns None → no change
        """

        self.po.find_partner("Vendor ABC Traders purchase order")
        self.assertEqual(self.po.partner_id, self.partner_abc)

        self.po.partner_id = self.dummy_partner.id
        self.po.find_partner("Vendor info later ABC Traders")
        self.assertEqual(self.po.partner_id, self.partner_abc)
        with patch.object(type(self.po), "get_partner_details_ai",
                          return_value={"partner_name": "New Vendor"}):
            self.po.partner_id = self.dummy_partner.id
            self.po.find_partner("No match")
        self.assertIn("New Vendor", self.env['res.partner'].search([]).mapped("name"))
        with patch.object(type(self.po), "get_partner_details_ai", return_value=None):
            self.po.partner_id = self.dummy_partner.id
            self.po.find_partner("Nothing")
            self.assertEqual(self.po.partner_id, self.dummy_partner)

    def test_get_partner_details_ai(self):
        """Test get_partner_details_ai() for all response types."""

        expected_data = {
            "partner_name": "ABC Traders",
            "street": "Street 1",
            "city": "Cochin",
            "state": "Kerala",
            "country": "India"
        }
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "success", "content": json.dumps(expected_data)}
        ):
            result = self.po.get_partner_details_ai("sample text")
            self.assertEqual(result, expected_data)
        noisy_response = (
            'RANDOM IGNORE BEFORE {'
            '"partner_name": "ABC Traders", '
            '"street": "Street 1", '
            '"city": "Cochin", '
            '"state": "Kerala", '
            '"country": "India" } EXTRA'
        )
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "success", "content": noisy_response}
        ):
            result = self.po.get_partner_details_ai("sample text")
            self.assertEqual(result, expected_data)
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "error_prompt_too_long"}
        ):
            self.po.get_partner_details_ai("sample text")
        self.assertTrue(self.po.ocr_digitize_failed)
        self.assertIn("Failed to Identify", self.po.ocr_digitize_message)
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "error"}
        ):
            self.po.get_partner_details_ai("sample text")
        self.assertTrue(self.po.ocr_digitize_failed)
        self.assertIn("Failed to Identify", self.po.ocr_digitize_message)
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                side_effect=Exception("API failure")
        ):
            self.po.get_partner_details_ai("sample text")
        self.assertTrue(self.po.ocr_digitize_failed)
        self.assertIn("Failed to Identify", self.po.ocr_digitize_message)

    def test_action_find_field_values(self):
        """
        Test action_find_field_values():
            1. Keyword match for char field → extract next word
            2. Keyword match for many2one → update field
            3. Incoterm code detection
        """

        char_field = self.env['ir.model.fields']._get('purchase.order', 'origin')
        field_char = self.env['purchase.field.details'].create({
            'purchase_digitization_id': self.config.id,
            'purchase_field_id': char_field.id,
        })
        keyword_char = self.env['ocr.keyword'].create({'name': 'Order'})
        field_char.write({'field_keyword_ids': [(4, keyword_char.id)]})
        self.po.action_find_field_values("Order ABC123 issued by vendor")
        self.assertEqual(self.po.origin, "ABC123")
        self.po.write({'origin': False})
        vendor_field = self.env['ir.model.fields']._get('purchase.order', 'partner_id')
        field_many2one = self.env['purchase.field.details'].create({
            'purchase_digitization_id': self.config.id,
            'purchase_field_id': vendor_field.id,
        })
        keyword_vendor = self.env['ocr.keyword'].create({'name': 'Vendor'})
        field_many2one.write({'field_keyword_ids': [(4, keyword_vendor.id)]})
        self.po.action_find_field_values("Vendor ABC Traders confirmed")
        self.assertEqual(self.po.partner_id, self.partner_abc)
        self.env['account.incoterms'].search([]).unlink()
        incoterm_record = self.env['account.incoterms'].create({
            'name': "Free On Board",
            'code': "FOB",
        })
        incoterm_field = self.env['ir.model.fields']._get('purchase.order', 'incoterm_id')
        field_incoterm = self.env['purchase.field.details'].create({
            'purchase_digitization_id': self.config.id,
            'purchase_field_id': incoterm_field.id,
        })
        keyword_incoterm = self.env['ocr.keyword'].create({'name': 'Incoterm'})
        field_incoterm.write({'field_keyword_ids': [(4, keyword_incoterm.id)]})
        self.po.action_find_field_values("Incoterm FOB shipment details")
        self.assertEqual(self.po.incoterm_id, incoterm_record)

    def test_action_get_purchase_line_columns(self):
        """
        Validate extraction:
            ✓ Qty
            ✓ Price
            ✓ Discount
            ✓ Tax
        """
        qty_field = self.env['ir.model.fields']._get('purchase.order.line', 'product_qty')
        tax_field = self.env['ir.model.fields']._get('purchase.order.line', 'taxes_id')
        price_field = self.env['ir.model.fields']._get('purchase.order.line', 'price_unit')
        discount_field = self.env['ir.model.fields']._get('purchase.order.line', 'discount')

        qty_detail = self.env['purchase.line.field.details'].create({
            'purchase_digitization_id': self.config.id,
            'purchase_line_field_id': qty_field.id,
        })
        tax_detail = self.env['purchase.line.field.details'].create({
            'purchase_digitization_id': self.config.id,
            'purchase_line_field_id': tax_field.id,
        })
        price_detail = self.env['purchase.line.field.details'].create({
            'purchase_digitization_id': self.config.id,
            'purchase_line_field_id': price_field.id,
        })
        discount_detail = self.env['purchase.line.field.details'].create({
            'purchase_digitization_id': self.config.id,
            'purchase_line_field_id': discount_field.id,
        })

        qty_keyword = self.env['ocr.keyword'].create({'name': 'Qty'})
        tax_keyword = self.env['ocr.keyword'].create({'name': 'Tax'})
        price_keyword = self.env['ocr.keyword'].create({'name': 'Price'})
        discount_keyword = self.env['ocr.keyword'].create({'name': 'Discount'})

        qty_detail.write({'line_field_keyword_ids': [(4, qty_keyword.id)]})
        tax_detail.write({'line_field_keyword_ids': [(4, tax_keyword.id)]})
        price_detail.write({'line_field_keyword_ids': [(4, price_keyword.id)]})
        discount_detail.write({'line_field_keyword_ids': [(4, discount_keyword.id)]})

        self.config.tax_type = "tax_per_line"

        combined_table = pd.DataFrame({
            "Column A": ["Item", "Laptop", "Mouse"],
            "Column B": ["Qty", "2 Unit", "5 Unit"],
            "Column C": ["Price", "$1200", "$25"],
            "Column D": ["Discount", "10%", "0%"],
            "Column E": ["Tax", "18%", "18%"],
        })
        self.env['uom.uom'].search([], limit=1).write({'name': 'Unit'})
        result = self.po.action_get_purchase_line_columns(combined_table, "Tax 18%")
        self.assertCountEqual(result["product_qty"], ['2', '5'])
        self.assertIn(1200.0, [float(str(v).replace(",", "")) for v in result["price_unit"]])
        self.assertTrue(any("10" in d for d in result["discount"]))
        self.assertCountEqual(result["taxes_id"], ['18%', '18%'])

    def test_get_order_line(self):
        """
        Validate:
            ✓ Line creation
            ✓ Correct product
            ✓ Qty, price, tax, discount assignment
        """

        table_data = [[
            ["Laptop", "LP100", "2", "$1200", "10%", "18%"],
            ["Mouse", "MS200", "5", "$30", "0%", "18%"],
        ]]

        self.po.get_order_line(table_data, self.sample_purchase_line_values)
        self.assertTrue(self.po.ocr_digitize_completed)
        self.assertFalse(self.po.ocr_digitize_failed)
        self.assertEqual(len(self.po.order_line), 1)
        line = self.po.order_line[0]
        self.assertEqual(line.product_id.id, self.test_product.id)
        self.assertEqual(line.product_qty, 2.0)
        self.assertIsInstance(line.price_unit, (int, float))
        self.assertGreaterEqual(line.price_unit, 0)
        self.assertTrue(str(int(line.discount)).isdigit())

    def test_find_product_price(self):
        """Test price extraction logic for find_product_price()."""

        product_data = {
            'id': self.test_product.id,
            'name': self.test_product.name,
            'default_code': 'LP100',
            'standard_price': 0,
        }
        row_data = ["Laptop", "LP100", "1200", "Extra", "Notes"]
        purchase_values = {"price_unit": ["1200"]}
        result = self.po.find_product_price(product_data.copy(), row_data, purchase_values)
        self.assertEqual(result['price_unit'], 1200.0)
        row_data_multiple = ["Laptop", "LP100", "1200", "10", "25"]
        result_2 = self.po.find_product_price(product_data.copy(), row_data_multiple, purchase_values)
        self.assertEqual(result_2['price_unit'], 10.0)
        product_data_standard = {
            'id': self.test_product.id,
            'name': self.test_product.name,
            'default_code': 'LP100',
            'standard_price': 999.0,
        }
        result_3 = self.po.find_product_price(product_data_standard.copy(), row_data, purchase_values)
        self.assertEqual(result_3['price_unit'], 999.0)
        row_dirty = ["1200.00", "Laptop", "LP100", "###", "30"]
        result_4 = self.po.find_product_price(product_data.copy(), row_dirty, purchase_values)
        self.assertEqual(result_4['price_unit'], 30.00)
        row_none = ["Laptop", "LP100", "Text", "NoPrice"]
        with self.assertRaises(IndexError):
            self.po.find_product_price(product_data.copy(), row_none, purchase_values)

    def test_find_product_quantity(self):
        """Test quantity extraction logic for find_product_quantity()."""

        product_data = {
            'id': self.test_product.id,
            'name': self.test_product.name,
            'default_code': 'LP100',
            'standard_price': 0,
        }
        purchase_values = {"product_qty": ['2', '5']}
        row_data = ["Laptop", "LP100", "2", "$1200", "10%", "18%"]
        result = self.po.find_product_quantity(product_data.copy(), row_data, purchase_values)
        self.assertEqual(result['product_qty'], 2.0)
        row_multi = ["Laptop", "LP100", "2", "5", "$1200", "Other"]
        result2 = self.po.find_product_quantity(product_data.copy(), row_multi, purchase_values)
        self.assertEqual(result2['product_qty'], 5.0)
        row_dirty = ["LP100", "Laptop", "1200", "###", "5"]
        result3 = self.po.find_product_quantity(product_data.copy(), row_dirty, purchase_values)
        self.assertEqual(result3['product_qty'], 5.0)
        row_no_match = ["Laptop", "LP100", "3", "7"]
        purchase_values_no_match = {"product_qty": []}
        result4 = self.po.find_product_quantity(product_data.copy(), row_no_match, purchase_values_no_match)
        self.assertEqual(
            float(result4['product_qty']),
            7.0)
        row_none = ["Laptop", "LP100", "NoQty"]
        with self.assertRaises(ValueError):
            self.po.find_product_quantity(product_data.copy(), row_none, purchase_values)

    def test_find_product_discount(self):
        """Test discount extraction logic for find_product_discount()."""

        product_data = {
            'id': self.test_product.id,
            'name': self.test_product.name,
            'default_code': 'LP100',
            'standard_price': 1200.00,
        }
        row_data = ["Laptop", "LP100", "$1200", "10", "Other"]
        purchase_values = {"discount": ["10"]}
        result1 = self.po.find_product_discount(product_data.copy(), row_data, purchase_values)
        self.assertEqual(result1['discount'], 10.0)
        row_multiple = ["Laptop", "LP100", "5", "12", "8"]
        purchase_values_multi = {"discount": ["5", "12", "8"]}
        result2 = self.po.find_product_discount(product_data.copy(), row_multiple, purchase_values_multi)
        self.assertEqual(result2['discount'], 12.0)
        row_no_match = ["Laptop", "LP100", "$1200", "N/A"]
        purchase_no_match = {"discount": []}
        result3 = self.po.find_product_discount(product_data.copy(), row_no_match, purchase_no_match)
        self.assertEqual(result3['discount'], 0.00)
        row_dirty = ["Laptop", "LP100", "Discount", "15"]
        purchase_dirty = {"discount": ["15"]}
        result4 = self.po.find_product_discount(product_data.copy(), row_dirty, purchase_dirty)
        self.assertEqual(result4['discount'], 15.0)
        row_missing_key = ["Laptop", "LP100", "$1200"]
        purchase_missing_key = {}
        result5 = self.po.find_product_discount(product_data.copy(), row_missing_key, purchase_missing_key)
        self.assertEqual(result5['discount'], 0.00)

    def test_action_create_products(self):
        """Test OCR-based product creation based on table row detection."""

        self.config.write({'product_creation_type': 'create_product'})
        product_field = self.env['ir.model.fields']._get('purchase.order.line', 'product_id')
        price_field = self.env['ir.model.fields']._get('purchase.order.line', 'price_unit')
        code_field = self.env['ir.model.fields']._get('purchase.order.line', 'default_code')
        detail_product = self.env['purchase.line.field.details'].create({
            'purchase_digitization_id': self.config.id,
            'purchase_line_field_id': product_field.id,
        })
        detail_code = self.env['purchase.line.field.details'].create({
            'purchase_digitization_id': self.config.id,
            'purchase_line_field_id': code_field.id,
        })
        detail_price = self.env['purchase.line.field.details'].create({
            'purchase_digitization_id': self.config.id,
            'purchase_line_field_id': price_field.id,
        })
        kw_product = self.env['ocr.keyword'].create({'name': 'Product'})
        kw_code = self.env['ocr.keyword'].create({'name': 'Code'})
        kw_price = self.env['ocr.keyword'].create({'name': 'Price'})
        detail_product.write({'line_field_keyword_ids': [(4, kw_product.id)]})
        detail_code.write({'line_field_keyword_ids': [(4, kw_code.id)]})
        detail_price.write({'line_field_keyword_ids': [(4, kw_price.id)]})
        combined_table = pd.DataFrame({
            "A": ["Product", "Mouse"],
            "B": ["Code", "MS200"],
            "C": ["Price", "300"],
        })
        purchase_values = {
            "product_id": ["Mouse"],
            "default_code": ["MS200"],
            "price_unit": ["300"],
        }
        result = self.po.action_create_products(combined_table, purchase_values)
        self.assertEqual(len(result), 1)
        created_product = result[0]
        self.assertTrue(created_product.ocr_product)
        self.assertEqual(created_product.name, "Mouse")
        self.assertEqual(created_product.default_code, "MS200")
        self.assertEqual(created_product.standard_price, 300.0)

    def test_action_retry_digitization(self):
        """
        Test action_retry_digitization():

        Validates:
            ✓ Order lines are cleared before retry
            ✓ Digitization is re-triggered
            ✓ Returns wizard action if digitization fails
            ✓ Does NOT return wizard when digitization succeeds
        """
        line = self.env['purchase.order.line'].create({
            'order_id': self.po.id,
            'product_id': self.test_product.id,
            'name': 'Test Line',
            'product_qty': 1,
            'price_unit': 100,
        })
        self.assertEqual(len(self.po.order_line), 1)
        with patch.object(type(self.po), "action_send_digitization", return_value=True) as mock_action:
            self.po.ocr_digitize_failed = True
            result = self.po.action_retry_digitization()
        mock_action.assert_called_once()
        self.assertEqual(len(self.po.order_line), 0)
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get("res_model"), "digitization.ai.wizard")
        self.assertIn('context', result)
        with patch.object(type(self.po), "action_send_digitization", return_value=True) as mock_action_success:
            self.po.ocr_digitize_failed = False
            result_success = self.po.action_retry_digitization()
        mock_action_success.assert_called()
        self.assertIsNone(result_success)

    def test_get_details_ai(self):
        """
        Test get_details_ai():

        Validates:
            ✓ Successful single response
            ✓ Successful multi-part response ("Continued in next message")
            ✓ Handles 'error_prompt_too_long'
            ✓ Handles generic failure response
            ✓ Handles exception gracefully and logs error
        """

        expected_text = "Extracted purchase quotation details."
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "success", "content": expected_text}
        ):
            result = self.po.get_details_ai("Sample text")
            self.assertEqual(result, expected_text)
        continued_part_1 = "Line 1. Continued in next message"
        continued_part_2 = " Final continuation."
        def mock_chat_api(url, params=None, timeout=30):
            if params.get("prompt") == "Sample text":
                return {"status": "success", "content": continued_part_1}
            return {"status": "success", "content": continued_part_2}

        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                side_effect=mock_chat_api
        ):
            result = self.po.get_details_ai("Sample text")
            self.assertEqual(result, continued_part_1 + continued_part_2)
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "error_prompt_too_long"}
        ):
            self.po.get_details_ai("Sample text")
            self.assertTrue(self.po.ocr_digitize_failed)
            self.assertIn("too long", self.po.ocr_digitize_message)
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "error"}
        ):
            self.po.get_details_ai("Sample text")
            self.assertTrue(self.po.ocr_digitize_failed)
            self.assertIn("failed", self.po.ocr_digitize_message.lower())
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                side_effect=Exception("API crashed")
        ):
            self.po.get_details_ai("Sample text")
            self.assertTrue(self.po.ocr_digitize_failed)
            self.assertIn("Failed", self.po.ocr_digitize_message)

    def test_get_quotation_details(self):
        """
        Test get_quotation_details():

        Validates:
            ✓ Successful clean JSON response
            ✓ JSON inside noisy surrounding text
            ✓ Handles 'error_prompt_too_long'
            ✓ Handles generic failure response
            ✓ Handles exceptions gracefully
        """

        sample_pdf_text = """
            Vendor Name: ABC Traders
            Reference: PQ-001
            Payment Terms: NET 30
            Incoterm: FOB Chennai
        """

        expected_dict = {
            "partner_name": "ABC Traders",
            "vendor_reference": "PQ-001",
            "payment_term": "NET 30",
            "incoterm": "FOB",
            "incoterm_location": "Chennai"
        }
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "success", "content": json.dumps(expected_dict)}
        ):
            result = self.po.get_quotation_details(sample_pdf_text)
            self.assertEqual(result, expected_dict)
        noisy_json = f"""
            RANDOM NOISE BEFORE
            {json.dumps(expected_dict)}
            EXTRA FOOTER
        """
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "success", "content": noisy_json}
        ):
            result = self.po.get_quotation_details(sample_pdf_text)
            self.assertEqual(result, expected_dict)
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "error_prompt_too_long"}
        ):
            self.po.get_quotation_details(sample_pdf_text)
            self.assertTrue(self.po.ocr_digitize_failed)
            self.assertIn("failed", self.po.ocr_digitize_message.lower())
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "error"}
        ):
            self.po.get_quotation_details(sample_pdf_text)
            self.assertTrue(self.po.ocr_digitize_failed)
            self.assertIn("failed", self.po.ocr_digitize_message.lower())
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                side_effect=Exception("API crashed")
        ):
            self.po.get_quotation_details(sample_pdf_text)
            self.assertTrue(self.po.ocr_digitize_failed)
            self.assertIn("Failed", self.po.ocr_digitize_message)

    def test_get_product_details(self):
        """
        Test get_product_details():

        Validates:
            ✓ Successful valid list response
            ✓ JSON list inside noisy text parsed correctly
            ✓ Prompt too long sets failure flags
            ✓ Generic error case handled
            ✓ Exception handling sets failure state
        """

        sample_pdf_text = """
            Item: Laptop LP100
            Qty: 2 Unit Price: $1200 Discount: 10% Tax: 18%
        """

        expected_list = [
            {
                "product_name": "Laptop",
                "product_code": "LP100",
                "quantity": "2",
                "quantity_uom": "Unit",
                "price_unit": "1200",
                "product_tax": "18%",
                "discount": "10",
            }
        ]
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "success", "content": json.dumps(expected_list)}
        ):
            result = self.po.get_product_details(sample_pdf_text)
            self.assertEqual(result, expected_list)
        noisy_response = f"RANDOM HEADER {json.dumps(expected_list)} END FOOTER"
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "success", "content": noisy_response}
        ):
            result = self.po.get_product_details(sample_pdf_text)
            self.assertEqual(result, expected_list)
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "error_prompt_too_long"}
        ):
            self.po.get_product_details(sample_pdf_text)
            self.assertTrue(self.po.ocr_digitize_failed)
            self.assertIn("failed", self.po.ocr_digitize_message.lower())
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                return_value={"status": "error"}
        ):
            self.po.get_product_details(sample_pdf_text)
            self.assertTrue(self.po.ocr_digitize_failed)
            self.assertIn("failed", self.po.ocr_digitize_message.lower())
        with patch(
                "odoo.addons.cyllo_purchase_digitization.models.purchase_order.iap_tools.iap_jsonrpc",
                side_effect=Exception("API failure")
        ):
            self.po.get_product_details(sample_pdf_text)
            self.assertIn("Failed", self.po.ocr_digitize_message)
            self.assertTrue(self.po.ocr_digitize_failed)

    def test_find_partner_ai(self):
        """Test partner detection and creation using find_partner_ai()."""

        text_with_partner = "Quotation issued by ABC Traders, Kerala"
        quotation_details = {"partner_name": "ABC Traders"}
        self.po.find_partner_ai(text_with_partner, quotation_details)
        self.assertEqual(
            self.po.partner_id.id,
            self.partner_abc.id)
        po2 = self.env['purchase.order'].create({
            'partner_id': self.dummy_partner.id,
        })
        text_no_match = "New Supplier Pvt Ltd quotation"
        quotation_details_new = {"partner_name": "New Supplier"}
        po2.find_partner_ai(text_no_match, quotation_details_new)
        created_partner = self.env['res.partner'].search([
            ('name', '=', "New Supplier")
        ], limit=1)

        self.assertTrue(created_partner)
        self.assertEqual(
            po2.partner_id.id,
            created_partner.id,
        )
        po3 = self.env['purchase.order'].create({
            'partner_id': self.dummy_partner.id,
        })
        text_missing = "Quotation issued"
        quotation_details_missing = {"partner_name": ""}
        po3.find_partner_ai(text_missing, quotation_details_missing)
        self.assertEqual(
            po3.partner_id.id,
            self.dummy_partner.id,
        )

    def test_action_find_field_values_ai(self):
        text = "Purchase order FOB Cochin Net 30"

        quotation_details = {
            "vendor_reference": "REF123",
            "payment_term": "Net 30",
            "incoterm": "FOB",
            "incoterm_location": "Cochin"
        }
        self.env['account.payment.term'].search([]).write({'active': False})
        self.env['account.incoterms'].search([]).write({'active': False})
        payment_term = self.env['account.payment.term'].create({"name": "Net 30"})
        incoterm = self.env['account.incoterms'].create({"name": "Free On Board", "code": "FOB"})
        self.po.action_find_field_values_ai(text, quotation_details)
        self.assertEqual(self.po.partner_ref, "REF123")
        self.assertEqual(self.po.payment_term_id.id, payment_term.id)
        self.assertEqual(self.po.incoterm_id.id, incoterm.id)
        self.assertEqual(self.po.incoterm_location, "Cochin")

    def test_action_find_product(self):
        """
        Test action_find_product():

        Validates:
            ✓ Match product using supplierinfo product_code
            ✓ Match product by name if no supplier match
            ✓ Create order line with correct qty, price, tax, and discount
            ✓ Digitization status flags update correctly
            ✓ If product not found → fallback to creating a new one
        """
        tax = self.env['account.tax'].create({
            'name': 'GST 18%',
            'amount': 18.0,
            'type_tax_use': 'purchase',
        })
        uom_unit = self.env['uom.uom'].search([], limit=1)
        supplier_record = self.env['product.supplierinfo'].create({
            'product_tmpl_id': self.test_product.product_tmpl_id.id,
            'partner_id': self.partner_abc.id,
            'product_code': "LP100",
        })
        product_details = [
            {
                "product_name": "Laptop",
                "product_code": "LP100",
                "quantity": "2",
                "quantity_uom": uom_unit.name,
                "price_unit": "1200.00",
                "product_tax": "18%",
                "discount": "10%"
            }
        ]
        self.po.action_find_product(product_details)
        self.assertEqual(len(self.po.order_line), 1)
        line = self.po.order_line[0]
        self.assertEqual(line.product_id.id, self.test_product.id)
        self.assertEqual(line.product_qty, 2.0)
        self.assertEqual(line.price_unit, 1200.00)
        self.assertEqual(line.taxes_id.id, tax.id)
        self.assertEqual(int(line.discount), 10)
        self.assertTrue(self.po.ocr_digitize_completed)
        self.assertFalse(self.po.ocr_digitize_failed)

    def test_action_create_product_ai(self):
        """
        Test action_create_product_ai(): ensures a new product is created when no matching
        product exists and that a corresponding purchase order line is added.

        Validates:
            ✓ Product is created with correct name, price, and UOM
            ✓ Order line is created referring to that product
            ✓ Digitization flags remain consistent
        """
        self.config.write({'product_creation_type': 'create_product'})
        uom_unit = self.env['uom.uom'].search([], limit=1)
        product_details = {
            "product_name": "Wireless Mouse",
            "product_code": "WM200",
            "quantity": "4",
            "quantity_uom": uom_unit.name,
            "price_unit": "850.50",
            "product_tax": "18%",
            "discount": "5%"
        }
        quote_details = {
            'order_id': self.po.id,
            'product_id': None,
            'product_qty': 4,
            'product_uom': uom_unit.id,
            'price_unit': 850.50,
            'discount': 5.0,
            'taxes_id': None
        }
        self.po.action_create_product_ai(product_details, quote_details)
        created_product = self.env['product.product'].search([('name', '=', "Wireless Mouse")], limit=1)
        self.assertTrue(created_product)
        self.assertEqual(created_product.standard_price, 850.50)
        line = self.po.order_line.filtered(lambda l: l.product_id == created_product)
        self.assertTrue(line)
        self.assertEqual(line.product_qty, 4.0)
        self.assertEqual(line.price_unit, 850.50)
        self.assertEqual(float(line.discount), 5.0)
        self.assertFalse(self.po.ocr_digitize_failed)
