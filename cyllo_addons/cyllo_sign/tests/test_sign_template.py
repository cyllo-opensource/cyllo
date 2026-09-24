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
from io import BytesIO
from PyPDF2 import PdfFileWriter
from unittest.mock import patch, PropertyMock

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestSignTemplate(TransactionCase):
    """
       Test suite for verifying the functionality of the `SignTemplate` model.

       This test ensures:
           * PDF page count is correctly calculated for valid templates.
           * Proper validation is enforced for missing or invalid PDF data.
           * The `get_datas()` method returns correct structured data with or without sign requests.
    """

    @classmethod
    def setUpClass(cls):
        """
        Test data setup executed once for the entire test class.

        Creates:
            - A sample valid sign template with PDF data.
            - A sign role, field, and template item.
            - A related sign request for the template.
        """
        super().setUpClass()

        pdf_writer = PdfFileWriter()
        pdf_writer.addBlankPage(width=200, height=200)
        pdf_writer.addBlankPage(width=200, height=200)
        pdf_stream = BytesIO()
        pdf_writer.write(pdf_stream)
        pdf_data = base64.b64encode(pdf_stream.getvalue())

        cls.template_valid = cls.env['sign.template'].create({
            'name': 'Valid PDF Template',
            'data': pdf_data,
        })
        cls.independent_template = cls.env['sign.template'].create({
            'name': 'Unlinked Template',
            'data': pdf_data,
        })
        cls.sign_role = cls.env['sign.role'].create({'name': 'Reviewer'})
        cls.sign_field = cls.env['sign.field'].create({'name': 'Signature Field'})
        cls.template_item = cls.env['sign.template.item'].create({
            'template_id': cls.template_valid.id,
            'name': 'Test Field',
            'field_id': cls.sign_field.id,
            'role_id': cls.sign_role.id,
            'page': 1,
            'required': True,
            'position_x': 10,
            'position_y': 20,
            'width': 30,
            'height': 15,
            'placeholder': 'Sign here',
            'color': 5,
            'field_type': 'signature',
        })
        cls.sign_request = cls.env['sign.request'].create({
            'name': 'Test Request for Template',
            'template_id': cls.template_valid.id,
        })
    def test_get_pdf_page_count(self):
        """
        Comprehensive test for verifying the `get_pdf_page_count()` method behavior
        across valid, missing, and invalid PDF scenarios.

        Test Validations:
            1. Valid PDF:
               Ensures the method returns the correct number of pages (2 in this case).
            2. Missing PDF:
               Ensures a ValidationError is raised when no PDF data is present.
            3. Corrupted PDF:
               Ensures a ValidationError is raised when the PDF data is unreadable.

        The test uses a pre-created two-page PDF template (`self.template_valid`)
        for the valid case and dynamically creates empty and invalid templates
        for the negative test cases
        """
        page_count = self.template_valid.get_pdf_page_count(self.template_valid.id)
        self.assertEqual(page_count, 2)
        empty_template = self.env['sign.template'].create({
            'name': 'Empty PDF Template'
        })
        with self.assertRaises(ValidationError):
            empty_template.get_pdf_page_count(empty_template.id)
        corrupted_data = base64.b64encode(b"This is not a valid PDF file")

        invalid_template = self.env['sign.template'].create({
            'name': 'Invalid PDF Template',
            'data': corrupted_data,
        })
        with self.assertRaises(ValidationError):
            invalid_template.get_pdf_page_count(invalid_template.id)


    def test_get_datas(self):
        """
        Verify the behavior of the `get_datas()` method for both scenarios:
            1. When only a template ID is provided (no request_id)
            2. When a sign request ID is provided (with existing request items)

        Test Validations:
            - Returned structure contains keys: template, template_items, roles, fields.
            - Without request_id → returns base template items.
            - With request_id → returns request-specific sign items.
            - Automatically creates request items if none exist for given template.
        """

        data_no_request = self.template_valid.get_datas(self.template_valid.id)
        self.assertIsInstance(data_no_request, dict)
        self.assertIn('template', data_no_request)
        self.assertIn('template_items', data_no_request)
        self.assertIn('roles', data_no_request)
        self.assertIn('fields', data_no_request)
        self.assertTrue(len(data_no_request['template_items']) > 0)

        data_with_request = self.template_valid.get_datas(self.template_valid.id, self.sign_request.id)
        self.assertIsInstance(data_with_request, dict)
        self.assertIn('template', data_with_request)
        self.assertIn('template_items', data_with_request)
        self.assertTrue(len(data_with_request['template_items']) > 0)

    def test_unlink(self):
        """
        Verify that a sign template cannot be deleted if it is linked to one or more sign requests.
        """
        with self.assertRaises(ValidationError):
            self.template_valid.unlink()
        self.independent_template.unlink()
        result = self.env['sign.template'].search([('name', '=', 'Unlinked Template')])
        self.assertFalse(result)

    def test_create_request_items(self):
        """
        Verify that the `_create_request_items()` method correctly creates
        `sign.request.item` records from the template items.

        Test Validations:
            - Creates one request item per template item.
            - Each request item correctly inherits values (name, role, position, etc.) from template item.
            - Returns the created request items list.
        """
        RequestItem = self.env['sign.request.item']

        # Record the initial count of request items for this request
        initial_count = RequestItem.search_count([('request_id', '=', self.sign_request.id)])

        request_items = self.template_valid._create_request_items(self.template_valid, self.sign_request)
        new_count = RequestItem.search_count([('request_id', '=', self.sign_request.id)])
        self.assertGreater(new_count, initial_count)
        self.assertEqual(len(request_items), len(self.template_valid.item_ids))

        created_item = RequestItem.search([('request_id', '=', self.sign_request.id)], limit=1)
        template_item = self.template_valid.item_ids[0]

        self.assertEqual(created_item.request_id.id, self.sign_request.id)
        self.assertEqual(created_item.template_item_id.id, template_item.id,)
        self.assertEqual(created_item.role_id.id, template_item.role_id.id)
        self.assertEqual(created_item.name, template_item.name)
        self.assertEqual(created_item.page, template_item.page)
        self.assertEqual(created_item.position_x, template_item.position_x)
        self.assertEqual(created_item.position_y, template_item.position_y)
        self.assertEqual(created_item.placeholder, template_item.placeholder)
        self.assertEqual(created_item.color, template_item.color)
        self.assertEqual(created_item.field_type, template_item.field_type)
        self.assertFalse(created_item.signature)

    def test_view_record(self):
        """Test that `view_record()` returns the correct action dictionary for SignTemplate."""
        action = self.template_valid.view_record()
        self.assertIsInstance(action, dict)
        self.assertIn('type', action)
        self.assertIn('name', action)
        self.assertIn('res_model', action)
        self.assertIn('res_id', action)
        self.assertIn('view_mode', action)
        self.assertIn('target', action)

        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], self.template_valid._name)
        self.assertEqual(action['res_id'], self.template_valid.id)
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'current')
        self.assertEqual(action['name'], self.template_valid.name)

    def test_delete_record(self):
        """Test that `delete_record()` correctly removes the template record."""
        pdf_data = self.template_valid.data
        temp_template = self.env['sign.template'].create({
            'name': 'Temporary Template',
            'data': pdf_data,
        })
        self.assertTrue(temp_template.exists())
        temp_template.delete_record()
        self.assertFalse(temp_template.exists())

    def test_add_item(self):
        """Test that `add_item()` correctly creates a new template item."""
        field = self.sign_field.id
        template = self.template_valid
        item_id = template.add_item(
            field=field,
            required=True,
            page=1,
            position_x=10,
            position_y=20,
            placeholder="Sign here",
            position_x_px=100,
            position_y_px=200
        )
        created_item = self.env['sign.template.item'].browse(item_id)
        self.assertTrue(created_item.exists())
        self.assertEqual(created_item.template_id.id, template.id)
        self.assertEqual(created_item.field_id.id, field)
        self.assertEqual(created_item.required, True)
        self.assertEqual(created_item.page, 1)
        self.assertEqual(created_item.position_x, 10)
        self.assertEqual(created_item.position_y, 20)
        self.assertEqual(created_item.placeholder, "Sign here")
        self.assertEqual(created_item.position_x_px, 100)
        self.assertEqual(created_item.position_y_px, 200)

    def test_action_configure(self):
        """Test that `action_configure()` returns correct client action data."""

        action = self.template_valid.action_configure()

        self.assertIsInstance(action, dict)
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['name'], self.template_valid.name)
        self.assertEqual(action['tag'], 'sign_configure')
        self.assertIn('params', action)
        self.assertEqual(action['params']['res_model'], 'sign.template')
        self.assertEqual(action['params']['res_id'], self.template_valid.id)

    def test_action_view_sign_generate(self):
        """
           Test that `action_view_sign_generate()` works for both active and inactive cases.
        """

        action = self.template_valid.action_view_sign_generate()

        self.assertIsInstance(action, dict)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['name'], 'Generate Sign')
        self.assertEqual(action['res_model'], 'sign.generate')
        self.assertIn('res_id', action)
        self.assertTrue(action['res_id'] > 0)
        self.assertEqual(action['view_mode'], 'form')
        self.assertIn('views', action)
        self.assertEqual(action['target'], 'new')

        SignGenerateModel = self.env['sign.generate'].__class__
        inactive_record = self.env['sign.generate'].browse([])

        with patch.object(SignGenerateModel, 'create', return_value=inactive_record), \
                patch.object(type(inactive_record), 'is_active', new_callable=PropertyMock, return_value=False):
            with self.assertRaises(ValidationError):
                self.template_valid.action_view_sign_generate()






