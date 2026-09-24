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
from odoo.tests.common import HttpCase


class TestWebsiteBlogInherit(HttpCase):
    """Functional test to check that the blog route (/blog) is accessible."""

    def setUp(self):
        """Initialize HttpCase environment before each test."""
        super(TestWebsiteBlogInherit, self).setUp()

    def test_blog(self):
        """
        Verify that the /blog route is accessible.

        Steps:
            1. Send a request to the /blog URL.
            2. Assert that the HTTP response status code is 200 (OK).
        """
        response = self.url_open('/blog')
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        """Reset environment after each test."""
        super(TestWebsiteBlogInherit, self).tearDown()
