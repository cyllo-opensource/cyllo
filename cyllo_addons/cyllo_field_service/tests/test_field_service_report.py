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
import io
import json
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase


class TestFieldServiceReport(TransactionCase):
    """
    Test class for Field Service Report functionality.

    This test class covers the following areas:

    1. **Action Methods:**
        - `action_print`: Ensures that the PDF report action is correctly
          returned and the report's `report_action` is called.

        - `action_xlsx_print`: Ensures that the XLSX report action is correctly
          returned, that the data options are correctly structured, and
          the report generation logic prepares the expected payload.

    2. **Report Generation:**
        - `get_xlsx_report`: Validates that the XLSX report is generated
          correctly from JSON input, written to a response stream,
          and contains actual data.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a test wizard/record for Field Service Report
        cls.wizard = cls.env['field.service.report'].create({
            'from_date': '2025-01-01',
            'to_date': '2025-12-31',
            'filter': 'customer_wise',
            'group_by': 'state',
        })

    def test_action_print(self):
        """
        Test the `action_print` function with a mocked report.

        Steps:
            1. Create a mock report object with `report_action` returning
               a fixed dictionary.
            2. Patch `self.wizard.env.ref` to return the mock report.
            3. Call `action_print` and verify:
                - The report action is called exactly once.
                - The returned dictionary matches the expected type.
        """
        mock_report = MagicMock()
        mock_report.report_action.return_value = {'type': 'ir.actions.report'}

        with patch.object(self.wizard.env, 'ref', return_value=mock_report):
            result = self.wizard.action_print()
            mock_report.report_action.assert_called_once()
            self.assertEqual(result, {'type': 'ir.actions.report'})

    def test_action_xlsx_print(self):
        """
        Test `action_xlsx_print` with mocked report values.

        Steps:
            1. Create a mock report object that returns expected report values.
            2. Patch `self.wizard.env['report.cyllo_field_service.report_field_service_request_xlsx']`
               to return the mock report.
            3. Call `action_xlsx_print` and verify:
                - Returned type is `ir.actions.report`.
                - Report type is `xlsx`.
                - Report name contains expected string.
                - JSON options include active_id, start_date, end_date,
                  'datas', and 'group_option'.
        """
        mock_report = MagicMock()
        mock_report._get_report_values.return_value = {
            'datas': [],
            'group_option': [],
            'from_date': '2025-01-01',
            'to_date': '2025-12-31',
            'filter': 'customer_wise',
            'state': 'draft',
            'group_by': 'state'
        }

        with patch.object(self.wizard.env, '__getitem__', return_value=mock_report):
            result = self.wizard.action_xlsx_print()

            self.assertEqual(result['type'], 'ir.actions.report')
            self.assertEqual(result['report_type'], 'xlsx')
            self.assertIn('Field Service Request Report', result['data']['report_name'])

            options = json.loads(result['data']['options'])
            self.assertEqual(options['context']['active_id'], self.wizard.id)
            self.assertEqual(options['start_date'], str(self.wizard.from_date))
            self.assertEqual(options['end_date'], str(self.wizard.to_date))
            self.assertTrue('datas' in options)
            self.assertTrue('group_option' in options)

    def test_get_xlsx_report(self):
        """
        Test `get_xlsx_report` generates XLSX data without errors.

        Steps:
            1. Prepare sample JSON input similar to the report payload.
            2. Mock a response object with `stream` as `io.BytesIO()`.
            3. Call `get_xlsx_report` with mock data and response.
            4. Verify that data was written to the response stream.
        """
        mock_data = json.dumps({
            'datas': [
                {
                    'name': 'FS00005',
                    'partner_name': 'Deco Addict',
                    'category_name': 'installation',
                    'priority': 'a',
                    'skill_category_id': 9,
                    'company_id': 1,
                    'create_date': '2025-11-03 09:51:42',
                    'date_deadline': '2025-11-27 09:30:00',
                    'sale_order_name': None,
                    'state': 'in_progress'
                }
            ],
            'group_option': [['draft', 'Draft'], ['in_progress', 'In Progress']],
            'from_date': '2025-01-01',
            'to_date': '2025-12-31',
            'filter': 'customer_wise',
            'state': 'draft',
            'group_by': 'state',
            'start_date': '2025-01-01',
            'end_date': '2025-12-31'
        })
        mock_response = MagicMock()
        mock_response.stream = io.BytesIO()
        self.wizard.get_xlsx_report(mock_data, mock_response)
        mock_response.stream.seek(0)
        content = mock_response.stream.read()
        self.assertTrue(len(content) > 0)
