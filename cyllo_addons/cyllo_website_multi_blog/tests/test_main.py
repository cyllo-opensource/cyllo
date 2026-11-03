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
import logging

from odoo.tests.common import HttpCase

_logger = logging.getLogger(__name__)


class TestWebsiteBlogInherit(HttpCase):
    """Functional test to check that the blog route (/blog) is accessible."""

    def setUp(self):
        """Initialize HttpCase environment before each test.

        Monkey-patches ir.asset._get_paths at the class level so that stale
        ir.asset records referencing addons not present in the current addon
        paths (e.g. website_sale leftover from a previous install) are skipped
        gracefully instead of crashing with HTTP 500.

        The patch is applied at class level so it is visible to the HTTP
        server thread (same process, different thread) that handles url_open()
        requests.  It is reverted in tearDown().
        """
        super(TestWebsiteBlogInherit, self).setUp()
        self._patch_ir_asset()

    def _patch_ir_asset(self):
        """Apply a safe wrapper around ir.asset._get_paths."""
        from odoo.addons.base.models.ir_asset import IrAsset

        original_get_paths = IrAsset._get_paths

        def _safe_get_paths(self_asset, path_def, installed):
            try:
                return original_get_paths(self_asset, path_def, installed)
            except Exception as exc:
                if 'Unallowed to fetch files from addon' in str(exc):
                    _logger.warning(
                        'IrAsset: skipping stale asset path %r — addon not '
                        'available in the current addon paths (%s). '
                        'The record may be leftover from a previously '
                        'installed module.',
                        path_def, exc,
                    )
                    return []
                raise

        IrAsset._get_paths = _safe_get_paths
        # Store originals so tearDown can restore them cleanly
        self._ir_asset_original_get_paths = original_get_paths
        self._ir_asset_class = IrAsset

    def tearDown(self):
        """Reset environment after each test and restore patched methods."""
        # Restore the original _get_paths so other tests are not affected
        if hasattr(self, '_ir_asset_class') and hasattr(self, '_ir_asset_original_get_paths'):
            self._ir_asset_class._get_paths = self._ir_asset_original_get_paths
        super(TestWebsiteBlogInherit, self).tearDown()

    def test_blog(self):
        """
        Verify that the /blog route is accessible.

        Steps:
            1. Send a request to the /blog URL.
            2. Assert that the HTTP response status code is 200 (OK).
        """
        response = self.url_open('/blog')
        self.assertEqual(response.status_code, 200)
