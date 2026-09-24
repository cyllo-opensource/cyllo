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
import datetime

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

_logger = logging.getLogger(__name__)


class TestGratuitySettlement(TestPayrollManagementBase):
    """Test for gratuity settlement"""

    def _create_gratuity_configuration(self, name, **values):
        today = fields.Date.today()
        vals = {
            'name': name,
            'contract_type': 'open',
            'start_date': today - datetime.timedelta(days=1),
            'end_date': today + datetime.timedelta(days=1),
            'gratuity_configuration_ids': [(0, 0, {
                'name': '%s Line' % name,
                'from_year': 0,
                'to_year': 0,
                'divide_days': 30,
                'extra_days': 21,
                'percentage': 100,
            })],
        }
        vals.update(values)
        return self.env['gratuity.configuration'].create(vals)

    def _create_gratuity_settlement(self, configuration, **values):
        vals = {
            'employee_id': self.employee_01.id,
            'state': 'draft',
            'contract_type': 'open',
            'gratuity_configuration_id': configuration.id,
            'gratuity_duration_line_id': configuration.gratuity_configuration_ids[:1].id,
        }
        vals.update(values)
        return self.env['gratuity.settlement'].create(vals)

    def test_onchange_employee_id(self):
        _logger.info('Test for onchange employee id')
        self.settlement = self.env['gratuity.settlement'].new({
            'employee_id': self.employee_01.id,
            'state': 'draft',
        })
        self.settlement._onchange_employee_id()
        self.assertEqual(self.settlement.contract_id, self.contract_01)
        _logger.info('Test success for onchange employee id')

    def test_onchange_employee_id_configuration(self):
        _logger.info('Test for onchange employee without running contract')
        employee = self.env['hr.employee'].create({'name': 'No Contract Employee'})
        with self.assertRaises(ValidationError) as VE:
            self.settlement_01 = self.env['gratuity.settlement'].new({
                'employee_id': employee.id,
                'state': 'draft',
            })
            self.settlement_01._onchange_employee_id()
        self.assertEqual(VE.exception.args[0],
                         'No running contract found for selected employee')
        _logger.info('Test success for onchange employee without running contract')

    def test_action_submit(self):
        _logger.info('Test for action submit')
        self.journal_02 = self.env['account.journal'].create({
            'name': 'Journal',
            'code': 'JNL',
            'type': 'bank'
        })
        self.credit_account_03 = self.env['account.account'].create({
            'name': 'Credit',
            'code': 'TESTCREDIT',
            'account_type': 'asset_receivable',
        })
        self.debit_account_03 = self.env['account.account'].create({
            'name': 'Debit',
            'code': 'TESTDEBIT',
            'account_type': 'asset_receivable',
        })
        self.gratuity_configuration_03 = self._create_gratuity_configuration(
            'Gratuity Configuration Submit'
        )
        self.settlement_02 = self._create_gratuity_settlement(
            self.gratuity_configuration_03
        )
        self.settlement_02.action_confirm()
        self.assertEqual(self.settlement_02.state, 'confirm')
        _logger.info('Test success for action submit')

    def test_action_approve(self):
        _logger.info('Test for action approve')
        self.journal_03 = self.env['account.journal'].create({
            'name': 'Journal',
            'code': 'JNL',
            'type': 'bank'
        })
        self.credit_account_04 = self.env['account.account'].create({
            'name': 'Credit',
            'code': 'TESTCREDIT',
            'account_type': 'asset_receivable',
        })
        self.debit_account_04 = self.env['account.account'].create({
            'name': 'Debit',
            'code': 'TESTDEBIT',
            'account_type': 'asset_receivable',
        })
        self.gratuity_configuration_04 = self._create_gratuity_configuration(
            'Gratuity Configuration Approve'
        )
        self.settlement_03 = self._create_gratuity_settlement(
            self.gratuity_configuration_04
        )
        self.settlement_03.action_confirm()
        self.assertEqual(self.settlement_03.state, 'confirm')
        _logger.info('Test success for action approve')

    def test_action_cancel(self):
        _logger.info('Test for action cancel')
        self.journal_04 = self.env['account.journal'].create({
            'name': 'Journal',
            'code': 'JNL',
            'type': 'bank'
        })
        self.credit_account_04 = self.env['account.account'].create({
            'name': 'Credit',
            'code': 'TESTCREDIT',
            'account_type': 'asset_receivable',
        })
        self.debit_account_04 = self.env['account.account'].create({
            'name': 'Debit',
            'code': 'TESTDEBIT',
            'account_type': 'asset_receivable',
        })
        self.gratuity_configuration_04 = self._create_gratuity_configuration(
            'Gratuity Configuration Cancel',
        )
        self.settlement_04 = self._create_gratuity_settlement(
            self.gratuity_configuration_04
        )
        self.settlement_04.action_cancel()
        self.assertEqual(self.settlement_04.state, 'cancel')
        _logger.info('Test success for action cancel')
