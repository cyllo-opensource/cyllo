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


class TestGratuityConfiguration(TestPayrollManagementBase):
    """Test for gratuity configuration"""

    def test_onchange_start_date(self):
        _logger.info('Test for onchange start date')
        self.journal = self.env['account.journal'].create({
            'name': 'Journal',
            'code': 'JNL',
            'type': 'bank'
        })
        self.credit_account = self.env['account.account'].create({
            'name': 'Credit',
            'code': 'TESTCREDIT',
            'account_type': 'asset_receivable',
        })
        self.debit_account = self.env['account.account'].create({
            'name': 'Debit',
            'code': 'TESTDEBIT',
            'account_type': 'asset_receivable',
        })
        with self.assertRaises(ValidationError) as VE:
            self.gratuity_configuration = self.env[
                'gratuity.configuration'].create(
                {
                    'name': 'Gratuity Configuration',
                    'contract_type': 'limited',
                    'start_date': '2018-02-02',
                    'end_date': '2018-01-01',
                })
            self.gratuity_configuration._onchange_start_date()
        self.assertEqual(VE.exception.args[0],
                         'End date must be grater than the start date ')
        _logger.info('Test success for onchange start date')


class TestGratuityConfigurationLine(TestPayrollManagementBase):
    """Test for gratuity configuration line"""

    def test_onchange_from_year(self):
        _logger.info('Test for onchange year')
        with self.assertRaises(ValidationError) as VE:
            self.configuration_line = self.env[
                'gratuity.configuration.line'].create({
                'name': 'Rule1',
                'from_year': 5,
                'to_year': 1
            })
            self.configuration_line._onchange_from_year()
        self.assertEqual(VE.exception.args[0],
                         "'From Year' should be less than 'To Year'.")
        _logger.info('Test success for onchange year')
