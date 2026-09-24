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
from odoo.tests.common import TransactionCase


class TestIrAttachmentFacebook(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.attachment = cls.env['ir.attachment'].create({
            'name': 'Test Attachment',
            'type': 'binary',
            'datas': 'VGhpcyBpcyBhIHRlc3QgZmlsZQ==',
            'res_model': 'res.users',
            'res_id': cls.env.user.id,
        })

    def test_fb_public_url_computed(self):
        """Test computed Facebook public URL for attachment"""

        self.assertTrue(
            self.attachment.fb_public_url,
            "fb_public_url should be computed"
        )

        base_url = self.attachment.get_base_url()
        expected_url = f"{base_url}/web/content/{self.attachment.id}"

        self.assertEqual(
            self.attachment.fb_public_url,
            expected_url,
            "Computed fb_public_url should match expected format"
        )
