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
import datetime
import logging

from odoo import fields
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

_logger = logging.getLogger(__name__)


class TestResignationRequest(TestPayrollManagementBase):
    """Test case for resignation request"""

    def test_action_cancel_request(self):
        _logger.info('Test case for action cancel')
        self.resignation.action_cancel_request()
        self.assertEqual(self.resignation.state, 'cancel')
        _logger.info('Test success for action cancel')

    def test_action_approve_request(self):
        _logger.info('Test for action approve request')
        self.resignation.write({
            'approved_date': fields.datetime.now(),
            'notice_period': 10
        })
        self.resignation.action_approve_request()
        self.assertEqual(self.resignation.state, 'approved')
        _logger.info('Test success for action approve')

    def test_action_reject_request(self):
        _logger.info('Test for action reject request')
        self.resignation.action_reject_request()
        self.assertEqual(self.resignation.state, 'cancel')
        _logger.info('Test success for action reject request')

    def test_action_reset_to_draft(self):
        _logger.info('Test for action reset to draft')
        self.resignation.action_reset_to_draft()
        self.assertEqual(self.resignation.state, 'draft')
        _logger.info('Test success for action rest to draft')

    def test_compute_leaving_date(self):
        _logger.info('Test for compute leaving date')
        self.resignation.write({
            'approved_date': fields.datetime.now(),
            'notice_period': 10
        })
        self.resignation._compute_leaving_date()
        approved_date = fields.Date.from_string(self.resignation.approved_date)
        leaving_date = approved_date + datetime.timedelta(
            days=self.resignation.notice_period)
        self.resignation.leaving_date = fields.Date.to_string(leaving_date)
        self.assertEqual(self.resignation.leaving_date, leaving_date)
        _logger.info('Test success for compute leaving date')

    def test_onchange_employee_id(self):
        _logger.info('Test for onchange employee')
        self.resignation._onchange_employee_id()
        existing_records = self.resignation.search([
            ('employee_id', '=', self.employee_01.id),
            ('state', 'in', ['confirm', 'approved'])
        ])
        self.assertFalse(existing_records)
        _logger.info('Test success for onchange employee')
