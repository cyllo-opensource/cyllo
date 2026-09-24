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
from . common import TestCommon
from odoo.exceptions import ValidationError


class TestConsolidationAccount(TestCommon):
    """Test methods of the Consolidation Account"""

    def test_compute_view_name(self):
        cons_ac = self.consolidation_ac
        cons_ac._compute_view_name()
        self.assertEqual(cons_ac.view_name,  f'{cons_ac.group_id.view_name} /{cons_ac.name}')
        self.cons_group2.group_id = False
        cons_ac._compute_view_name()
        self.assertEqual(cons_ac.view_name, f'{cons_ac.group_id.name} /{cons_ac.name}')

    def test_check_parent_group(self):
        self.cons_chart2 = self.env['consolidation.chart'].create({
            'name': 'Test Chart',
            'currency_id': self.env.company.currency_id.id,
        })
        with self.assertRaises(ValidationError):
            self.cons_group2.chart_id = self.cons_chart2.id


