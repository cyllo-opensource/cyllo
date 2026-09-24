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
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase

_logger = logging.getLogger(__name__)


class TestResConfigSettings(TestPayrollManagementBase):
    """Test for settings"""
    def test_onchange_batch_move_line_true(self):
        _logger.info('Test for onchange batch move line')
        self.config_settings_model = self.env['res.config.settings']
        config_settings = self.config_settings_model.create({})
        config_settings.batch_move_line = True
        config_settings._onchange_batch_move_line()
        self.assertTrue(self.env.user.company_id.batch_move_line)
        _logger.info('Test success for onchange batch move line')

    def test_onchange_batch_move_line_false(self):
        _logger.info('Test for onchange batch move line')
        self.config_settings_model = self.env['res.config.settings']
        config_settings = self.config_settings_model.create({})
        config_settings.batch_move_line = False
        config_settings._onchange_batch_move_line()
        self.assertFalse(self.env.user.company_id.batch_move_line)
        _logger.info('Test success for onchange batch move line false')

