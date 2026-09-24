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
from odoo.tests.common import TransactionCase


class TestCommon(TransactionCase):
    """Test methods of the Consolidation Account"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cons_chart = cls.env['consolidation.chart'].create({
            'name': 'Test Chart',
            'currency_id': cls.env.company.currency_id.id,
        })
        cls.cons_group1 = cls.env['consolidation.group'].create({
            'name': 'Test Group',
            'chart_id': cls.cons_chart.id,
        })
        cls.cons_group2 = cls.env['consolidation.group'].create({
            'name': 'Test Group',
            'view_name': 'Test View Name',
            'chart_id': cls.cons_chart.id,
            'group_id': cls.cons_group1.id,
        })
        cls.consolidation_ac = cls.env['consolidation.account'].create({
            'name': 'Test',
            'view_name': 'Test View',
            'chart_id': cls.cons_chart.id,
            'group_id': cls.cons_group2.id,
        })
        cls.cons_period = cls.env['consolidation.period'].create({
            'chart_id': cls.cons_chart.id,
            'state': 'draft',
            'start_date': '2000-1-1',
            'end_date': '2000-1-10',
        })
        cls.cons_journal = cls.env['consolidation.journal'].create({
            'name': 'Test Consolidation Journal',
            'chart_id': cls.cons_chart.id,
        })
