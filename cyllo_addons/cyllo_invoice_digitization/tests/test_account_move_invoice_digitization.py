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
from odoo.tests.common import TransactionCase, tagged
from unittest.mock import patch, MagicMock
import base64
import json
from odoo.exceptions import AccessError


@tagged('-at_install', 'post_install')
class TestAccountMoveInvoiceDigitization(TransactionCase):
    """
    """

    @classmethod
    def setUpClass(cls):
        """
        Prepare reusable invoice, module state, and environment for all test cases,
        ensuring a clean environment free from conflicting historical test records.
        """
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.Move = cls.env['account.move']
        cls.Digitization = cls.env['invoice.digitization']
        cls.Module = cls.env['ir.module.module']
        cls.Product = cls.env['product.product']

        cls.Digitization.search([]).unlink()

        module = cls.Module.search([('name', '=', 'cyllo_invoice_digitization')], limit=1)
        if module:
            module.write({'state': 'installed'})
        else:
            module = cls.Module.create({
                'name': 'cyllo_invoice_digitization',
                'state': 'installed'
            })
        cls.module_record = module

        cls.invoice = cls.Move.create({
            'move_type': 'out_invoice',
            'state': 'draft',
        })

    def test_invoice_digitization_property(self):
        """
        Validate invoice-level configuration lookup logic.

        Ensures:
            - No configuration returns False.
            - Only the latest active configuration binds to the invoice.
            - Configurations for other account types do not interfere.
        """
        self.assertFalse(self.invoice.invoice_digitization)

        self.Digitization.create({
            'name': 'Config 1',
            'account_type': 'out_invoice',
            'active_configuration': False,
        })
        self.assertFalse(self.invoice.invoice_digitization)

        active_config = self.Digitization.create({
            'name': 'Active Config',
            'account_type': 'out_invoice',
            'active_configuration': True,
        })
        self.assertTrue(self.invoice.invoice_digitization)
        self.assertEqual(self.invoice.invoice_digitization.id, active_config.id)
        new_active_config = self.Digitization.create({
            'name': 'New Active Config',
            'account_type': 'out_invoice',
            'active_configuration': True,
        })
        self.assertEqual(self.invoice.invoice_digitization.id, new_active_config.id)
        other_type_config = self.Digitization.create({
            'name': 'Vendor Config',
            'account_type': 'in_invoice',
            'active_configuration': True,
        })

        self.assertNotEqual(self.invoice.invoice_digitization.id, other_type_config.id)
        self.assertEqual(self.invoice.invoice_digitization.id, new_active_config.id)

    def test_compute_ocr_digitize_enabled(self):
        """
        Validate on-change compute logic for OCR enablement.

        Confirms behavior under:
            - request_digitize
            - not_digitize
            - auto_digitize
            - module disabled state
        """
        config = self.Digitization.create({
            'name': 'Config OCR',
            'account_type': 'out_invoice',
            'automation_type': 'not_digitize',
            'active_configuration': True
        })
        config.write({'automation_type': 'request_digitize'})
        self.invoice._compute_ocr_digitize_enabled()
        self.assertTrue(self.invoice.ocr_digitize_enabled)
        config.write({'automation_type': 'not_digitize'})
        self.invoice._compute_ocr_digitize_enabled()
        self.assertFalse(self.invoice.ocr_digitize_enabled)
        config.write({'automation_type': 'auto_digitize'})
        self.invoice._compute_ocr_digitize_enabled()
        self.assertFalse(self.invoice.ocr_digitize_enabled)
        module = self.Module.search([('name', '=', 'cyllo_invoice_digitization')], limit=1)
        if module:
            module.write({'state': 'uninstalled'})
        self.invoice._compute_ocr_digitize_enabled()
        self.assertFalse(self.invoice.ocr_digitize_enabled)

    def test_process_auto_digitization(self):
        """
        Validate full automation workflow for processing PDF invoices.

        Expected outcomes:
            - Successful runs trigger digitization action.
            - Failures record proper error state.
            - NO action when automation is disabled or attachment missing.
        """
        config = self.Digitization.create({
            'name': 'Auto Digitization Config',
            'account_type': 'out_invoice',
            'automation_type': 'auto_digitize',
            'active_configuration': True,
        })

        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.pdf',
            'datas': base64.b64encode(b"Test PDF Content").decode(),
            'mimetype': 'application/pdf',
        })
        self.invoice.message_main_attachment_id = attachment.id
        with patch.object(self.invoice.__class__, 'action_send_digitization', return_value=True) as mock_success:
            self.invoice.process_auto_digitization()
            mock_success.assert_called_once()
            self.assertTrue(self.invoice.ocr_digitize_completed)
            self.assertFalse(self.invoice.ocr_digitize_failed)
        self.invoice.ocr_digitize_completed = False
        self.invoice.ocr_digitize_failed = False
        with patch.object(self.invoice.__class__, 'action_send_digitization', side_effect=Exception("OCR Failed")) as mock_failure:
            self.invoice.process_auto_digitization()
            mock_failure.assert_called_once()
            self.assertTrue(self.invoice.ocr_digitize_failed)
            self.assertFalse(self.invoice.ocr_digitize_completed)
        self.invoice.ocr_digitize_failed = False
        self.invoice.ocr_digitize_completed = False
        config.write({'automation_type': 'not_digitize'})
        with patch.object(self.invoice.__class__, 'action_send_digitization') as mock_no_call:
            self.invoice.process_auto_digitization()
            mock_no_call.assert_not_called()
            self.assertFalse(self.invoice.ocr_digitize_completed)
        config.write({'automation_type': 'auto_digitize'})
        self.invoice.message_main_attachment_id = False
        with patch.object(self.invoice.__class__, 'action_send_digitization') as mock_no_attachment:
            self.invoice.process_auto_digitization()
            mock_no_attachment.assert_not_called()
            self.assertFalse(self.invoice.ocr_digitize_completed)

    def test_action_send_digitization(self):
        """
        Validate entry point logic for OCR processing based on:

            - Attachment type validation
            - Configuration availability
            - Manual vs AI execution paths
            - Exception handling
        """
        non_pdf = self.env['ir.attachment'].create({
            'name': 'file.png',
            'datas': base64.b64encode(b"IMG").decode(),
            'mimetype': 'image/png'
        })
        self.invoice.message_main_attachment_id = non_pdf.id
        self.invoice.action_send_digitization()
        self.assertTrue(self.invoice.ocr_digitize_failed)
        self.assertIn("PDF", self.invoice.ocr_digitize_message)
        pdf_attachment = self.env['ir.attachment'].create({
            'name': 'file.pdf',
            'datas': base64.b64encode(b"PDFDATA").decode(),
            'mimetype': 'application/pdf'
        })
        with patch("odoo.addons.cyllo_invoice_digitization.models.account_move.fitz.open"), \
             patch("odoo.addons.cyllo_invoice_digitization.models.account_move.pdfplumber.open"):
            self.invoice.message_main_attachment_id = pdf_attachment.id
            self.invoice.action_send_digitization()
        self.assertTrue(self.invoice.ocr_digitize_failed)
        self.assertIn("Configure", self.invoice.ocr_digitize_message)
        config = self.Digitization.create({
            'name': 'Invoice OCR',
            'account_type': 'out_invoice',
            'automation_method': 'manual_digitization',
            'active_configuration': True
        })
        with patch("odoo.addons.cyllo_invoice_digitization.models.account_move.fitz.open"), \
             patch("odoo.addons.cyllo_invoice_digitization.models.account_move.pdfplumber.open"), \
             patch.object(self.invoice.__class__, "_process_digitization_manually") as manual_call:
            self.invoice.action_send_digitization()
            manual_call.assert_called_once()
        config.write({'automation_method': 'ai_digitization'})
        with patch("odoo.addons.cyllo_invoice_digitization.models.account_move.fitz.open"), \
             patch("odoo.addons.cyllo_invoice_digitization.models.account_move.pdfplumber.open"), \
             patch.object(self.invoice.__class__, "_process_pdf_using_ai") as ai_call:
            self.invoice.action_send_digitization()
            ai_call.assert_called_once()
        with patch("odoo.addons.cyllo_invoice_digitization.models.account_move.fitz.open", side_effect=Exception("Boom")):
            self.invoice.action_send_digitization()
            self.assertTrue(self.invoice.ocr_digitize_failed)
            self.assertIn("failed", self.invoice.ocr_digitize_message.lower())

    def test_process_digitization_manually(self):
        """
        Validate workflow execution for manual digitization including:

            - Partner and field extraction
            - Product parsing and list processing
            - Failure and exception behavior
        """
        file_path = "/fake/path.pdf"
        text = "Sample OCR extracted text"
        with patch.object(self.invoice.__class__, "find_partner") as p1, \
             patch.object(self.invoice.__class__, "action_find_field_values") as p2, \
             patch.object(self.invoice.__class__, "_extract_product_info", return_value=[]) as p3:
            self.invoice._process_digitization_manually(file_path, text)
            p1.assert_called_once()
            p2.assert_called_once()
            p3.assert_called_once()
            self.assertTrue(self.invoice.ocr_digitize_failed)
        self.invoice.ocr_digitize_failed = False
        self.invoice.ocr_digitize_completed = False
        with patch.object(self.invoice.__class__, "find_partner") as p1, \
             patch.object(self.invoice.__class__, "action_find_field_values") as p2, \
             patch.object(self.invoice.__class__, "_extract_product_info", return_value=[{"name": "Test Product"}]) as p3, \
             patch.object(self.invoice.__class__, "_process_product_list") as p4:
            self.invoice._process_digitization_manually(file_path, text)
            p1.assert_called_once()
            p2.assert_called_once()
            p3.assert_called_once()
            p4.assert_called_once()
            self.assertTrue(self.invoice.ocr_digitize_completed)
        self.invoice.ocr_digitize_failed = False
        self.invoice.ocr_digitize_completed = False
        with patch.object(self.invoice.__class__, "find_partner", side_effect=Exception("boom")):
            self.invoice._process_digitization_manually(file_path, text)
            self.assertTrue(self.invoice.ocr_digitize_failed)

    def test_extract_product_info(self):
        """
        Validate PDF line parsing and dictionary mapping for product extraction in:

            - No match cases
            - No-discount patterns
            - Discount line parsing
        """
        fake_path = "/fake/path.pdf"
        mock_no_product = MagicMock()
        mock_no_product.extract_text.return_value = "Random\nNot a product line"
        with patch("odoo.addons.cyllo_invoice_digitization.models.account_move.pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value.pages = [mock_no_product]
            result = self.invoice._extract_product_info(fake_path)
            self.assertEqual(result, [])

        mock_page = MagicMock()
        mock_page.extract_text.return_value = (
            "Item  Qty  Price  Taxes  Total\n"
            "Milk Powder   2.00 kg   120.00   GST 18%   ₹ 240.00"
        )
        with patch("odoo.addons.cyllo_invoice_digitization.models.account_move.pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value.pages = [mock_page]
            result = self.invoice._extract_product_info(fake_path)
            self.assertEqual(len(result), 1)
            item = result[0]
            self.assertEqual(item["product_name"], "Milk Powder")
        mock_page_disc = MagicMock()
        mock_page_disc.extract_text.return_value = (
            "Item  Qty  Price  Disc.%  Taxes  Total\n"
            "Bread   1.00 pc   50.00   10   GST 5%   ₹ 45.00"
        )
        with patch("odoo.addons.cyllo_invoice_digitization.models.account_move.pdfplumber.open") as mock_open:
            mock_open.return_value.__enter__.return_value.pages = [mock_page_disc]
            result = self.invoice._extract_product_info(fake_path)
            self.assertEqual(len(result), 1)

    def test_process_product_list(self):
        """
        Validate product mapping and account line creation using mock product data.
        """
        product_list = [
            {"product_name": "Milk Powder"},
            {"product_name": "Bread"},
        ]

        with patch.object(self.invoice.__class__, "_split_product_name", return_value=("Milk Powder", None)) as mock_split, \
             patch.object(self.invoice.__class__, "_find_or_create_product", return_value="PRODUCT") as mock_find, \
             patch.object(self.invoice.__class__, "_create_account_move_line") as mock_line:
            self.invoice._process_product_list(product_list)
            self.assertEqual(mock_split.call_count, 2)
            self.assertEqual(mock_find.call_count, 2)
            self.assertEqual(mock_line.call_count, 2)

        with patch.object(self.invoice.__class__, "_split_product_name") as m1, \
             patch.object(self.invoice.__class__, "_find_or_create_product") as m2, \
             patch.object(self.invoice.__class__, "_create_account_move_line") as m3:
            self.invoice._process_product_list([])
            m1.assert_not_called()
            m2.assert_not_called()
            m3.assert_not_called()

    def test_split_product_name(self):
        """
        Validate internal reference parsing logic for different product naming formats.
        """
        result = self.invoice._split_product_name("[ABC123] Laptop")
        self.assertEqual(result, ("Laptop", "ABC123"))
        result = self.invoice._split_product_name("Charger")
        self.assertEqual(result, ("Charger", None))

    def test_get_regex_pattern(self):
        """
        Validate regex output format for discount and non-discount scenarios.
        """
        pattern_with_discount = self.invoice._get_regex_pattern(True).pattern
        self.assertIn(r"([\d.]+)?", pattern_with_discount)
        pattern_without_discount = self.invoice._get_regex_pattern(False).pattern
        self.assertNotIn(r"([\d.]+)?", pattern_without_discount)
        self.assertIn(r"[₹\$]", pattern_with_discount)
        self.assertIn(r"[₹\$]", pattern_without_discount)

    def test_find_or_create_product(self):
        """
        Validate product lookup and conditional creation logic based on settings.
        """
        config = self.Digitization.create({
            'name': 'Default Config',
            'account_type': 'out_invoice',
            'automation_type': 'not_digitize',
            'product_creation_type': 'create_product',
            'active_configuration': True
        })
        config.write({'product_creation_type': 'create_product'})
        existing = self.Product.create({
            'name': 'Laptop',
            'default_code': 'LP100',
        })
        result = self.invoice._find_or_create_product('Laptop', 'LP100')
        self.assertEqual(result.id, existing.id)
        result_new = self.invoice._find_or_create_product('Mouse', 'MS001')
        self.assertTrue(result_new.exists())
        config.write({'product_creation_type': 'not_create_product'})
        result_none = self.invoice._find_or_create_product('Keyboard', 'KB001')
        self.assertFalse(result_none.exists())

    def test_create_account_move_line(self):
        """
        Validate account move line creation behavior when product exists or not.
        """

        product_data = {
            "product_name": "Test Product",
            "quantity": "2.00",
            "unit_price": "50.00",
            "taxes": ["GST 18%"],
            "discount": 10.0
        }
        product_record = self.Product.create({
            "name": "Test Product",
            "default_code": "TP001"
        })
        with patch.object(self.invoice.__class__, "_get_tax_ids", return_value=[1, 2]) as mock_tax, \
                patch("odoo.addons.account.models.account_move_line.AccountMoveLine.create") as mock_create:
            self.invoice._create_account_move_line(product_data, product_record)
            mock_tax.assert_called_once_with(product_data["taxes"])
            mock_create.assert_called_once()
            created_vals = mock_create.call_args[0][0]
            self.assertEqual(created_vals["move_id"], self.invoice.id)
            self.assertEqual(created_vals["product_id"], product_record.id)
            self.assertEqual(created_vals["quantity"], 2.00)
            self.assertEqual(created_vals["price_unit"], 50.00)
            self.assertEqual(created_vals["discount"], 10.0)

        with patch("odoo.addons.account.models.account_move_line.AccountMoveLine.create") as mock_no_create:
            self.invoice._create_account_move_line(product_data, None)
            mock_no_create.assert_not_called()

    def test_get_tax_ids(self):
        """
        Validate `_get_tax_ids()` tax lookup behavior:

        - Returns matching tax IDs based on name
        - Respects move_type (sale vs purchase)
        - Returns empty/False when no matching tax exists
        - Supports tax lookup using amount when tax_per_invoice=True
        """

        tax1 = self.env['account.tax'].create({
            'name': 'GST 18%',
            'amount': 18.0,
            'type_tax_use': 'sale'
        })
        tax2 = self.env['account.tax'].create({
            'name': 'VAT 5%',
            'amount': 5.0,
            'type_tax_use': 'purchase'
        })
        self.invoice.move_type = 'out_invoice'
        result = self.invoice._get_tax_ids(['GST 18%'], tax_per_invoice=False)
        self.assertEqual(result, [(6, 0, [tax1.id])])
        result = self.invoice._get_tax_ids(['18.0'], tax_per_invoice=True)
        self.assertEqual(result, [(6, 0, [tax1.id])])
        self.invoice.move_type = 'in_invoice'
        result = self.invoice._get_tax_ids(['VAT 5%'], tax_per_invoice=False)
        self.assertEqual(result, [(6, 0, [tax2.id])])
        result = self.invoice._get_tax_ids(['Unknown Tax'])
        self.assertFalse(result)

    def test_process_pdf_using_ai(self):
        """Test `_process_pdf_using_ai` handles success, AI failure response, and exceptions."""

        fake_pdf_text = "Sample text from invoice"
        fake_json = {
            "partner": {"name": "Test Partner"},
            "invoice_orderline": [],
            "currency_code": "USD",
            "total_tax_percentages": []
        }
        with patch.object(
            self.invoice.__class__,
            "make_response_with_default",
            return_value={"is_error": False, "response": json.dumps(fake_json)}
        ) as mock_ai, \
        patch.object(self.invoice.__class__, "_process_invoice_partner", return_value=self.env['res.partner']) as mock_partner, \
        patch.object(self.invoice.__class__, "_process_invoice_data") as mock_process_data, \
        patch.object(self.invoice.__class__, "_process_invoice_order_line") as mock_process_lines:
            self.invoice._process_pdf_using_ai(fake_pdf_text)
            mock_ai.assert_called_once()
            mock_partner.assert_called_once()
            mock_process_data.assert_called_once()
            mock_process_lines.assert_called_once()
            self.assertTrue(self.invoice.ocr_digitize_completed)
            self.assertFalse(self.invoice.ocr_digitize_failed)
        self.invoice.ocr_digitize_completed = False
        self.invoice.ocr_digitize_failed = False
        with patch.object(
            self.invoice.__class__,
            "make_response_with_default",
            return_value={"is_error": True, "response": "Invalid format"}
        ) as mock_ai_error, \
        patch.object(self.invoice.__class__, "_mark_ocr_failed") as mock_fail:
            self.invoice._process_pdf_using_ai(fake_pdf_text)
            mock_ai_error.assert_called_once()
            mock_fail.assert_called_once()
        self.invoice.ocr_digitize_completed = False
        self.invoice.ocr_digitize_failed = False
        with patch.object(
            self.invoice.__class__,
            "make_response_with_default",
            side_effect=Exception("Crash")
        ), patch.object(self.invoice.__class__, "_mark_ocr_failed") as mock_fail_exception:
            self.invoice._process_pdf_using_ai(fake_pdf_text)
            mock_fail_exception.assert_called_once()

    def test_mark_ocr_failed(self):
        """Verify that _mark_ocr_failed correctly updates failure state and message."""

        self.invoice.ocr_digitize_failed = False
        self.invoice.ocr_digitize_completed = True
        fail_message = "AI processing failed"
        self.invoice._mark_ocr_failed(fail_message)
        self.assertTrue(self.invoice.ocr_digitize_failed)
        self.assertFalse(self.invoice.ocr_digitize_completed)
        self.assertEqual(self.invoice.ocr_digitize_message, fail_message)

    def test_make_response_with_default(self):
        """Verify make_response_with_default handles success response, fallback, and exceptions."""

        pdf_text = "Sample invoice text"
        conversation = [{"role": "user", "content": "Test"}]
        success_response = {"status": "success", "content": '{"data":"ok"}'}
        with patch(
            "odoo.addons.cyllo_invoice_digitization.models.account_move.iap_tools.iap_jsonrpc",
            return_value=success_response
        ):
            result = self.invoice.make_response_with_default(pdf_text, conversation)
        self.assertFalse(result["is_error"])
        self.assertEqual(result["response"], '{"data":"ok"}')
        fallback_response = {"is_error": False, "response": "fallback-response"}
        with patch(
            "odoo.addons.cyllo_invoice_digitization.models.account_move.iap_tools.iap_jsonrpc",
            return_value={"status": "error"}
        ), patch.object(
            self.invoice.__class__, "_fallback_to_gpt", return_value=fallback_response
        ) as mock_fallback:
            result = self.invoice.make_response_with_default(pdf_text, conversation)
        mock_fallback.assert_called_once()
        self.assertEqual(result, fallback_response)
        with patch(
            "odoo.addons.cyllo_invoice_digitization.models.account_move.iap_tools.iap_jsonrpc",
            side_effect=AccessError("No access")
        ), patch.object(
            self.invoice.__class__, "_fallback_to_gpt", return_value=fallback_response
        ) as mock_fallback:
            result = self.invoice.make_response_with_default(pdf_text, conversation)
        mock_fallback.assert_called_once()
        self.assertEqual(result, fallback_response)
        with patch(
            "odoo.addons.cyllo_invoice_digitization.models.account_move.iap_tools.iap_jsonrpc",
            side_effect=Exception("Random failure")
        ), patch.object(
            self.invoice.__class__, "_fallback_to_gpt", return_value=fallback_response
        ) as mock_fallback:
            result = self.invoice.make_response_with_default(pdf_text, conversation)
        mock_fallback.assert_called_once()
        self.assertEqual(result, fallback_response)

    def test_handle_response_error(self):
        """Verify response error handling uses correct fallback messaging."""

        pdf_text = "Sample Text"
        conversation = [{"role": "user", "content": "test"}]
        open_ai_key = "dummy_key"
        fallback_response = {"is_error": True, "response": "fallback result"}
        with patch.object(
            self.invoice.__class__, "_fallback_to_gpt", return_value=fallback_response
        ) as mock_fallback:
            result = self.invoice._handle_response_error(
                "error_prompt_too_long", pdf_text, conversation, open_ai_key
            )
        mock_fallback.assert_called_once_with(open_ai_key, pdf_text, conversation)
        self.assertEqual(result, fallback_response)
        mock_fallback.reset_mock()
        with patch.object(
            self.invoice.__class__, "_fallback_to_gpt", return_value=fallback_response
        ) as mock_fallback:
            result = self.invoice._handle_response_error(
                "limit_call_reached", pdf_text, conversation, open_ai_key
            )
        mock_fallback.assert_called_once_with(open_ai_key, pdf_text, conversation)
        self.assertEqual(result, fallback_response)
        mock_fallback.reset_mock()
        with patch.object(
            self.invoice.__class__, "_fallback_to_gpt", return_value=fallback_response
        ) as mock_fallback:
            result = self.invoice._handle_response_error(
                "something_random", pdf_text, conversation, open_ai_key
            )
        mock_fallback.assert_called_once_with(open_ai_key, pdf_text, conversation)
        self.assertEqual(result, fallback_response)

    def test_fallback_to_gpt(self):
        """Verify `_fallback_to_gpt` returns correct structure for success and error cases."""

        api_key = "dummy_key"
        prompt = "Test prompt"
        conversation = [{"role": "user", "content": "Hello"}]
        success_response = {"is_error": False, "response": "Valid AI response"}
        with patch.object(
            self.invoice.__class__, "make_response_with_gpt", return_value=success_response
        ) as mock_call:
            result = self.invoice._fallback_to_gpt(api_key, prompt, conversation)
            mock_call.assert_called_once_with(api_key, prompt, conversation)
            self.assertEqual(result, success_response)

        error_response_with_message = {"is_error": True, "response": "AI failed"}
        with patch.object(
            self.invoice.__class__, "make_response_with_gpt", return_value=error_response_with_message
        ):
            result = self.invoice._fallback_to_gpt(api_key, prompt, conversation)
            self.assertTrue(result["is_error"])
            self.assertEqual(result["response"], "AI failed")

        error_response_no_message = {"is_error": True, "response": ""}
        with patch.object(
            self.invoice.__class__, "make_response_with_gpt", return_value=error_response_no_message
        ):
            result = self.invoice._fallback_to_gpt(api_key, prompt, conversation)
            self.assertTrue(result["is_error"])
            self.assertEqual(result["response"], "Failed to generate response.")

    




