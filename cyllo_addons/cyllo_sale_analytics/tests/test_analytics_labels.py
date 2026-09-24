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
"""Tests for the translation/label helpers, the XLSX value sanitiser, the
forecast persistence round-trip and the algorithm-config weightage constraint.

These cover the pieces that back the multi-language dashboards (column headers,
derived/predefined field labels, churn labels, demand filters) plus the
supporting utilities — none of them require the ML stack (prophet/xgboost)."""
import json
import math

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestAnalyticsLabels(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SaleOrder = cls.env['sale.order']
        cls.Partner = cls.env['res.partner']
        cls.ForecastResult = cls.env['sale.forecast.result']

    # ------------------------------------------------------------------ #
    #  Column labels (sales-forecast dataset)                            #
    # ------------------------------------------------------------------ #
    def test_dataset_column_labels_shape(self):
        labels = self.SaleOrder._dataset_column_labels()
        self.assertIsInstance(labels, dict)
        # A representative sample of computed columns must be present.
        for key in ('Order Date', 'Sale Order Amount', 'No of Holidays',
                    'Sale Order IDs', 'Index', 'Order Month', 'sales_lag_1'):
            self.assertIn(key, labels)
            self.assertTrue(labels[key], "label for %s should not be empty" % key)

    def test_column_labels_for_includes_real_fields(self):
        """_column_labels_for merges computed labels with every real
        sale.order field's translated label (technical name -> string)."""
        labels = self.SaleOrder._column_labels_for()
        # Computed column still present ...
        self.assertIn('Order Date', labels)
        # ... and real field technical names are mapped to their label.
        self.assertIn('date_order', labels)
        self.assertIn('amount_total', labels)
        self.assertTrue(labels['date_order'])

    # ------------------------------------------------------------------ #
    #  Wizard field label providers                                      #
    # ------------------------------------------------------------------ #
    def test_virtual_forecast_fields(self):
        fields = self.SaleOrder.get_virtual_forecast_fields()
        self.assertEqual(len(fields), 5)
        names = {f['name'] for f in fields}
        self.assertEqual(names, {
            'virtual_customer_country', 'virtual_product_type',
            'virtual_month', 'virtual_quarter', 'virtual_week',
        })
        for f in fields:
            self.assertTrue(f['field_description'])

    def test_predefined_field_labels(self):
        labels = self.SaleOrder.get_predefined_field_labels()
        self.assertEqual(len(labels), 11)
        for key in ('customer_info', 'sale_order_amount', 'order_date',
                    'seasonality', 'active_customer', 'holidays'):
            self.assertIn(key, labels)
            self.assertTrue(labels[key])

    def test_demand_labels(self):
        labels = self.SaleOrder.get_demand_labels()
        self.assertIn('filters', labels)
        self.assertTrue(labels['filters'])

    # ------------------------------------------------------------------ #
    #  Churn labels                                                      #
    # ------------------------------------------------------------------ #
    def test_churn_labels(self):
        labels = self.Partner.get_churn_labels()
        # Raw Churn values map to display labels ...
        for key in ('Yes', 'No', 'Waiting', 'at_risk', 'loyal', 'waiting'):
            self.assertIn(key, labels)
            self.assertTrue(labels[key])
        # ... plus chart / period / filter labels.
        for key in ('total_sale_orders', 'total_sale_amount',
                    'quarter', 'period', 'filters'):
            self.assertIn(key, labels)
            self.assertTrue(labels[key])

    # ------------------------------------------------------------------ #
    #  XLSX cell sanitiser                                               #
    # ------------------------------------------------------------------ #
    def test_xlsx_cell_value_sanitises(self):
        clean = self.ForecastResult._xlsx_cell_value
        self.assertEqual(clean(None), '')
        self.assertEqual(clean(float('nan')), '')
        self.assertEqual(clean(float('inf')), '')
        self.assertEqual(clean(float('-inf')), '')
        self.assertEqual(clean(3.5), 3.5)
        self.assertEqual(clean(7), 7)
        self.assertEqual(clean('x'), 'x')
        self.assertEqual(clean(True), True)
        self.assertEqual(clean(['a', 1]), json.dumps(['a', 1]))
        self.assertEqual(clean({'k': 1}), json.dumps({'k': 1}))
        # Never returns a NaN/Inf float
        for v in (float('nan'), float('inf')):
            out = clean(v)
            self.assertFalse(isinstance(out, float) and (math.isnan(out) or math.isinf(out)))

    # ------------------------------------------------------------------ #
    #  Forecast persistence round-trip + column_labels injection         #
    # ------------------------------------------------------------------ #
    def test_save_and_get_last_forecast(self):
        params = {'start_date': '2024-01-01', 'end_date': '2024-12-31',
                  'aggregate': 'M', 'mode': 'algorithm', 'extra_fields': []}
        results = {'dataset': [{'Order Date': '2024 Jan', 'Sale Order Amount': 100}],
                   'sale_orders_table': [], 'orderlines_table': []}
        self.ForecastResult._save_forecast(params, results)

        saved = self.SaleOrder.get_last_forecast()
        self.assertTrue(saved)
        self.assertIn('results', saved)
        data = json.loads(saved['results'])
        self.assertEqual(data['dataset'][0]['Sale Order Amount'], 100)
        # get_last_forecast injects fresh translated column labels.
        self.assertIn('column_labels', data)
        self.assertIn('Order Date', data['column_labels'])

    def test_build_multisheet_xlsx_returns_valid_file(self):
        rec = self.ForecastResult.create({
            'results': json.dumps({
                'dataset': [
                    {'Order Date': '2024 Jan', 'Sale Order Amount': 100, 'date_order': '2024-01-01'},
                    {'Order Date': '2024 Feb', 'Sale Order Amount': None, 'date_order': '2024-02-01'},
                ],
                'sale_orders_table': [],
                'orderlines_table': [],
            }),
        })
        content = rec.build_multisheet_xlsx()
        self.assertIsInstance(content, bytes)
        self.assertTrue(content, "xlsx content should not be empty")
        # XLSX is a zip container -> starts with the PK signature.
        self.assertEqual(content[:2], b'PK')

    # ------------------------------------------------------------------ #
    #  Keyword parsing                                                   #
    # ------------------------------------------------------------------ #
    def test_parse_keywords(self):
        parse = self.SaleOrder._parse_keywords
        self.assertEqual(parse(''), [])
        self.assertEqual(parse(None), [])
        self.assertEqual(parse('fuel, crisis'), ['fuel', 'crisis'])
        # trims blanks and de-duplicates case-insensitively (first kept)
        self.assertEqual(parse('  fuel ,, Fuel , crisis '), ['fuel', 'crisis'])
        self.assertEqual(parse(['a', 'A', 'b']), ['a', 'b'])

    # ------------------------------------------------------------------ #
    #  Algorithm config weightage constraint                             #
    # ------------------------------------------------------------------ #
    def test_algo_config_weightage_valid(self):
        cfg = self.env['algo.config'].create({
            'line_ids': [
                (0, 0, {'field_type': 'count', 'weightage': 40}),
                (0, 0, {'field_type': 'total', 'weightage': 40}),
                (0, 0, {'field_type': 'recency', 'weightage': 20}),
            ],
        })
        self.assertEqual(sum(cfg.line_ids.mapped('weightage')), 100)

    def test_algo_config_weightage_invalid(self):
        with self.assertRaises(ValidationError):
            self.env['algo.config'].create({
                'line_ids': [
                    (0, 0, {'field_type': 'count', 'weightage': 40}),
                    (0, 0, {'field_type': 'total', 'weightage': 40}),
                ],
            })
