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
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestHrJobLinkedin(TransactionCase):

    def setUp(self):
        super().setUp()

        self.job = self.env["hr.job"].create({
            "name": "Python Developer",
        })

    def test_redirect_uri(self):
        uri = self.job._get_linkedin_post_redirect_uri()

        self.assertIn("/linkedin/redirect", uri)

    def test_share_linkedin_without_credentials(self):
        provider = self.env.ref(
            "cyllo_hr_linkedin_recruitment.provider_linkedin"
        )

        provider.client_id = False
        provider.client_secret = False

        with self.assertRaises(ValidationError):
            self.job.share_linkedin()

    @patch("requests.request")
    def test_share_request(self, mock_request):
        mock_request.return_value.status_code = 201

        response = self.job.share_request(
            "POST",
            "https://example.com",
            "token",
            "{}",
        )

        self.assertEqual(response.status_code, 201)

    @patch("requests.request")
    def test_get_urn(self, mock_request):
        mock_request.return_value.status_code = 200

        response = self.job.get_urn(
            "GET",
            "https://example.com",
            "token",
        )

        self.assertEqual(response.status_code, 200)