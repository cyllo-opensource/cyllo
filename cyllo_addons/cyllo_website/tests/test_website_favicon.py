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

from PIL import Image

from odoo import tools
from odoo.tests import common

FAVICON_PATH = 'cyllo_website/static/img/cyllo-favicon.ico'


class TestCylloWebsiteFavicon(common.TransactionCase):
    """Tests for the debranded website favicon."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with tools.file_open(FAVICON_PATH, 'rb') as favicon_file:
            cls.expected_favicon = base64.b64encode(favicon_file.read())

    def test_favicon_asset_is_shipped(self):
        """The Cyllo favicon file ships with the module."""
        self.assertTrue(self.expected_favicon)

    def test_new_website_uses_cyllo_favicon(self):
        """A newly created website defaults to the Cyllo favicon."""
        website = self.env['website'].create({'name': 'Cyllo Test Website'})
        self.assertEqual(website.favicon, self.expected_favicon)

    def test_default_favicon_helper(self):
        """_default_favicon returns the encoded Cyllo icon."""
        self.assertEqual(
            self.env['website']._default_favicon(),
            self.expected_favicon,
        )

    def test_favicon_can_still_be_overridden(self):
        """The default does not prevent setting a custom favicon."""
        website = self.env['website'].create({'name': 'Cyllo Custom Favicon'})
        stream = io.BytesIO()
        Image.new('RGB', (32, 32), color=(255, 0, 0)).save(stream, format='PNG')
        website.favicon = base64.b64encode(stream.getvalue())
        self.assertTrue(website.favicon)
        self.assertNotEqual(website.favicon, self.expected_favicon)
