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
import json
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase


class TestFieldServiceRequestReport(TransactionCase):
    """
    Test suite for the FieldServiceRequestReport XLSX report.

    This class verifies:
    - Creation of test records: partner, skill category, and field service request.
    - Creation of a field service report wizard with filter, group_by, and partner_ids.
    - That the XLSX report returns expected keys and values.
    - Correct structure of 'datas' list and 'group_option' for group_by = state.
    - Validation of report options such as start_date, end_date, filter, state, and group_by.
    - Uses mocking to simulate the report data and avoid dependency on database queries.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.category = cls.env['field.service.skill.category'].create({'name': 'Installation'})
        cls.fs_request = cls.env['field.service.request'].create({
            'name': 'FS00001',
            'partner_id': cls.partner.id,
            'priority': 'a',
            'skill_category_id': cls.category.id,
            'company_id': cls.env.company.id,
            'state': 'in_progress',
        })
        cls.wizard = cls.env['field.service.report'].create({
            'from_date': fields.Date.today(),
            'to_date': fields.Date.today(),
            'filter': 'customer_wise',
            'group_by': 'state',
            'partner_ids': [(4, cls.partner.id)],
        })

    def test_get_report_values(self):
        """
        Test the XLSX report generation for FieldServiceRequestReport.

        Steps:
        - Patch the _get_report_values method of the report model to return mock data.
        - Call action_xlsx_print on the wizard to get report options.
        - Parse the options JSON and validate keys and values.
        - Check that datas, group_option, start_date, end_date, filter, state, and group_by match expectations.
        """
        mock_data = {
            'datas': [{'name': 'FS00001', 'partner_name': 'Test Partner', 'state': 'in_progress'}],
            'group_option': [
                ['draft', 'Draft'], ['submit', 'Submitted'], ['assigned', 'Assigned'],
                ['in_progress', 'In Progress'], ['completed', 'Completed']
            ],
            'start_date': str(fields.Date.today()),
            'end_date': str(fields.Date.today()),
            'filter': 'customer_wise',
            'state': 'in_progress',
            'group_by': 'state'
        }

        report_model = self.env['report.cyllo_field_service.report_field_service_request_xlsx']
        with patch.object(report_model.__class__, '_get_report_values', return_value=mock_data):
            result = self.wizard.action_xlsx_print()
            options = json.loads(result['data']['options'])
            data_row = options['datas'][0]
            self.assertEqual(data_row['name'], 'FS00001')
            self.assertEqual(data_row['partner_name'], 'Test Partner')
            self.assertEqual(data_row['state'], 'in_progress')
            self.assertEqual(options['group_option'], [
                ['draft', 'Draft'], ['submit', 'Submitted'], ['assigned', 'Assigned'],
                ['in_progress', 'In Progress'], ['completed', 'Completed']
            ])

            self.assertEqual(options['start_date'], str(fields.Date.today()))
            self.assertEqual(options['end_date'], str(fields.Date.today()))
            self.assertEqual(options['filter'], 'customer_wise')
            self.assertEqual(options['state'], 'in_progress')
            self.assertEqual(options['group_by'], 'state')
