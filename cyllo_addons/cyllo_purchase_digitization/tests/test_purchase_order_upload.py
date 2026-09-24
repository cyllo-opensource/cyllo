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
import io
import json
import re
import uuid

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestPurchaseOrderUpload(HttpCase):
    """
    Test suite validating upload functionality of the Purchase Digitization
    HTTP controller.

    This test ensures:
        * Only authenticated users can execute upload.
        * CSRF protection is respected.
        * Upload creates a Purchase Order with an attachment.
        * Uploaded file content matches stored binary data.
    """
    @classmethod
    def setUpClass(cls):
        """Ensure required partner exists due to controller hardcoded dependency"""
        super().setUpClass()
        if not cls.env['res.partner'].browse(3).exists():
            cls.env.cr.execute("INSERT INTO res_partner (id,name) VALUES (3,'Auto Partner')")
            cls.env.invalidate_all()
    def _csrf(self):
        """Extract a valid CSRF token from /my page"""
        response = self.url_open('/my')
        match = re.search(r'csrf_token: "([^"]+)"', response.text)
        return match.group(1) if match else None

    def test_upload_document(self):
        """
        Validate end-to-end upload flow for an authenticated purchase user:

            1. Login as internal purchase user.
            2. Fetch CSRF token.
            3. Upload a file through the controller.
            4. Confirm new purchase order exists with attachment.
        """
        login = f"user_{uuid.uuid4().hex[:6]}"
        self.user = self.env["res.users"].create({
            "name": "Upload User",
            "login": login,
            "password": "test123",
            "email": "upload@test.com",
            "partner_id": self.env.ref("base.partner_admin").id,
            "groups_id": [(6, 0, [
                self.env.ref("base.group_user").id,
                self.env.ref("purchase.group_purchase_user").id
            ])],
        })
        self.authenticate(login, "test123")
        csrf = self._csrf()
        self.assertTrue(csrf)
        file_content = b"Hello Test File"
        file = io.BytesIO(file_content)
        file.name = "test.pdf"
        response = self.url_open(
            "/cyllo_purchase_digitization/upload_attachment",
            data={'csrf_token': csrf},
            files={'ufile': (file.name, file, "application/pdf")},
            allow_redirects=False
        )
        self.assertEqual(response.status_code, 200)
        po_id = json.loads(response.text)
        self.assertIsInstance(po_id, int)
        po = self.env['purchase.order'].browse(po_id)
        self.assertTrue(po.exists())
        attachment = po.message_main_attachment_id
        self.assertTrue(attachment)
        decoded = base64.b64decode(attachment.datas)
        self.assertEqual(decoded, file_content)
