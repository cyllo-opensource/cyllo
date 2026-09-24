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

class TestIrModel(TransactionCase):
    """
    Test cases for 'ir.model' enhancements in Studio, including custom model
    creation and model action validation.
    """

    def setUp(self):
        """
        Setup test environment for model-related operations.
        """
        super(TestIrModel, self).setUp()
        self.IrModel = self.env['ir.model']

    def test_create_new_model(self):
        """
        Test the end-to-end creation of a new custom model with associated views and menus.
        """
        app_name = "Test App"
        module_name = "test_module"
        
        result = self.IrModel.create_new_model(app_name, module_name)
        
        (model_name, model_technical_name, model_id, access_user,
         access_admin, form_view, list_view, search_view, 
         menu_action, menu_item) = result

        self.assertEqual(model_name, app_name)
        self.assertTrue(model_technical_name.startswith('x_cyllo_'))
        self.assertEqual(form_view.type, 'form')
        self.assertEqual(list_view.type, 'tree')
        self.assertEqual(search_view.type, 'search')
        self.assertEqual(menu_item.name, app_name)
        self.assertTrue(menu_item.is_studio)

    def test_get_model_actions(self):
        """
        Test retrieving valid actions available for a specific model.
        """
        actions = self.IrModel.get_model_actions('res.partner')
        self.assertIn('create', actions)
        self.assertIn('write', actions)
        self.assertIn('unlink', actions)
        
        actions = self.IrModel.get_model_actions('non.existent.model')
        self.assertEqual(actions, [])

    def test_validate_model_action(self):
        """
        Test the validation logic for specific model actions.
        """
        self.assertTrue(self.IrModel.validate_model_action('res.partner', 'write'))
        self.assertFalse(self.IrModel.validate_model_action('res.partner', 'non_existent_action'))
        self.assertFalse(self.IrModel.validate_model_action('non.existent.model', 'write'))
