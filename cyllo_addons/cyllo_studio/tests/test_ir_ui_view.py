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
from lxml import etree

class TestIrUiView(TransactionCase):
    """
    Test cases for 'ir.ui.view' customizations in Studio, covering view flags
    and security post-processing in Studio mode.
    """

    def setUp(self):
        """
        Setup test environment for view-related tests.
        """
        super(TestIrUiView, self).setUp()
        self.View = self.env['ir.ui.view']

    def test_is_studio_field(self):
        """
        Test the verification of the 'is_studio' flag on UI views.
        """
        view = self.View.create({
            'name': 'Test Studio View',
            'type': 'form',
            'model': 'res.partner',
            'arch': '<form><sheet><field name="name"/></sheet></form>',
            'is_studio': True,
        })
        self.assertTrue(view.is_studio)

    def test_postprocess_access_rights(self):
        """
        Test the modification of view architecture to handle access rights in Studio mode.
        """
        arch = etree.fromstring('<form><field name="name" groups="base.group_erp_manager"/></form>')
        
        mock_request = MagicMock()
        mock_request.session.studio = None
        mock_request.env = self.env
        
        self.patch_erp_manager = patch.object(self.env.user.__class__, 'has_group', return_value=False)
        self.patch_erp_manager.start()
        
        try:
            with patch('odoo.addons.cyllo_studio.models.ir_ui_view.request', mock_request):
                processed_tree = self.View._postprocess_access_rights(arch)
                fields = processed_tree.xpath('//field')
                self.assertEqual(len(fields), 0)

            mock_request.session.studio = '1'
            self.patch_erp_manager.stop()
            self.patch_erp_manager = patch.object(self.env.user.__class__, 'has_group', return_value=True)
            self.patch_erp_manager.start()
            
            arch = etree.fromstring('<form><field name="name" groups="base.group_erp_manager"/></form>')
            with patch('odoo.addons.cyllo_studio.models.ir_ui_view.request', mock_request):
                processed_tree = self.View._postprocess_access_rights(arch)
                fields = processed_tree.xpath('//field')
                self.assertEqual(len(fields), 1)
                self.assertIsNotNone(fields[0].get('cy-xpath'))
        finally:
            self.patch_erp_manager.stop()
