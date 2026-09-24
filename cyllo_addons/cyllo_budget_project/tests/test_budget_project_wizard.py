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
from .common import TestBudgetProject


class TestBudgetProjectWizard(TestBudgetProject):
    """Test methods of the Budget Lines"""

    def test_action_create_project(self):
        # Set the necessary attributes
        self.budget_project01.project_name = "Test Project"
        self.budget_project01.budget_id = self.budget05
        # Invoke the method
        self.budget_project01.action_create_project()
        # Assert the expected results
        self.assertEqual(self.budget_project01.project_id.name, "Test Project")
        self.assertEqual(self.budget_project01.project_id.budget_id,
                         self.budget_project01.budget_id)
        self.assertEqual(self.budget_project01.budget_id.project_id,
                         self.budget_project01.project_id)
        self.assertTrue(self.budget_project01.budget_id.check_project)
