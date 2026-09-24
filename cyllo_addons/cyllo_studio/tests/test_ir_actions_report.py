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

class TestIrActionsReport(TransactionCase):
    """
    Test cases for 'ir.actions.report' customizations in Studio, 
    covering report value retrieval and QWeb template processing.
    """

    def setUp(self):
        """
        Setup test environment for report actions.
        """
        super(TestIrActionsReport, self).setUp()
        self.Report = self.env['ir.actions.report']

    def test_get_values(self):
        """
        Test the retrieval of report metadata values.
        """
        values = self.Report.get_values()
        self.assertIsInstance(values, list)
        if values:
            self.assertIn('report_name', values[0])
            self.assertIn('model', values[0])

    def test_get_qweb(self):
        """
        Test retrieving QWeb templates related to specific reports.
        """
        self.Report.create({
            'name': 'Test Studio Report',
            'model': 'res.partner',
            'report_name': 'test.studio_report_template',
            'report_type': 'qweb-html',
        })
        
        self.env['ir.ui.view'].create({
            'name': 'studio_report_template',
            'type': 'qweb',
            'arch': '<t t-name="test.studio_report_template"><div>Test</div></t>',
        })
        
        qwebs = self.Report.get_qweb({'report_name': 'test.studio_report_template'})
        self.assertIsInstance(qwebs, list)
        self.assertTrue(any('Test' in q['arch'] for q in qwebs))
