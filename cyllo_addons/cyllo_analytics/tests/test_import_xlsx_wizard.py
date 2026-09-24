# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError
import base64
import json
import csv
import io

@tagged('-at_install', 'post_install')
class TestImportXlsxWizard(TransactionCase):

    def setUp(self):
        super(TestImportXlsxWizard, self).setUp()
        self.wizard_model = self.env['import.xlsx.wizard']

    def test_json_import_flow(self):
        """Test importing a JSON file and generating a dynamic table."""
        # Create a mock JSON payload
        mock_data = [
            {"Name": "Alice", "Age": 30, "IsActive": True},
            {"Name": "Bob", "Age": 25, "IsActive": False},
        ]
        file_content = base64.b64encode(json.dumps(mock_data).encode('utf-8'))

        wizard = self.wizard_model.create({
            'file': file_content,
            'file_name': 'test_data.json',
            'table_label': 'Test Employees',
        })

        # Test table name auto-formatting
        wizard._onchange_table_label()
        self.assertEqual(wizard.table_name, 'x_test_employees')

        # 1. Analyze File
        action = wizard.action_analyze_file()
        self.assertEqual(wizard.state, 'columns')
        
        # Verify columns were extracted correctly
        self.assertEqual(len(wizard.column_lines), 3)
        col_names = wizard.column_lines.mapped('column_name')
        self.assertIn('Name', col_names)
        self.assertIn('Age', col_names)
        self.assertIn('IsActive', col_names)

        # 2. Confirm Import
        wizard.action_import_data_confirm()

        # Check if the ir.model was created
        ir_model = self.env['ir.model'].search([('model', '=', 'x_test_employees')])
        self.assertTrue(ir_model)
        
        # Check if fields were created
        fields = self.env['ir.model.fields'].search([('model_id', '=', ir_model.id)])
        field_names = fields.mapped('name')
        self.assertIn('x_name', field_names)  # Safe generated name for 'Name'
        self.assertIn('x_age', field_names)
        self.assertIn('x_isactive', field_names)

        # Check if registry was updated
        registry = self.env['custom.imported.table'].search([('model_id', '=', ir_model.id)])
        self.assertTrue(registry)
        
        # Since we cannot easily query the dynamically created model inside the same transaction
        # without committing (Odoo test rollback), we at least assert the model definition exists.
        
    def test_csv_import_flow(self):
        """Test importing a CSV file."""
        csv_content = "Product,Price,Stock\nApple,1.5,100\nBanana,0.5,200"
        file_content = base64.b64encode(csv_content.encode('utf-8'))

        wizard = self.wizard_model.create({
            'file': file_content,
            'file_name': 'products.csv',
            'table_label': 'Test Products',
        })
        wizard._onchange_table_label()

        wizard.action_analyze_file()
        self.assertEqual(wizard.state, 'columns')
        
        col_names = wizard.column_lines.mapped('column_name')
        self.assertEqual(col_names, ['Product', 'Price', 'Stock'])
        
        # Test selection field invalidation
        # Manually change a field to selection without options
        wizard.column_lines[0].field_type = 'selection'
        wizard.column_lines[0].selection_options = False
        
        with self.assertRaises(UserError):
            wizard.action_import_data_confirm()

    def test_validation_errors(self):
        """Test validation and user errors in the wizard."""
        # Missing file
        wizard = self.wizard_model.create({
            'file_name': 'empty.json'
        })
        with self.assertRaises(Exception): # Odoo required field constraint
            wizard.action_analyze_file()
            
        # Invalid column names
        with self.assertRaises(ValidationError):
            self.wizard_model.create({
                'file': base64.b64encode(b'{}'),
                'file_name': 'test.json',
                'start_col': '123'
            })
            
        # Invalid table name format
        wizard3 = self.wizard_model.create({
            'file': base64.b64encode(b'[{"Test": "A"}]'),
            'file_name': 'test.json',
            'table_name': 'invalid_no_x',
            'table_label': 'Invalid',
        })
        wizard3.action_analyze_file()
        with self.assertRaises(UserError):
            wizard3.action_import_data_confirm()
