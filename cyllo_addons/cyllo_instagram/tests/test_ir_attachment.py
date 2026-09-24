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


class TestIrAttachmentPublicUrl(TransactionCase):
    """
    Test suite for validating the computed `public_url` field
    added to the `ir.attachment` model.
    """

    def test_compute_public_url(self):
        """
        Test that the public_url field is correctly computed
        for an ir.attachment record.

        Test Steps:
        -----------
        1. Create an attachment.
        2. Verify public_url is computed.
        3. Validate URL format and correctness.
        """

        attachment = self.env["ir.attachment"].create({
            "name": "Test Attachment",
            "type": "binary",
            "datas": "VGhpcyBpcyBhIHRlc3QgZmlsZQ==",
            "res_model": "res.partner",
            "res_id": self.env.user.partner_id.id,
        })

        self.assertTrue(attachment)

        base_url = attachment.get_base_url()
        expected_url = "%s/web/content/%s" % (base_url, attachment.id)

        self.assertTrue(
            attachment.public_url,
            "Public URL should be computed for the attachment"
        )
        self.assertEqual(
            attachment.public_url,
            expected_url,
            "Computed public URL does not match expected format"
        )
