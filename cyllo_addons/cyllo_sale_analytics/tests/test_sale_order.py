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
from unittest.mock import patch, MagicMock
import pandas as pd
import json
import io
import json
import zipfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestSaleOrder(TransactionCase):
    """Test suite covering all extended Sale Order forecasting features including:

    - Forecast configuration behavior based on available dataset.
    - Prophet forecast processing and data formatting.
    - Product-specific demand forecasting logic.
    - XLSX export report generation.
    """

    def setUp(self):
        """Initialize reusable test data including product, customer,
        dataframe for Prophet mocking, and general forecast input parameters."""
        super().setUp()
        self.model = self.env["sale.order"]
        self.partner = self.env['res.partner'].create({'name': 'Test Customer'})
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100,
        })
        self.df = pd.DataFrame({
            'ds': pd.to_datetime(['2025-01-01', '2025-01-02', '2025-01-03']),
            'y': [1000, 1500, 1200],
        })
        self.sales_dict = {
            '2025-01-01': 1000,
            '2025-01-02': 1500,
            '2025-01-03': 1200,
        }
        self.period = 5
        self.frequency = 'D'
        self.start_date = "2025-01-01"
        self.end_date = "2025-02-01"

    def _create_orders(self, count):
        """Helper method to create confirmed sale orders across distinct sequential dates."""
        base_date = datetime.now()
        for i in range(count):
            order_date = (base_date - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            order = self.env['sale.order'].create({
                'partner_id': self.partner.id,
            })
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100,
            })
            order.write({'state': 'sale', 'date_order': order_date})


    def test_product_demand_forecast(self):
        """Check demand forecasting logic including actual data, forecast, and structure validation."""
        self._create_orders(12)
        mock_future_df = pd.DataFrame({
            'ds': pd.to_datetime(['2025-02-01', '2025-02-02']),
            'yhat': [60, 62],
        })
        with patch("odoo.addons.cyllo_sale_analytics.models.sale_order.Prophet") as mock_prophet:
            mock_instance = MagicMock()
            mock_prophet.return_value = mock_instance
            mock_instance.make_future_dataframe.return_value = pd.DataFrame({'ds': mock_future_df['ds']})
            mock_instance.predict.return_value = mock_future_df
            today = datetime.now().date()
            date_params = {
                'period': 2,
                'frequency': 'D',
                'actStartDate': today - timedelta(days=20),
                'actEndDate': today + timedelta(days=1)
            }
            result = self.model.product_demand_forecast(date_params, prod=[self.product.id, self.product.name])
        self.assertIsInstance(result, dict)
        expected_keys = {
            'product_list', 'current_product', 'table_act_data',
            'table_fore_data', 'start_date', 'end_date', 'no_data', 'chart_data'
        }
        self.assertTrue(expected_keys.issubset(result))
        self.assertEqual(result['current_product'], [self.product.id, self.product.name])
        self.assertEqual(len(result['table_act_data']), 12)
        self.assertTrue(result['no_data'])
        self.assertGreater(len(result['table_fore_data']), 0)
        self.assertGreater(len(result['chart_data']), len(result['table_act_data']))
        self.assertEqual(len(result['table_fore_data']), 2)

    def test_get_xlsx_report(self):
        """Validate XLSX report generation and verify key strings exist."""
        response = MagicMock()
        response.stream = io.BytesIO()
        sample_data = {
            'frequency': 'D',
            'start_date': '2025-01-01',
            'end_date': '2025-01-10',
            'period': 5,
            'product': 'Test Product',
            'actual': [{'date': '2025/01/01', 'qty': 10, 'sub_total': 500, 'avg_price': 50}],
            'predict': [{'date': '2025/01/11', 'qty': 18, 'subtotal': 900, 'avg_price': 50}],
        }
        self.model.get_xlsx_report(json.dumps(sample_data), response)
        xlsx_output = response.stream.getvalue()
        self.assertGreater(len(xlsx_output), 0)
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(xlsx_output)))
        with zipfile.ZipFile(io.BytesIO(xlsx_output), 'r') as z:
            sheet_xml = z.read('xl/worksheets/sheet1.xml').decode('utf-8')
            shared_strings = z.read('xl/sharedStrings.xml').decode('utf-8')
        self.assertIn("DEMAND PREDICTION REPORT", shared_strings)
        self.assertIn("Test Product", shared_strings)
        self.assertIn("ACTUAL SALES", shared_strings)
        self.assertIn("PREDICTED SALES", shared_strings)
        self.assertIn("<mergeCell ref=\"B2:J3\"/>", sheet_xml)

    def test_trend_seasonality_score_and_persistence(self):
        """Verify that generate_training_dataset computes min-max normalized score and persists it."""
        # Create some confirmed orders with different amount totals
        # Order 1: amount_total = 100 (min)
        order1 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        self.env['sale.order.line'].create({
            'order_id': order1.id,
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'price_unit': 100,
        })
        order1.write({'state': 'sale', 'date_order': datetime.now()})

        # Order 2: amount_total = 1000 (max)
        order2 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        self.env['sale.order.line'].create({
            'order_id': order2.id,
            'product_id': self.product.id,
            'product_uom_qty': 10,
            'price_unit': 100,
        })
        order2.write({'state': 'sale', 'date_order': datetime.now()})

        # Order 3: amount_total = 550 (middle -> score should be exactly 5.5)
        order3 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        self.env['sale.order.line'].create({
            'order_id': order3.id,
            'product_id': self.product.id,
            'product_uom_qty': 5.5,
            'price_unit': 100,
        })
        future_date = datetime(2099, 1, 1)
        order1.write({'state': 'sale', 'date_order': future_date})
        order2.write({'state': 'sale', 'date_order': future_date})
        order3.write({'state': 'sale', 'date_order': future_date})

        # Flush ORM cache to SQL database so raw queries can see the new orders
        self.env.flush_all()

        # Check Trend Seasonality Score and persistence
        params = {
            'start_date': '2099-01-01',
            'end_date': '2099-01-02',
            'aggregate': 'D',
            'mode': 'algorithm',
            'custom_fields': ['sale_order_amount', 'order_date'],
            'extra_fields': []
        }


        # Generate training dataset
        result = self.model.generate_training_dataset(params)

        # Assert Trend Seasonality Score is present in base rows
        self.assertIn('dataset', result)
        dataset = result['dataset']
        self.assertTrue(len(dataset) >= 3)

        # Let's verify scores stored on the records in DB
        self.assertEqual(order1.trend_seasonality_score, 1.0)
        self.assertEqual(order2.trend_seasonality_score, 10.0)
        self.assertEqual(order3.trend_seasonality_score, 5.5)

        # Assert result columns list contains 'Trend Seasonality Score'
        row1 = next(row for row in dataset if row.get('Sale Order Record ID') == order1.id)
        self.assertEqual(row1.get('Trend Seasonality Score'), 1.0)

        # Verify that get_last_forecast retrieves the saved forecast
        saved = self.model.get_last_forecast()
        self.assertTrue(saved)
        self.assertIn('params', saved)
        self.assertIn('results', saved)

        # Verify JSON content matches
        import json
        saved_params = json.loads(saved['params'])
        saved_results = json.loads(saved['results'])
        self.assertEqual(saved_params.get('aggregate'), 'D')
        self.assertTrue(len(saved_results.get('dataset', [])) >= 3)




