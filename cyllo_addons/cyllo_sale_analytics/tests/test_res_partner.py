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
from odoo.tests import TransactionCase, tagged
from datetime import datetime, timedelta
import pandas as pd
from unittest.mock import patch, MagicMock
import numpy as np
import zipfile
import io
import json
import zipfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestResPartner(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner_model = self.env['res.partner']
        self.sale_model = self.env['sale.order']

        self.product = self.env['product.product'].create({
            'name': 'Test Item',
            'list_price': 100,
        })

        self.partner1 = self.partner_model.create({'name': 'Customer A'})
        self.partner2 = self.partner_model.create({'name': 'Customer B'})

        base_date = datetime.now()
        for i in range(3):
            order = self.sale_model.create({
                'partner_id': self.partner1.id,
                'date_order': (base_date - timedelta(days=i)),
            })
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100,
            })
            order.action_confirm()
            order.write({'date_order': base_date - timedelta(days=i)})

        order_outside = self.sale_model.create({
            'partner_id': self.partner1.id,
            'date_order': base_date - timedelta(days=90),
        })
        self.env['sale.order.line'].create({
            'order_id': order_outside.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'price_unit': 100,
        })
        order_outside.action_confirm()
        order_outside.write({'date_order': base_date - timedelta(days=90)})

    def test_execute_query(self):
        test_partner = self.partner_model.create({'name': 'Query Test Partner'})

        for _ in range(2):
            order = self.sale_model.create({
                'partner_id': test_partner.id,
                'date_order': datetime.now() - timedelta(days=2)
            })
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100,
            })
            order.action_confirm()
            order.write({'date_order': datetime.now() - timedelta(days=2)})

        start_date = (datetime.now() - timedelta(days=5)).date()
        end_date = datetime.now().date()

        self.env.flush_all()

        result = test_partner._execute_query((start_date, end_date), 1)
        freq_key = 'frequency_1' if 'frequency_1' in result[0] else 'f0_1'
        mon_key = 'monetary_1' if 'monetary_1' in result[0] else 'f1_1'
        matching_row = max(result, key=lambda r: r[freq_key])

        self.assertGreater(matching_row[freq_key], 0)
        self.assertTrue(matching_row[freq_key] >= 2)
        self.assertIn(mon_key, matching_row)
        self.assertIsInstance(matching_row[mon_key], float)

    def test_predict_churn(self):
        dates = [[datetime.now().date(), datetime.now().date()]]
        date_range = dates

        empty_df = pd.DataFrame()
        result_empty = self.partner_model.predict_churn(
            empty_df, dates=dates, date_range=date_range
        )
        self.assertIsInstance(result_empty, dict)
        self.assertFalse(result_empty.get("predict"))

        small_df = pd.DataFrame({
            "frequency_1": [5, 5, 5],
            "monetary_1": [500, 500, 500],
            "frequency_2": [7, 7, 7],
            "monetary_2": [550, 550, 550],
        })
        result_small = self.partner_model.predict_churn(
            small_df, dates=dates, date_range=date_range
        )
        self.assertIsInstance(result_small, dict)
        self.assertTrue(result_small.get("predict"))

        valid_df1 = pd.DataFrame({
            "frequency_1": [5, 2, 3],
            "monetary_1": [500, 200, 300],
        })
        valid_df2 = pd.DataFrame({
            "frequency_2": [6, 1, 4],
            "monetary_2": [520, 150, 350],
        })
        valid_df3 = pd.DataFrame({
            "frequency_3": [4, 2, 5],
            "monetary_3": [450, 220, 600],
        })
        mock_scaler = MagicMock()
        mock_scaler.fit_transform.return_value = np.array([[0.1], [0.2], [0.3]])
        mock_clf = MagicMock()
        mock_clf.predict.return_value = np.array(["No", "Yes", "No"])
        mock_clf.predict_proba.return_value = np.array([[0.4, 0.6], [0.7, 0.3], [0.3, 0.7]])
        mock_customers = [
            {'customerid': 1, 'customername': 'C1', 'lastsaleorderdate': datetime.now()},
            {'customerid': 2, 'customername': 'C2', 'lastsaleorderdate': datetime.now()},
            {'customerid': 3, 'customername': 'C3', 'lastsaleorderdate': datetime.now()},
        ]

        with patch("odoo.addons.cyllo_sale_analytics.models.res_partner.train_test_split",
                   return_value=(valid_df1, valid_df2, ["Yes", "No", "No"], ["Yes"])), \
                patch("odoo.addons.cyllo_sale_analytics.models.res_partner.StandardScaler",
                      return_value=mock_scaler), \
                patch("odoo.addons.cyllo_sale_analytics.models.res_partner.RandomForestClassifier",
                      return_value=mock_clf), \
                patch.object(self.env.cr, "dictfetchall", return_value=mock_customers), \
                patch.object(self.env.cr, "execute", return_value=True), \
                patch("odoo.addons.cyllo_sale_analytics.models.res_partner.models.Model.search_count",
                      return_value=3), \
                patch("odoo.addons.cyllo_sale_analytics.models.res_partner.models.Model.search") as mock_search:
            mock_search.return_value.mapped.return_value = [500, 450, 600]

            result_valid = self.partner_model.predict_churn(
                valid_df1, valid_df2, valid_df3, dates=dates, date_range=date_range
            )

        self.assertTrue(result_valid.get("predict"))
        self.assertIn("cust_wise_details", result_valid)
        self.assertIn("chart_data", result_valid)
        self.assertIn("churn_perc", result_valid)

    def test_get_date_range(self):
        period = "Month"
        period_type = "current_date"
        duration = 2

        mock_query_result = [
            {'frequency_1': 3, 'monetary_1': 600},
            {'frequency_1': 1, 'monetary_1': 200}
        ]
        mock_predict_output = {
            'predict': True,
            'cust_wise_details': [
                {'id': 1, 'name': 'Customer A', 'Churn': 'No'},
                {'id': 2, 'name': 'Customer B', 'Churn': 'Yes'}
            ],
            'chart_data': [
                {'frequency_1': 3, 'monetary_1': 600},
                {'frequency_1': 1, 'monetary_1': 200}
            ],
            'start_date': '01/01/2025',
            'end_date': '31/01/2025',
            'date_range': [('01/01/2025', '31/01/2025'), ('01/12/2024', '31/12/2024')]
        }

        with patch(
                "odoo.addons.cyllo_sale_analytics.models.res_partner.ResPartner._execute_query",
                return_value=mock_query_result
        ), patch(
            "odoo.addons.cyllo_sale_analytics.models.res_partner.ResPartner.predict_churn",
            return_value=mock_predict_output
        ):
            result = self.partner_model.get_date_range(period, period_type, duration)

        self.assertIsInstance(result, dict)
        self.assertTrue(result["predict"])
        self.assertIsInstance(result["cust_wise_details"], list)
        self.assertIsInstance(result["chart_data"], list)
        self.assertGreater(len(result["date_range"]), 0)

    def test_get_date_range_financial_year(self):

        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_analytics.fiscal_year_last_month', '12'
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'cyllo_analytics.fiscal_year_last_day', '31'
        )

        mock_query_result = [
            {"frequency_1": 3, "monetary_1": 600},
            {"frequency_1": 1, "monetary_1": 200},
        ]
        mock_churn_output = {
            "predict": True,
            "cust_wise_details": [
                {"id": 1, "name": "Customer A", "Churn": "No"},
                {"id": 2, "name": "Customer B", "Churn": "Yes"}
            ],
            "chart_data": mock_query_result,
            "start_date": "01/04/2024",
            "end_date": "31/03/2025",
            "date_range": [("01/04/2024", "31/03/2025")]
        }
        with patch.object(self.partner_model.__class__, "_execute_query", return_value=mock_query_result), \
                patch.object(self.partner_model.__class__, "predict_churn", return_value=mock_churn_output):
            result = self.partner_model.get_date_range(
                "Year", "financial_year", 1
            )

        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("predict"))
        self.assertIn("cust_wise_details", result)
        self.assertGreater(len(result["date_range"]), 0)

    def test_get_xlsx_report(self):
        response = MagicMock()
        response.stream = io.BytesIO()

        sample_data = {
            'numberOfPeriods': 3,
            'period': 'Month',
            'churnData': {
                'predict': True,
                'date_range': [('01/01/2025', '31/01/2025')],
                'cust_wise_details': [
                    {
                        'custName': 'Customer A',
                        'last_purchase_date': '10/01/2025',
                        'total_sales': 3,
                        'total_amount': 1500,
                        'Churn': 'No',
                        'prob_yes': 30.5,
                        'prob_no': 69.5,
                    },
                ]
            }
        }

        self.partner_model.get_xlsx_report(json.dumps(sample_data), response)
        xlsx_bytes = response.stream.getvalue()
        self.assertGreater(len(xlsx_bytes), 0)
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(xlsx_bytes)))
        with zipfile.ZipFile(io.BytesIO(xlsx_bytes), 'r') as z:
            sheet_xml = z.read('xl/worksheets/sheet1.xml').decode('utf-8')
            shared_strings = z.read('xl/sharedStrings.xml').decode('utf-8')
        self.assertIn("CHURN PREDICTION REPORT", shared_strings)
        self.assertIn("Customer A", shared_strings)
        self.assertIn("<mergeCell ref=\"A2:H3\"/>", sheet_xml)
