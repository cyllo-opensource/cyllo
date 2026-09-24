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
from odoo.addons.cyllo_payroll_management.tests.common import \
    TestPayrollManagementBase


class TestAccountMoveLine(TestPayrollManagementBase):
    """Tests for payroll fields added to account move lines."""

    def test_account_move_line_batch_id_field_exists(self):
        fields_info = self.env['account.move.line'].fields_get(['batch_id'])

        self.assertIn('batch_id', fields_info)
        self.assertEqual(fields_info['batch_id']['type'], 'integer')

