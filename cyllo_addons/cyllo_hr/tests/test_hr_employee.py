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


class TestHREmployee(TransactionCase):
    """
    Test cases for the custom method `action_open_record`
    in the hr.employee model.
    """
    @classmethod
    def setUpClass(cls):
        """
        Set up test data before running test cases.

        This method creates a sample employee record
        that will be used in the test cases.
        """
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'John Doe',
        })

    def test_action_open_record(self):
        """
        Test the `action_open_record` method.

        Steps:
            1. Attach the employee ID to the context.
            2. Call the `action_open_record` method.
            3. Verify the returned dictionary contains:
                - type: 'ir.actions.act_window'
                - res_model: 'hr.employee'
                - res_id: correct employee ID
                - target: 'new'
                - views: includes form view
        """
        emp = self.employee.with_context(id=self.employee.id)
        action = emp.action_open_record()
        self.assertIsInstance(action, dict,
                              "The action should be a dictionary.")
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'hr.employee')
        self.assertEqual(action.get('res_id'), self.employee.id)
        self.assertEqual(action.get('target'), 'new')
        self.assertIn(('form',), [tuple(v for v in view if v)
                                  for view in
                                  action.get('views')])
