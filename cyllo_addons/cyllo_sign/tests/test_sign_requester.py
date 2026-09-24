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
from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.addons.cyllo_sign.models import sign_request


class TestSignRequester(TransactionCase):
    """
    Test suite for verifying the functionality of the `SignRequesters` model.

    This test ensures:
        * The `action_sign` method updates signed status correctly.
        * The related sign request state changes to 'signed' or 'partial'.
        * PDF data is written back to the request after signing.
        * PDF overwrite helper methods work as expected.
    """

    @classmethod
    def setUpClass(cls):
        """
        Sets up base data for all SignRequester tests.

        Creates:
            - Partner, role, template, and sign request.
            - Requester record linked to the request.
            - A dummy PDF file as binary data for signing simulation.
            - Common reusable PDF writer and box for tests.
        """
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({
            'name': 'Signer Partner',
            'email': 'signer@example.com',
        })

        cls.role = cls.env['sign.role'].create({'name': 'Manager'})
        cls.template = cls.env['sign.template'].create({'name': 'Template A'})
        pdf_writer = PdfFileWriter()
        pdf_writer.addBlankPage(width=200, height=200)
        pdf_stream = BytesIO()
        pdf_writer.write(pdf_stream)
        pdf_data = base64.b64encode(pdf_stream.getvalue())

        cls.sign_request = cls.env['sign.request'].create({
            'name': 'Test Request',
            'template_id': cls.template.id,
            'data': pdf_data,
        })
        cls.signer = cls.env['sign.requester'].create({
            'partner_id': cls.partner.id,
            'role_id': cls.role.id,
            'request_id': cls.sign_request.id,
        })

        cls.pdf_writer = PdfFileWriter()
        cls.pdf_writer.addBlankPage(width=200, height=200)
        cls.box = cls.pdf_writer.getPage(0).mediaBox
        cls.sample_item = {
            'value': 'Test Value',
            'width': 10,
            'height': 10,
            'position_x': 10,
            'position_y': 10,
        }

    def test_action_sign_single_signer(self):
        """
        Validate that the `action_sign` method:
            - Updates the requester `signed_on` timestamp.
            - Updates the request state to 'signed' when all have signed.
        """
        items = [{
            'page': 1,
            'role_id': self.role.id,
            'signature': 'Test Signature',
            'field_type': 'text',
            'width': 10,
            'height': 10,
            'position_x': 10,
            'position_y': 10,
            'value': 'Signed by user',
        }]
        self.signer.action_sign(items)
        self.assertTrue(self.signer.signed_on)
        self.assertTrue(self.sign_request.data)
        self.assertEqual(self.sign_request.state, 'signed')

    def test_action_sign_partial(self):
        """
        Validate that `action_sign` sets request state to 'partial'
        when not all signers have signed.
        """
        second_role = self.env['sign.role'].create({'name': 'Employee'})
        second_partner = self.env['res.partner'].create({
            'name': 'Second Signer',
            'email': 'second@example.com',
        })
        second_signer = self.env['sign.requester'].create({
            'partner_id': second_partner.id,
            'role_id': second_role.id,
            'request_id': self.sign_request.id,
        })
        items = [{
            'page': 1,
            'role_id': self.role.id,
            'signature': 'Test Signature',
            'field_type': 'text',
            'width': 10,
            'height': 10,
            'position_x': 10,
            'position_y': 10,
            'value': 'Signed by user',
        }]
        self.signer.action_sign(items)
        self.assertTrue(self.signer.signed_on)
        self.assertEqual(self.sign_request.state, 'partial')

    def test_overwrite_pdf_page(self):
        """
        Verify that `_overwrite_pdf_page` correctly dispatches
        to the respective sub-methods using class-level mocking.
        """
        item = {
            'field_type': 'text',
            'value': 'Mock Test',
            'width': 10,
            'height': 10,
            'position_x': 10,
            'position_y': 10,
        }

        with patch.object(self.signer.__class__, "_overwrite_pdf_page_text", return_value="TEXT_OK") as mock_text, \
                patch.object(self.signer.__class__, "_overwrite_pdf_page_date", return_value="DATE_OK") as mock_date, \
                patch.object(self.signer.__class__, "_overwrite_pdf_page_signature", return_value="SIGNATURE_OK") as mock_signature:

            item["field_type"] = "text"
            result_text = self.signer._overwrite_pdf_page(item, self.box)
            self.assertEqual(result_text, "TEXT_OK")
            mock_text.assert_called_once_with(item, self.box)

            item["field_type"] = "date"
            result_date = self.signer._overwrite_pdf_page(item, self.box)
            self.assertEqual(result_date, "DATE_OK")
            mock_date.assert_called_once_with(item, self.box)

            item["field_type"] = "signature"
            result_sign = self.signer._overwrite_pdf_page(item, self.box)
            self.assertEqual(result_sign, "SIGNATURE_OK")
            mock_signature.assert_called_once_with(item, self.box)

    def test_overwrite_pdf_page_text(self):
        """
        Test `_overwrite_pdf_page_text` to ensure it generates a valid PDF page
        with text placement logic and returns a PyPDF2 page object.
        """
        result = self.signer._overwrite_pdf_page_text(self.sample_item, self.box)
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, "mediaBox"))

    def test_overwrite_pdf_page_date(self):
        """
        Test `_overwrite_pdf_page_date` for valid and invalid date values.
        Ensures it gracefully handles both cases without errors.
        """
        valid_item = dict(self.sample_item, value="10-11-2025")
        result_valid = self.signer._overwrite_pdf_page_date(valid_item, self.box)
        self.assertIsNotNone(result_valid)
        self.assertTrue(hasattr(result_valid, "mediaBox"))

        invalid_item = dict(self.sample_item, value="Invalid Date")
        result_invalid = self.signer._overwrite_pdf_page_date(invalid_item, self.box)
        self.assertIsNotNone(result_invalid)
        self.assertTrue(hasattr(result_invalid, "mediaBox"))

    def test_overwrite_pdf_page_signature(self):
        """
        Test `_overwrite_pdf_page_signature` using `with patch.object` to mock
        both Image and PdfFileReader, avoiding real image and PDF handling.

        Validations:
            - Image() is called with correct arguments when valid data is provided.
            - drawOn() is called exactly once.
            - PdfFileReader and getPage(0) are invoked correctly.
            - Returns False when no image data is provided.
        """
        with patch.object(sign_request, "Image") as mock_image, \
                patch.object(sign_request, "PdfFileReader") as mock_reader:
            mock_image_instance = mock_image.return_value
            mock_image_instance.drawOn.return_value = None

            mock_reader_instance = mock_reader.return_value
            mock_page = object()
            mock_reader_instance.getPage.return_value = mock_page
            fake_b64 = base64.b64encode(b"fakeimagebytes").decode("utf-8")
            valid_item = dict(self.sample_item, value=fake_b64)
            result_valid = self.signer._overwrite_pdf_page_signature(valid_item, self.box)

            self.assertEqual(result_valid, mock_page)
            mock_image.assert_called_once()
            mock_image_instance.drawOn.assert_called_once()
            mock_reader.assert_called_once()
            mock_reader_instance.getPage.assert_called_once_with(0)
        invalid_item = dict(self.sample_item, value=False)
        result_invalid = self.signer._overwrite_pdf_page_signature(invalid_item, self.box)
        self.assertFalse(result_invalid)




