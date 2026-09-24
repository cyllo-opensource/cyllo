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
import zipfile
import io
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestXlsxReportController(HttpCase):
    """Test suite for XLSX report download endpoint."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'password': 'test_user',
            'email': 'test_user@test.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })

        cls.sample_data = {
            'numberOfPeriods': 1,
            'period': 'Month',
            'churnData': {
                'predict': True,
                'date_range': [('01/01/2025', '31/01/2025')],
                'cust_wise_details': [
                    {
                        'custName': 'Customer A',
                        'last_purchase_date': '15/01/2025',
                        'total_sales': 4,
                        'total_amount': 2400,
                        'Churn': 'No',
                        'prob_yes': 40.3,
                        'prob_no': 59.7,
                    }
                ]
            }
        }

        cls.url = "/smartd_xlsx_reports"
        cls.model = "res.partner"
        cls.report_name = "Churn_Report"

    def test_get_report_xlsx(self):
        """Test XLSX report route for authenticated use, unauthorized access,
        and invalid payload response handling."""

        response = self.url_open(
            f"{self.url}?model={self.model}&data={json.dumps(self.sample_data)}&output_format=xlsx&report_name={self.report_name}",
            allow_redirects=False
        )
        self.assertIn(response.status_code, (301, 303, 401, 403, 405))
        self.authenticate("test_user", "test_user")
        payload = {
            "model": self.model,
            "data": json.dumps(self.sample_data),
            "output_format": "xlsx",
            "report_name": self.report_name,
        }
        response = self.url_open(
            f"{self.url}?model={self.model}&data={json.dumps(self.sample_data)}&output_format=xlsx&report_name={self.report_name}",
            data=json.dumps(payload),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/vnd.ms-excel", response.headers.get("Content-Type"))
        content = response.content
        self.assertGreater(len(content), 0)
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(content)))

        with zipfile.ZipFile(io.BytesIO(content), "r") as archive:
            sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode()
            shared_strings = archive.read("xl/sharedStrings.xml").decode()

        self.assertIn("CHURN PREDICTION REPORT", shared_strings)
        self.assertIn("Customer A", shared_strings)
        self.assertIn("Probability of Churn", shared_strings)
        self.assertIn("Probability of Not Churn", shared_strings)
        self.assertIn("<mergeCell ref=\"A2:H3\"/>", sheet_xml)
        response_invalid = self.url_open(
            f"{self.url}?model={self.model}&data='invalid'&output_format=xlsx&report_name={self.report_name}",
            data="INVALID_JSON",
        )
        self.assertEqual(response_invalid.status_code, 200)
        self.assertIn(b"Odoo Server Error", response_invalid.content)
