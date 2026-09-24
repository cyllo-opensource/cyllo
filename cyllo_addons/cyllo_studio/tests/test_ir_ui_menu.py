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
from unittest.mock import MagicMock, patch

class TestIrUiMenu(TransactionCase):
    """
    Test cases for 'ir.ui.menu' modifications in Studio, specifically 
    filtering and behavior in Studio mode.
    """

    def setUp(self):
        """
        Setup test environment for menu-related tests.
        """
        super(TestIrUiMenu, self).setUp()
        self.Menu = self.env['ir.ui.menu']

    def test_get_user_roots_studio_mode(self):
        """
        Test the retrieval of root menu items in and out of Studio mode.
        """
        mock_request = MagicMock()
        mock_request.session.studio = None
        
        with patch('odoo.addons.cyllo_studio.models.ir_ui_menu.request', mock_request):
            roots = self.Menu.get_user_roots()
            self.assertTrue(all(not root.parent_id for root in roots))

        mock_request.session.studio = '1'
        with patch('odoo.addons.cyllo_studio.models.ir_ui_menu.request', mock_request):
            test_menu = self.Menu.create({
                'name': 'Studio Test Menu',
                'active': False,
                'parent_id': False,
                'sequence': 100,
            })
            
            roots = self.Menu.get_user_roots()
            self.assertIn(test_menu, roots)
            
            tests_menu = self.Menu.create({
                'name': 'Tests',
                'parent_id': False,
                'sequence': 101,
            })
            roots = self.Menu.get_user_roots()
            self.assertNotIn(tests_menu, roots)
