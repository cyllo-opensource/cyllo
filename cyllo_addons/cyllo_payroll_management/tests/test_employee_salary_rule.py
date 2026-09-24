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

from odoo.exceptions import UserError, ValidationError
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

_logger = logging.getLogger(__name__)


class TestSalaryRule(TestPayrollManagementBase):
    """Test for employee salary rule"""

    def test_check_parent_rule_id(self):
        _logger.info('Test for check parent rule')
        self.salary_rule = self.env['employee.salary.rule'].create({
            'name': 'Child Rule',
            'code': 'CHILD',
            'amount_select': 'fix',
            'amount_fix': 50,
            'category_id': self.env.ref(
                'cyllo_payroll_management.employee_salary_rule_category_allowance').id
        })
        with self.assertRaises(ValidationError) as VE:
            self.salary_rule.write({
                'parent_rule_id': self.salary_rule.id
            })
            self.child_rule._check_parent_rule_id()
        self.assertEqual(VE.exception.args[0],
                         'Error! You cannot create recursive hierarchy of Salary Rules.')
        _logger.info('Test success for check parent rule')

    def test_recursive_search_of_rules(self):
        _logger.info('Test for recursive function')
        self.parent_rule_1 = self.env['employee.salary.rule'].create(
            {'name': 'Parent Rule 1',
             'sequence': 10, 'code': 'PR1',
             'category_id': self.env.ref(
                 'cyllo_payroll_management.employee_salary_rule_category_allowance').id})
        self.child_rule_1 = self.env['employee.salary.rule'].create(
            {'name': 'Child Rule 1',
             'sequence': 20,
             'code': 'CR1',
             'parent_rule_id': self.parent_rule_1.id,
             'category_id': self.env.ref(
                 'cyllo_payroll_management.employee_salary_rule_category_allowance').id})
        self.child_rule_2 = self.env['employee.salary.rule'].create(
            {'name': 'Child Rule 2',
             'sequence': 30,
             'code': 'CR2',
             'parent_rule_id': self.parent_rule_1.id,
             'category_id': self.env.ref(
                 'cyllo_payroll_management.employee_salary_rule_category_allowance').id})
        self.grandchild_rule_1 = self.env['employee.salary.rule'].create({
            'name': 'Grandchild Rule 1',
            'sequence': 40,
            'code': 'GR1',
            'parent_rule_id': self.child_rule_1.id,
            'category_id': self.env.ref(
                'cyllo_payroll_management.employee_salary_rule_category_allowance').id})
        self.rule_ids = self.parent_rule_1._recursive_search_of_rules()
        expected_result = [
            (self.parent_rule_1.id, self.parent_rule_1.sequence),
            (self.child_rule_1.id, self.child_rule_1.sequence),
            (self.grandchild_rule_1.id, self.grandchild_rule_1.sequence),
            (self.child_rule_2.id, self.child_rule_2.sequence)
        ]
        self.assertCountEqual(self.rule_ids, expected_result,
                              "Recursive search result does not match expected result")
        _logger.info('Test success for recursive function')

    def test_satisfy_condition_none(self):
        _logger.info('Test condition_select = "none"')

        self.rule_01 = self.env['employee.salary.rule'].create({
            'name': ' Rule1',
            'code': 'RULE_1',
            'condition_select': 'none',
            'category_id': self.env.ref(
                'cyllo_payroll_management.employee_salary_rule_category_allowance').id
        })
        localdict = {}
        self.assertTrue(self.rule_01._satisfy_condition(localdict))
        _logger.info('Test success for condition_select = "none"')

    def test_satisfy_condition_range_true(self):
        """ Test condition_select = 'range' with valid condition """
        _logger.info('Test condition_select = "range" with valid condition')
        self.rule_02 = self.env['employee.salary.rule'].create({
            'name': ' Rule2',
            'code': 'RULE_2',
            'condition_select': 'range',
            'category_id': self.env.ref(
                'cyllo_payroll_management.employee_salary_rule_category_allowance').id
        })
        self.rule_02.condition_range = 50
        self.rule_02.condition_range_min = 40
        self.rule_02.condition_range_max = 60
        localdict = {'result': 50}
        self.assertTrue(self.rule_02._satisfy_condition(localdict))
        _logger.info(
            'Test success for condition_select = "range" with valid condition')

    def test_satisfy_condition_range_false(self):
        _logger.info('Test condition_select = "range" with invalid condition')
        self.rule_03 = self.env['employee.salary.rule'].create({
            'name': ' Rule3',
            'code': 'RULE_3',
            'condition_select': 'range',
            'category_id': self.env.ref(
                'cyllo_payroll_management.employee_salary_rule_category_allowance').id
        })
        self.rule_03.condition_range = '65'
        self.rule_03.condition_range_min = 40
        self.rule_03.condition_range_max = 60
        localdict = {'result': 65}
        self.rule_03._satisfy_condition(localdict)
        self.assertFalse(self.rule_03._satisfy_condition(localdict))
        _logger.info(
            'Test success for condition_select = "range" with invalid condition')

    def test_satisfy_condition_python_true(self):
        _logger.info("Test condition_select = 'python' with valid condition")
        self.rule_03 = self.env['employee.salary.rule'].create({
            'name': ' Rule3',
            'code': 'RULE_3',
            'condition_select': 'python',
            'category_id': self.env.ref(
                'cyllo_payroll_management.employee_salary_rule_category_allowance').id
        })
        self.rule_03.condition_python = 'result = True'
        localdict = {}
        self.assertTrue(self.rule_03._satisfy_condition(localdict))
        _logger.info('Test success for python valid case')

    def test_satisfy_condition_python_false(self):
        """ Test condition_select = 'python' with invalid condition """
        self.rule_04 = self.env['employee.salary.rule'].create({
            'name': ' Rule4',
            'code': 'RULE_4',
            'condition_select': 'python',
            'category_id': self.env.ref(
                'cyllo_payroll_management.employee_salary_rule_category_allowance').id
        })
        self.rule_04.condition_python = 'result = False'
        localdict = {}
        self.assertFalse(self.rule_04._satisfy_condition(localdict))
        _logger.info('Test success for python invalid condition')

    def test_compute_rule(self):
        _logger.info('Test for compute rule')
        self.rule_05 = self.env['employee.salary.rule'].create({
            'name': ' Rule5',
            'code': 'RULE_5',
            'amount_select': 'fix',
            'category_id': self.env.ref(
                'cyllo_payroll_management.employee_salary_rule_category_allowance').id
        })
        self.rule_05.write({
            'amount_fix': 5700.0
        })
        localdict = {'result': 5700}
        self.rule_05._compute_rule(localdict)
        self.assertTrue(self.rule_05._compute_rule(localdict))
        _logger.info('Test success for compute rule')

    def test_compute_rule_valid_percentage(self):
        _logger.info('Test for compute rule valid')
        self.rule_06 = self.env['employee.salary.rule'].create({
            'name': ' Rule6',
            'code': 'RULE_6',
            'amount_select': 'percentage',
            'category_id': self.env.ref(
                'cyllo_payroll_management.employee_salary_rule_category_allowance').id
        })
        self.rule_06.write({
            'amount_percentage_base': 5,
            'quantity': 1
        })
        localdict = {'result': 5}
        self.rule_06._compute_rule(localdict)
        self.assertTrue(self.rule_06._compute_rule(localdict))
        _logger.info('Test success for valid percentage compute rule')

    def test_compute_rule_percentage(self):
        _logger.info('Test for compute rule invalid')
        self.rule_07 = self.env['employee.salary.rule'].create({
            'name': ' Rule7',
            'code': 'RULE_7',
            'amount_select': 'percentage',
            'category_id': self.env.ref(
                'cyllo_payroll_management.employee_salary_rule_category_allowance').id
        })
        self.rule_07.write({
            'amount_fix': -1,
            'quantity': 0
        })
        localdict = {'result': '0'}
        with self.assertRaises(UserError) as UE:
            self.rule_07._compute_rule(localdict)
        self.assertEqual(UE.exception.args[0],
                         'Wrong percentage base or quantity defined for salary rule  Rule7 (RULE_7).')
        _logger.info('Test success for invalid percentage compute rule')
