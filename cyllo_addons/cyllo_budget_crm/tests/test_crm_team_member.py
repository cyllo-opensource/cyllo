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
from datetime import timedelta

from odoo import fields

from .common import TestBudgetCrm


class TestCrmTeamMember(TestBudgetCrm):
    """Test methods of the Budget Lines"""

    def test_compute_budget_line_ids(self):
        # Invoke the method
        self.crm_member01._compute_budget_line_ids()
        # Check the result
        self.assertEqual(len(self.crm_member01.budget_line_ids), 1)
        self.assertEqual(self.crm_member01.budget_line_ids[0].start_date,
                         fields.Date.today() + timedelta(days=-5))
        self.assertEqual(self.crm_member01.budget_line_ids[0].end_date,
                         fields.Date.today() + timedelta(days=5))
        self.assertEqual(self.crm_member01.budget_line_ids[0].planned_amount,
                         1100)

    def test_compute_state(self):
        # Set target amount
        self.crm_member01.target_amount = 250
        # Invoke the method to compute state
        self.crm_member01._compute_state()
        # Assert that the state is set to 'achieved'
        self.assertEqual(self.crm_member01.state, 'achieved')
