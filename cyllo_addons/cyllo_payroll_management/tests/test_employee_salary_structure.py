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

from odoo.exceptions import ValidationError
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

_logger = logging.getLogger(__name__)


class TestSalaryStructure(TestPayrollManagementBase):
    """Test for employee salary structure"""

    def test_get_parent(self):
        _logger.info('Test for get parent structure')
        self.assertTrue(self.salary_structure._get_parent())
        _logger.info('Test success for get parent structure')

    def test_check_parent_id(self):
        _logger.info('Test for check parent structure')
        with self.assertRaises(ValidationError) as VE:
            self.salary_structure.write({
                'parent_id': self.salary_structure.id
            })
            self.salary_structure._check_parent_id()
        self.assertEqual(VE.exception.args[0],
                         'You cannot create a recursive salary structure.')
        _logger.info('Test success for check parent structure')

    def test_copy(self):
        _logger.info('Test for check copy of the structure')
        self.salary_structure_07 = self.env['employee.salary.structure'].create({
            'name': 'Employee Salary Structure',
            'type_id': self.structure_type.id,
            'code': 'BASE',
        })
        copied_structure = self.salary_structure_07.copy()
        self.assertEqual(copied_structure.code, 'BASE (copy)')
        _logger.info('Test success for check copy of the structure')

    def test_get_all_rules(self):
        _logger.info('Test for check all the rules')
        structure = self.env['employee.salary.structure'].create({
            'name': 'Test Structure',
            'code': 'TEST',
            'type_id': self.structure_type.id,
        })
        all_rules = structure._get_all_rules()
        self.assertTrue(all(
            isinstance(rule, self.env['employee.salary.rule']) for rule in
            all_rules))
        _logger.info('Test success for check all the rules')

    def test_get_parent_structure(self):
        _logger.info('Test for parent structure')
        parent_structure = self.env['employee.salary.structure'].create({
            'name': 'Parent Structure',
            'code': 'PARENT',
            'type_id': self.structure_type.id,
        })
        child_structure = self.env['employee.salary.structure'].create({
            'name': 'Child Structure',
            'code': 'CHILD',
            'parent_id': parent_structure.id,
            'type_id': self.structure_type.id,
        })
        combined_structures = child_structure._get_parent_structure()
        self.assertIn(parent_structure, combined_structures)
        self.assertIn(child_structure, combined_structures)
        _logger.info('Test success for parent structure')

