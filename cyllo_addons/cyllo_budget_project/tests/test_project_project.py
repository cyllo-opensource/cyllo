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


class TestProjectProject(TestBudgetProject):
    """Test methods of the Project_Project"""

    def test_action_view_budget(self):
        result = self.project01.action_view_budget()
        self.assertIsInstance(result, dict)
        self.assertIn('type', result)
        self.assertIn('name', result)
        self.assertIn('res_model', result)
        self.assertIn('res_id', result)
        self.assertIn('view_type', result)
        self.assertIn('view_mode', result)
        self.assertIn('target', result)
