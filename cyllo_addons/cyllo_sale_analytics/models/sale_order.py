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
import datetime
import io
import json
import logging
import warnings

import numpy as np
import pandas as pd
import xlsxwriter
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from prophet import Prophet

warnings.filterwarnings('ignore')

_logger = logging.getLogger(__name__)

# Exponential-moving-average smoothing factors used by the training dataset
# and the Prophet forecast extension: alpha = 2 / (span + 1).
EMA3_ALPHA = 2 / (3 + 1)  # 0.5
EMA6_ALPHA = 2 / (6 + 1)  # ≈ 0.2857


class SaleOrderInheritClass(models.Model):
    """ This class inherits from 'sale.order' model and extends its functionality."""

    _inherit = 'sale.order'

    trend_seasonality_score = fields.Float(string="Trend Seasonality Score")


    @api.model
    def product_demand_forecast(self, date, prod):

        """  Generate a forecast for product demand based on historical sales data."""
        actual_start_date = date.get('actStartDate') if date.get(
            'actStartDate') else (datetime.date.today() -
                                  datetime.timedelta(days=30))
        actual_end_date = date.get('actEndDate') if date.get(
            'actEndDate') else datetime.date.today()
        periods = date.get('period') if date.get('period') else 10
        frequency = date.get('frequency') if date.get('frequency') else 'D'
        search_params = [('order_id.state', '=', 'sale'),
                         ('order_id.date_order', '>=', actual_start_date),
                         ('order_id.date_order', '<=', actual_end_date)]
        sale_order_lines = self.env['sale.order.line'].search(search_params)
        prod_list = sorted([{rec.id: [rec.id, rec.display_name]} for rec in
                            sale_order_lines.mapped('product_id')],
                           key=lambda x: list(x.keys())[0])
        if prod_list:
            if not prod:
                prod = list(prod_list[0].values())[0]
        else:
            return False
        data = [{'name': order_line.product_id.display_name,
                 'date': order_line.order_id.date_order.date(),
                 'qty': order_line.product_uom_qty,
                 'unit_price': order_line.price_unit,
                 'sub_total': order_line.price_subtotal
                 } for order_line in sale_order_lines.filtered(
            lambda rec: rec.product_id.id == prod[0])]

        df = pd.DataFrame(data)
        df.sort_values(by='date', ascending=True)
        daily = df.groupby('date').agg(
            {'qty': 'sum', 'sub_total': 'sum'}).reset_index()
        daily['avg_price'] = (daily['sub_total'] / daily['qty']).where(
            daily['qty'] != 0, 0).round(2)
        daily['date'] = daily['date'].astype(str)
        daily[['sub_total', 'avg_price']] = daily[
            ['sub_total', 'avg_price']].round(2)
        # data for prophet model
        sales_data = df.groupby('date').agg(
            {'qty': 'sum', 'sub_total': 'sum'}).reset_index()
        sales_data = sales_data.rename(
            columns={'qty': 'total_qty', 'unit_price': 'avg_unit_price'})
        sales_data['date'] = pd.to_datetime(sales_data['date'])
        actual_data = sales_data
        actual_data = actual_data.drop(columns=['sub_total'])
        actual_data = actual_data.rename(
            columns={'date': 'ds', 'total_qty': 'y'})
        daily['date'] = pd.to_datetime(daily['date'])
        if frequency == 'D':
            daily['date'] = pd.to_datetime(daily['date']).dt.strftime(
                '%Y/%m/%d')
            # data for prophet model
            prop_input = actual_data
        else:  # Handles M and Y cases here
            daily = daily.resample(frequency, on='date').agg(
                {'qty': 'sum', 'sub_total': 'sum'})
            daily['avg_price'] = (daily['sub_total'] / daily['qty']).where(
                daily['qty'] != 0, 0).round(2)
            date_format = "%Y %b" if frequency == "M" else "%Y"
            daily = daily.reset_index()
            daily['date'] = daily['date'].dt.strftime(date_format)
            prop_input = actual_data.groupby(
                pd.Grouper(key='ds', freq=frequency)).sum().reset_index()
        demand_act_data = daily.to_dict(orient='records')
        if len(prop_input) >= 10:
            try:
                prod_price = df['unit_price'].mean()
                model = Prophet()
                model.fit(prop_input)
                future_pred = model.make_future_dataframe(
                    periods=int(periods),
                    freq=frequency
                )
                future_pred = future_pred.iloc[len(prop_input):]
                forecast = model.predict(future_pred)
                forecast_dict_list = []
                for key, value in zip(forecast['ds'], forecast['yhat']):
                    rounded_value = round(value, 0)
                    forecast_dict = {
                        'date': str(key.date()),
                        'qty': rounded_value,
                        'subtotal': round(rounded_value * prod_price, 2),
                        'avg_price': round(prod_price, 2),
                    }
                    forecast_dict_list.append(forecast_dict)
                no_data = True
            except Exception:
                return False
            forecast_dict_list = pd.DataFrame(forecast_dict_list)
            forecast_dict_list['date'] = pd.to_datetime(
                forecast_dict_list['date'])
            if frequency == 'D':
                forecast_dict_list['date'] = pd.to_datetime(
                    forecast_dict_list['date']).dt.strftime('%Y/%m/%d')
            else:
                date_format = "%Y %b" if frequency == "M" else "%Y"
                forecast_dict_list['date'] = forecast_dict_list[
                    'date'].dt.strftime(date_format)
            demand_fore_data = forecast_dict_list.to_dict(orient='records')
            chart_data = demand_act_data + demand_fore_data
        else:
            no_data = False
            demand_fore_data = []
            chart_data = []
        vals = {
            'product_list': prod_list,
            'current_product': prod,
            'table_act_data': demand_act_data,
            'table_fore_data': demand_fore_data,
            'start_date': actual_start_date,
            'end_date': actual_end_date,
            'no_data': no_data,
            'chart_data': chart_data
        }
        return vals

    def get_xlsx_report(self, data, response):
        """ Generate an Excel report based on demand prediction data."""

        data = json.loads(data)
        if data['frequency'] == 'D':
            frequency = 'Days'
        elif data['frequency'] == 'M':
            frequency = 'Months'
        else:
            frequency = 'Years'
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()

        main_head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '15px'})
        sub_head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '13px'})
        sub_head1 = workbook.add_format(
            {'align': 'left', 'bold': True, 'font_size': '13px'})
        header = workbook.add_format({'bold': True, 'align': 'center'})
        table_data = workbook.add_format(
            {'align': 'center', 'font_size': '12px'})
        sheet.merge_range('B2:J3', 'DEMAND PREDICTION REPORT', main_head)
        sheet.merge_range('B5:J6',
                          f"Actual Sales is from {data['start_date']} to {data['end_date']} & Predicted Demand"
                          f" for {data['period']} {frequency}", sub_head)
        sheet.merge_range('B8:F9', f"Product : {data['product']}", sub_head1)
        sheet.merge_range('B11:E12', 'ACTUAL SALES', sub_head)
        sheet.merge_range('G11:J12', 'PREDICTED SALES', sub_head)
        row = 13
        column = 1
        sheet.set_column(1, 4, 20)
        sheet.set_column(6, 9, 20)
        sheet.set_row(13, height=30)
        sheet.write(row, column, 'Periods', header)
        column += 1
        sheet.write(row, column, 'Quantity Sold', header)
        column += 1
        sheet.write(row, column, 'Average Sales Price', header)
        column += 1
        sheet.write(row, column, 'Revenue', header)
        column += 2
        sheet.write(row, column, 'Periods', header)
        column += 1
        sheet.write(row, column, 'Quantity Sold', header)
        column += 1
        sheet.write(row, column, 'Average Sales Price', header)
        column += 1
        sheet.write(row, column, 'Revenue', header)
        row = 14
        new_row1 = row + 1
        for each in data['actual']:
            sheet.write('B%s' % new_row1, each['date'], table_data)
            sheet.write('C%s' % new_row1, each['qty'], table_data)
            sheet.write('D%s' % new_row1, each['sub_total'], table_data)
            sheet.write('E%s' % new_row1, each['avg_price'], table_data)
            new_row1 += 1
        row_num = 14
        new_row2 = row_num + 1
        for eachitem in data['predict']:
            sheet.write('G%s' % new_row2, eachitem['date'], table_data)
            sheet.write('H%s' % new_row2, eachitem['qty'], table_data)
            sheet.write('I%s' % new_row2, eachitem['subtotal'], table_data)
            sheet.write('J%s' % new_row2, eachitem['avg_price'], table_data)
            new_row2 += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
# Sales Forecasting
    @api.model
    def _dataset_column_labels(self):
        """Translatable display labels for the generated-dataset columns.

        The dataset dict keys stay English (they are also used as data/lookup
        keys); this map is what the UI and the XLSX export show, translated to
        the user's language."""
        return {
            'Index': _('Index'),
            'Order Date': _('Order Date'),
            'Trend Seasonality Score': _('Trend Seasonality Score'),
            'Sale Order Amount': _('Sale Order Amount'),
            'Seasonality': _('Seasonality'),
            'No of Holidays': _('No of Holidays'),
            'No of Opportunities': _('No of Opportunities'),
            'No of Website Orders': _('No of Website Orders'),
            'No of Direct Orders': _('No of Direct Orders'),
            'No of Active Customers': _('No of Active Customers'),
            'No of Campaigns': _('No of Campaigns'),
            'Sale Order IDs': _('Sale Order IDs'),
            'Customer Country': _('Customer Country'),
            'Order Month': _('Order Month'),
            'Order Quarter': _('Order Quarter'),
            'Order Week': _('Order Week'),
            'Product Type': _('Product Type'),
            'Product Name': _('Product Name'),
            'Product Category': _('Product Category'),
            'On Hand Qty': _('On Hand Qty'),
            'Purchased Qty': _('Purchased Qty'),
            'Unit Price': _('Unit Price'),
            'Discount %': _('Discount %'),
            'Period': _('Period'),
            'Sale Order Record ID': _('Sale Order Record ID'),
            'Order Reference': _('Order Reference'),
            'Customer Name': _('Customer Name'),
            'Customer ID': _('Customer ID'),
            'Orderlines IDs': _('Orderlines IDs'),
            'Orderline ID': _('Orderline ID'),
            'Active Customer': _('Active Customer'),
            'Website Visitors vs Orders': _('Website Visitors vs Orders'),
            'Holiday Sequence': _('Holiday Sequence'),
            'Campaign': _('Campaign'),
            'Opportunity ID': _('Opportunity ID'),
            'Opportunity Name': _('Opportunity Name'),
            'Leads & Opportunity': _('Leads & Opportunity'),
            'Avg Discount': _('Avg Discount'),
            'Avg Unit Price': _('Avg Unit Price'),
            'Total On Hand Qty': _('Total On Hand Qty'),
            'Day of Week': _('Day of Week'),
            'sales_lag_1': _('Sales Lag 1'),
            'sales_lag_2': _('Sales Lag 2'),
            'sales_lag_3': _('Sales Lag 3'),
            'rolling_mean_3': _('Rolling Mean (3)'),
            'EMA3': _('EMA (3)'),
            'EMA6': _('EMA (6)'),
        }

    @api.model
    def get_virtual_forecast_fields(self):
        """Derived (virtual) fields offered in the wizard, with translated
        labels. Served from Python so the labels use the (reliable) server-side
        translation path instead of the JS web-translation bundle."""
        return [
            {'name': 'virtual_customer_country', 'field_description': _('Customer Country (Derived)')},
            {'name': 'virtual_product_type', 'field_description': _('Product Type (Derived)')},
            {'name': 'virtual_month', 'field_description': _('Order Month')},
            {'name': 'virtual_quarter', 'field_description': _('Order Quarter')},
            {'name': 'virtual_week', 'field_description': _('Order Week')},
        ]

    @api.model
    def get_predefined_field_labels(self):
        """Translated labels for the wizard's predefined-field toggles. Served
        from Python (reliable translation path) so the labels don't depend on
        the JS web-translation bundle."""
        return {
            'customer_info': _('Customer Name & ID'),
            'sale_order_amount': _('Sale Order Amount'),
            'order_date': _('Order Date'),
            'leads_opportunities': _('Leads & Opportunity'),
            'opportunity_id': _('Opportunity Name & ID'),
            'campaign_id': _('Campaign'),
            'holidays': _('Holidays Calendar'),
            'website_visitors': _('Website Visitors vs Orders'),
            'product_features': _('Product Features'),
            'seasonality': _('Seasonality'),
            'active_customer': _('Active Customer Count'),
        }

    @api.model
    def get_demand_labels(self):
        """Translated labels for the Demand Prediction dashboard."""
        return {
            'filters': _('Demand filters'),
        }

    @api.model
    def _column_labels_for(self, extra_fields=None):
        """Static (computed-column) labels merged with the translated labels of
        EVERY Sale Order field. Real-field columns use their technical name as
        the key, so mapping every field's translated ``string`` guarantees a
        proper header (in the user's language) whether or not the field was in
        the explicit selection. Used by both the on-screen table and the XLSX."""
        labels = self._dataset_column_labels()
        try:
            info = self.env['sale.order'].fields_get(attributes=['string'])
            for fname, meta in info.items():
                # computed-column labels (human keys) win over technical names;
                # no key collision since field names are technical.
                if meta.get('string'):
                    labels.setdefault(fname, meta['string'])
        except Exception:
            pass
        return labels

    @api.model
    def generate_training_dataset(self, params):
        try:
            from datetime import datetime, timedelta

            orig_params = dict(params)
            start_date = params.get('start_date')
            end_date = params.get('end_date')
            custom_fields = params.get('custom_fields', [])
            extra_fields = params.get('extra_fields', [])
            aggregate = params.get('aggregate', 'D')
            mode = params.get('mode', 'algorithm')
            domain = [('state', 'in', ['sale', 'done'])]
            if start_date:
                domain.append(('date_order', '>=', start_date))
            if end_date:
                domain.append(('date_order', '<=', end_date))

            allowed_fields = ['id', 'name', 'date_order', 'amount_total'] + extra_fields
            for custom in custom_fields:
                if custom in ('customer_info', 'active_customer'):
                    allowed_fields.append('partner_id')
                if custom in ('leads_opportunities', 'opportunity_id'):
                    allowed_fields.append('opportunity_id')
                if custom == 'website_visitors':
                    allowed_fields.append('website_id')
                if custom == 'campaign_id':
                    allowed_fields.append('campaign_id')

            allowed_fields = list(set(allowed_fields))
            if 'virtual_customer_country' in extra_fields and 'partner_id' not in allowed_fields:
                allowed_fields.append('partner_id')
            
            existing_fields_info = self.env['sale.order'].fields_get()
            VIRTUAL_FIELDS = ['virtual_customer_country', 'virtual_product_type', 'virtual_month', 'virtual_quarter', 'virtual_week']
            query_fields = [field_name for field_name in allowed_fields if field_name in existing_fields_info and field_name not in VIRTUAL_FIELDS]

            stored_fields = [field_name for field_name in query_fields if existing_fields_info[field_name].get('store', True) and existing_fields_info[field_name].get('type') not in ['many2many', 'one2many', 'binary']]
            compute_fields = [field_name for field_name in query_fields if field_name not in stored_fields]

            # ── RAW SQL FETCH FOR SPEED ──
            selects = ["id"] + [field_name for field_name in stored_fields if field_name != 'id']
            sql = f"SELECT {', '.join(selects)} FROM sale_order WHERE state IN ('sale', 'done') AND company_id IN %s"
            params = [tuple(self.env.companies.ids)]
            if start_date:
                sql += " AND date_order >= %s"
                params.append(f"{start_date} 00:00:00")
            if end_date:
                sql += " AND date_order <= %s"
                params.append(f"{end_date} 23:59:59")
            sql += " ORDER BY date_order ASC LIMIT 100000"

            self.env.cr.execute(sql, params)
            orders = self.env.cr.dictfetchall()

            # ── CALCULATE TREND SEASONALITY SCORE ──
            amounts = [float(order.get('amount_total') or 0.0) for order in orders]
            min_amount = min(amounts) if amounts else 0.0
            max_amount = max(amounts) if amounts else 0.0

            for order in orders:
                order_id = order['id']
                amount = float(order.get('amount_total') or 0.0)
                if max_amount > min_amount:
                    score = 1.0 + ((amount - min_amount) * 9.0) / (max_amount - min_amount)
                else:
                    score = 1.0
                score = round(max(1.0, min(10.0, score)), 2)
                order['trend_seasonality_score'] = score
                self.env.cr.execute(
                    "UPDATE sale_order SET trend_seasonality_score = %s WHERE id = %s",
                    (score, order_id)
                )
            if orders:
                self.env['sale.order'].invalidate_model(['trend_seasonality_score'])


            # ── BULK RESOLVE MANY2ONE FIELDS ──
            m2o_fields = [field_name for field_name in stored_fields if existing_fields_info[field_name].get('type') == 'many2one']
            for field_name in m2o_fields:
                model_name = existing_fields_info[field_name].get('relation')
                if not model_name: continue
                val_ids = list({order_rec[field_name] for order_rec in orders if order_rec.get(field_name)})
                if val_ids:
                    # Retrieve the physical names
                    names_map = {rel_record['id']: rel_record.get('display_name', '') for rel_record in self.env[model_name].search_read([('id', 'in', val_ids)], ['display_name'])}
                    for order_rec in orders:
                        if order_rec.get(field_name):
                            order_rec[field_name] = (order_rec[field_name], names_map.get(order_rec[field_name], ''))
                        else:
                            order_rec[field_name] = False

            # ── MERGE COMPUTED FIELDS VIA SEARCH_READ ──
            if compute_fields and orders:
                order_ids = [order_rec['id'] for order_rec in orders]
                chunk_size = 5000
                for i in range(0, len(order_ids), chunk_size):
                    chunk = order_ids[i:i + chunk_size]
                    comp_data = self.env['sale.order'].search_read([('id', 'in', chunk)], ['id'] + compute_fields)
                    compute_map = {compute_rec['id']: compute_rec for compute_rec in comp_data}
                    for order_rec in orders:
                        if order_rec['id'] in compute_map:
                            order_rec.update(compute_map[order_rec['id']])

            # ── Build holiday set from resource.calendar.leaves (global public leaves) ──
            # resource.calendar.leaves is a native model that stores Work Schedule
            # exceptions. When resource_id = False it means a company-wide (public) holiday.
            holiday_dates = set()
            if 'holidays' in custom_fields:
                public_leaves = self.env['resource.calendar.leaves'].search_read(
                    [('resource_id', '=', False)],
                    ['date_from', 'date_to', 'name']
                )
                for leave in public_leaves:
                    date_from_val = leave.get('date_from')
                    dt_val = leave.get('date_to')
                    if date_from_val and dt_val:
                        start_l = date_from_val if isinstance(date_from_val, datetime) else datetime.fromisoformat(str(date_from_val))
                        end_l = dt_val if isinstance(dt_val, datetime) else datetime.fromisoformat(str(dt_val))
                        current_date = start_l.date()
                        while current_date <= end_l.date():
                            holiday_dates.add(current_date)
                            current_date += timedelta(days=1)

            # ── Batch fetch order lines ──
            need_lines = 'product_features' in custom_fields
            lines_by_order = {}
            if need_lines:
                order_ids = [o['id'] for o in orders]
                chunk_size = 5000
                for i in range(0, len(order_ids), chunk_size):
                    chunk = order_ids[i:i + chunk_size]
                    if not chunk:
                        continue
                    lines = self.env['sale.order.line'].search_read(
                        [('order_id', 'in', chunk)],
                        ['order_id', 'product_id', 'product_uom_qty', 'discount', 'price_unit', 'product_template_id']
                    )
                    for order_line in lines:
                        oid_val = order_line.get('order_id')
                        oid = oid_val[0] if isinstance(oid_val, tuple) else oid_val
                        if not oid:
                            continue
                        lines_by_order.setdefault(oid, []).append(order_line)

            # ── Pre-fetch product category & on-hand qty in bulk ──
            product_info = {}
            if need_lines:
                all_product_ids = []
                for lines in lines_by_order.values():
                    for order_line in lines:
                        pid_raw = order_line.get('product_id')
                        pid = pid_raw[0] if isinstance(pid_raw, tuple) else pid_raw
                        if pid:
                            all_product_ids.append(pid)
                all_product_ids = list(set(all_product_ids))

                chunk_size = 5000
                for i in range(0, len(all_product_ids), chunk_size):
                    chunk = all_product_ids[i:i + chunk_size]
                    prods = self.env['product.product'].search_read(
                        [('id', 'in', chunk)],
                        ['id', 'name', 'categ_id', 'qty_available', 'type']
                    )
                    for product_rec in prods:
                        categ = product_rec.get('categ_id')
                        product_info[product_rec['id']] = {
                            'name': product_rec.get('name', 'N/A'),
                            'categ': categ[1] if isinstance(categ, tuple) else 'N/A',
                            'on_hand_qty': float(product_rec.get('qty_available') or 0.0),
                            'product_type': product_rec.get('type') or 'N/A'
                        }

            # ── Climate-zone seasonality (Koppen-inspired) by company country ──
            # Zones:
            #   'tropical'     – equatorial/wet-dry, no traditional 4 seasons
            #   'desert'       – arid/semi-arid (Arabian Peninsula, Sahara, etc.)
            #   'arctic'       – polar/subarctic (Greenland, northern Scandinavia, etc.)
            #   'mediterranean'– mild/wet winters, hot/dry summers
            #   'southern'     – Southern-hemisphere temperate (inverted 4 seasons)
            #   default        – Northern-hemisphere temperate 4 seasons

            TROPICAL_COUNTRIES = {
                'BD', 'BN', 'BO', 'BR', 'BT', 'CD', 'CF', 'CG', 'CI', 'CM',
                'CO', 'CR', 'CU', 'EC', 'ET', 'GH', 'GM', 'GN', 'GQ', 'GT',
                'GW', 'HN', 'ID', 'IN', 'KE', 'KH', 'LA', 'LK', 'MG', 'MM',
                'MU', 'MV', 'MW', 'MY', 'MZ', 'NE', 'NG', 'NI', 'NP', 'PG',
                'PH', 'RW', 'SC', 'SG', 'SL', 'SN', 'SO', 'SR', 'SS', 'SZ',
                'TD', 'TH', 'TL', 'TZ', 'UG', 'VN', 'VU', 'YE', 'ZM',
            }
            # Arid / desert countries (hot or cold desert – no spring/summer pattern)
            DESERT_COUNTRIES = {
                'AE', 'AF', 'BH', 'DJ', 'DZ', 'EG', 'ER', 'IQ', 'IR', 'JO',
                'KW', 'LY', 'MA', 'MR', 'OM', 'PK', 'QA', 'SA', 'SD', 'SY',
                'TM', 'TN', 'UZ',
            }
            # Arctic / subarctic countries
            ARCTIC_COUNTRIES = {
                'GL', 'IS', 'FO', 'SJ',
            }
            # Mediterranean climate countries
            MEDITERRANEAN_COUNTRIES = {
                'CY', 'ES', 'GR', 'HR', 'IL', 'IT', 'LB', 'MA', 'MT', 'PT',
                'RS', 'SI', 'TN', 'TR',
            }
            # Southern hemisphere temperate (inverted 4 seasons)
            SOUTHERN_TEMPERATE = {
                'AR', 'AU', 'CL', 'LS', 'NA', 'NZ', 'SZ', 'UY', 'ZA', 'ZW',
            }

            company = self.env.company
            country_code = (company.country_id.code or '').upper() if company.country_id else ''

            def get_seasonality(month):
                if country_code in TROPICAL_COUNTRIES:
                    # Tropical wet/dry – based on typical monsoon cycles
                    # Roughly: wet season Jun-Sep (NH monsoon) or Dec-Mar (SH monsoon)
                    # We use a generic representation
                    if month in (6, 7, 8, 9):
                        return _('Wet Season')
                    else:
                        return _('Dry Season')

                if country_code in DESERT_COUNTRIES:
                    # Arid climates: Peak Heat vs. Cooler/Mild period
                    if month in (6, 7, 8, 9):
                        return _('Peak Heat')
                    elif month in (12, 1, 2):
                        return _('Cool / Mild')
                    else:
                        return _('Transition')

                if country_code in ARCTIC_COUNTRIES:
                    # Arctic: Long Dark Winter vs. Short Bright Summer
                    if month in (11, 12, 1, 2, 3):
                        return _('Polar Winter')
                    elif month in (6, 7, 8):
                        return _('Midnight Sun / Summer')
                    else:
                        return _('Shoulder Season')

                if country_code in MEDITERRANEAN_COUNTRIES:
                    # Mediterranean: hot dry summer, mild wet winter
                    if month in (6, 7, 8):
                        return _('Hot Dry Summer')
                    elif month in (12, 1, 2):
                        return _('Mild Wet Winter')
                    else:
                        return _('Spring / Autumn Transition')

                if country_code in SOUTHERN_TEMPERATE:
                    # Southern hemisphere – inverted temperate seasons
                    if month in (12, 1, 2):
                        return _('Summer')
                    elif month in (3, 4, 5):
                        return _('Autumn')
                    elif month in (6, 7, 8):
                        return _('Winter')
                    else:
                        return _('Spring')

                # Default – Northern hemisphere temperate
                if month in (12, 1, 2):
                    return _('Winter')
                elif month in (3, 4, 5):
                    return _('Spring')
                elif month in (6, 7, 8):
                    return _('Summer')
                else:
                    return _('Autumn')

            DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


            # ── Pre-build active customer set from churn recency logic ──
            # A customer is 'Active' if they placed at least 1 sale order in the past 180 days.
            active_partner_ids = set()
            if 'active_customer' in custom_fields:
                cutoff = datetime.now() - timedelta(days=180)
                active_orders = self.env['sale.order'].search_read(
                    [('state', 'in', ['sale', 'done']), ('date_order', '>=', cutoff)],
                    ['partner_id']
                )
                for active_order in active_orders:
                    pid = active_order.get('partner_id')
                    if isinstance(pid, tuple):
                        active_partner_ids.add(pid[0])
                    elif pid:
                        active_partner_ids.add(pid)
            partner_country_map = {}
            if 'virtual_customer_country' in extra_fields:
                partner_ids = list({
                    order_rec.get('partner_id')[0] if isinstance(order_rec.get('partner_id'), tuple) else order_rec.get('partner_id')
                    for order_rec in orders if order_rec.get('partner_id')
                })
                if partner_ids:
                    partners_data = self.env['res.partner'].search_read([('id', 'in', partner_ids)], ['country_id'])
                    for partner_rec in partners_data:
                        country = partner_rec.get('country_id')
                        partner_country_map[partner_rec['id']] = country[1] if isinstance(country, tuple) and len(country) == 2 else 'N/A'

            dataset = []
            for order in orders:
                # ── Parse order date ──
                raw_date = order.get('date_order')
                order_dt = None
                if raw_date:
                    try:
                        order_dt = raw_date if isinstance(raw_date, datetime) else datetime.fromisoformat(str(raw_date))
                    except Exception:
                        order_dt = None

                # ── Build common base row shared across lines ──
                base = {}
                base['Sale Order Record ID'] = order.get('id')
                base['Order Reference'] = order.get('name')
                base['Trend Seasonality Score'] = order.get('trend_seasonality_score', 1.0)


                for field_name in extra_fields:
                    if field_name in existing_fields_info:
                        val = order.get(field_name, '')
                        if isinstance(val, tuple) and len(val) == 2:
                            val = val[1]
                        base[field_name] = val

                if 'customer_info' in custom_fields:
                    partner = order.get('partner_id')
                    if isinstance(partner, tuple) and len(partner) == 2:
                        base['Customer ID'] = partner[0]
                        base['Customer Name'] = partner[1]
                    else:
                        base['Customer ID'] = 'N/A'
                        base['Customer Name'] = 'N/A'

                if 'sale_order_amount' in custom_fields:
                    base['Sale Order Amount'] = order.get('amount_total', 0.0)

                if 'order_date' in custom_fields:
                    base['Order Date'] = str(raw_date) if raw_date else ''
                    base['Day of Week'] = DAY_NAMES[order_dt.weekday()] if order_dt else 'N/A'
                if 'virtual_customer_country' in extra_fields:
                    partner = order.get('partner_id')
                    pid = partner[0] if isinstance(partner, tuple) else partner
                    base['Customer Country'] = partner_country_map.get(pid, 'N/A')

                if 'virtual_month' in extra_fields:
                    base['Order Month'] = order_dt.strftime('%B') if order_dt else 'N/A'
                if 'virtual_quarter' in extra_fields:
                    base['Order Quarter'] = f"Q{(order_dt.month - 1) // 3 + 1}" if order_dt else 'N/A'
                if 'virtual_week' in extra_fields:
                    base['Order Week'] = f"Week {order_dt.isocalendar()[1]}" if order_dt else 'N/A'

                if 'leads_opportunities' in custom_fields:
                    opp_val = order.get('opportunity_id')
                    base['Leads & Opportunity'] = opp_val[1] if isinstance(opp_val, tuple) and len(opp_val) == 2 else ('Yes' if opp_val else 'No')

                if 'opportunity_id' in custom_fields:
                    opp_val = order.get('opportunity_id')
                    base['Opportunity ID'] = opp_val[0] if isinstance(opp_val, tuple) and len(opp_val) == 2 else 'N/A'
                    base['Opportunity Name'] = opp_val[1] if isinstance(opp_val, tuple) and len(opp_val) == 2 else 'N/A'

                if 'campaign_id' in custom_fields:
                    campaign_val = order.get('campaign_id')
                    base['Campaign'] = campaign_val[1] if isinstance(campaign_val, tuple) and len(campaign_val) == 2 else 'N/A'

                if 'holidays' in custom_fields:
                    if order_dt:
                        order_date_key = order_dt.date()
                        base['Holiday Sequence'] = 'Public Holiday' if order_date_key in holiday_dates else (
                            'Weekend' if order_dt.weekday() >= 5 else 'Working Day'
                        )
                    else:
                        base['Holiday Sequence'] = 'N/A'

                if 'website_visitors' in custom_fields:
                    website_val = order.get('website_id')
                    base['Website Visitors vs Orders'] = 'Website Order' if website_val else 'Direct / Backend'

                if 'seasonality' in custom_fields:
                    if order_dt:
                        base['Seasonality'] = get_seasonality(order_dt.month)
                    else:
                        base['Seasonality'] = 'N/A'

                if 'active_customer' in custom_fields:
                    partner_raw = order.get('partner_id')
                    partner_id_val = partner_raw[0] if isinstance(partner_raw, tuple) else partner_raw
                    base['Active Customer'] = 'Active' if partner_id_val in active_partner_ids else 'At Risk / Churned'

                # ── Expand to one row per order line when product_features selected ──
                if need_lines:
                    order_lines = lines_by_order.get(order['id'], [])
                    if order_lines:
                        for order_line in order_lines:
                            row = dict(base)
                            product_id_raw = order_line.get('product_id')
                            product_id = product_id_raw[0] if isinstance(product_id_raw, tuple) else product_id_raw
                            product_detail = product_info.get(product_id, {})
                            row['Product Name'] = product_id_raw[1] if isinstance(product_id_raw, tuple) else product_detail.get('name', 'N/A')
                            row['Product Category'] = product_detail.get('categ', 'N/A')
                            row['On Hand Qty'] = product_detail.get('on_hand_qty', 0.0)
                            row['Purchased Qty'] = float(order_line.get('product_uom_qty') or 0.0)
                            row['Unit Price'] = float(order_line.get('price_unit') or 0.0)
                            row['Discount %'] = float(order_line.get('discount') or 0.0)
                            if 'virtual_product_type' in extra_fields:
                                row['Product Type'] = product_detail.get('product_type', 'N/A')
                            dataset.append(row)
                    else:
                        # Order has no lines – still emit the base row
                        row = dict(base)
                        row['Product Name'] = 'N/A'
                        row['Product Category'] = 'N/A'
                        row['On Hand Qty'] = 0.0
                        row['Purchased Qty'] = 0.0
                        row['Unit Price'] = 0.0
                        row['Discount %'] = 0.0
                        if 'virtual_product_type' in extra_fields:
                            row['Product Type'] = 'N/A'
                        dataset.append(row)
                else:
                    dataset.append(base)

            # ── Time-Series Feature Engineering ──
            # All features computed oldest-first so each row looks BACK at prior rows.
            #
            # sales_lag_1  : sale amount 1 row ago
            # sales_lag_2  : sale amount 2 rows ago
            # sales_lag_3  : sale amount 3 rows ago
            # rolling_mean_3: simple average of the 3 immediately preceding amounts
            # EMA3 (α=0.50): span-3 EMA — 50% weight on current, 25% on t-1, 12.5% on t-2 …
            # EMA6 (α=0.29): span-6 EMA — 28.6% weight on current, more gradual smoothing
            # (EMA3_ALPHA / EMA6_ALPHA are module-level constants)

            # Sort ascending by date — SQL fetched DESC, features need chronological order
            def _sort_key_by_date(dataset_row):
                raw = dataset_row.get('Order Date') or dataset_row.get('date_order') or ''
                return str(raw)

            dataset.sort(key=_sort_key_by_date)

            # ── Aggregate Dataset if selected ──
            # Sub-tables for sale orders and order lines (populated only for W/M/Y)
            sale_orders_table = []
            orderlines_table = []

            if aggregate in ['W', 'M', 'Y'] and dataset:
                try:

                    df = pd.DataFrame(dataset)
                    date_col = 'Order Date' if 'Order Date' in df.columns else 'date_order'
                    amt_col = 'Sale Order Amount' if 'Sale Order Amount' in df.columns else 'amount_total'

                    if date_col not in df.columns:
                        raise ValueError("Date column not found in dataset")

                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                    df = df.dropna(subset=[date_col])
                    df = df.sort_values(date_col)

                    if amt_col in df.columns:
                        df[amt_col] = pd.to_numeric(df[amt_col], errors='coerce').fillna(0.0)
                    else:
                        df[amt_col] = 0.0

                    # ── Period key column ──
                    if aggregate == 'W':
                        df['_period'] = df[date_col].dt.to_period('W').dt.end_time.dt.strftime('%Y-%m-%d')
                    elif aggregate == 'M':
                        df['_period'] = df[date_col].dt.strftime('%Y-%m')
                    else:  # Y
                        df['_period'] = df[date_col].dt.strftime('%Y')

                    # ── Define field roles ──
                    # Numeric cols: summed per period
                    NUMERIC_COLS = [amt_col, 'Purchased Qty', 'On Hand Qty', 'Unit Price', 'Discount %', 'Trend Seasonality Score']
                    # Mean instead of sum for price/discount/on-hand
                    MEAN_COLS = ['On Hand Qty', 'Unit Price', 'Discount %', 'Trend Seasonality Score']

                    # Comma-join text fields (multi-value categoricals)
                    COMMA_JOIN_COLS = [
                        'Leads & Opportunity', 'Opportunity ID', 'Opportunity Name',
                        'Campaign', 'Website Visitors vs Orders', 'Holiday Sequence',
                        'Seasonality', 'Active Customer',
                    ]
                    # First-value fields (stable within a period)
                    FIRST_COLS = [
                        'Order Month', 'Order Quarter', 'Order Week',
                        'Customer Country',
                        'Product Type',
                    ]
                    # Columns handled via sub-tables (excluded from main grouped row)
                    PRODUCT_COLS = ['Product Name', 'Product Category', 'On Hand Qty', 'Purchased Qty', 'Unit Price', 'Discount %', 'Product Type']
                    CUSTOMER_COLS = ['Customer ID', 'Customer Name']
                    # Columns to drop entirely in aggregated view
                    DROP_COLS = {'Sale Order Record ID', 'Order Reference', 'Day of Week'}

                    def _safe_comma_join(series):
                        """Return unique non-null values as a comma-separated string."""
                        vals = series.dropna().astype(str).unique().tolist()
                        return ', '.join(v for v in vals if v and v not in ('nan', 'N/A', 'False', 'None')) or 'N/A'

                    # ── Build Sale Orders Table ──
                    if 'Sale Order Record ID' in df.columns:
                        so_df = df.drop_duplicates(subset=['Sale Order Record ID']).copy()
                        
                        so_cols = ['_period', 'Sale Order Record ID', 'Order Reference', 'Customer Name', amt_col]
                        if 'Campaign' in df.columns: so_cols.append('Campaign')
                        if 'Opportunity ID' in df.columns: so_cols.append('Opportunity ID')
                        if 'Opportunity Name' in df.columns: so_cols.append('Opportunity Name')
                        if 'Holiday Sequence' in df.columns: so_cols.append('Holiday Sequence')
                        if 'Website Visitors vs Orders' in df.columns: so_cols.append('Website Visitors vs Orders')
                        if 'Active Customer' in df.columns: so_cols.append('Active Customer')
                        if 'Trend Seasonality Score' in df.columns: so_cols.append('Trend Seasonality Score')

                        
                        sale_order_list = so_df[[c for c in so_cols if c in so_df.columns]].to_dict(orient='records')
                        
                        for so in sale_order_list:
                            so['Period'] = so.pop('_period')
                            so_id = so.get('Sale Order Record ID')
                            lines = lines_by_order.get(so_id, [])
                            so['Orderlines IDs'] = ', '.join([str(line['id']) for line in lines]) if lines else 'N/A'
                            
                        sale_orders_table = sale_order_list
                    
                    # ── Build Order Lines Table ──
                    if need_lines and 'Sale Order Record ID' in df.columns:
                        ol_list = []
                        so_ids = df['Sale Order Record ID'].dropna().unique()
                        for so_id in so_ids:
                            lines = lines_by_order.get(so_id, [])
                            for line in lines:
                                pid = line.get('product_id')
                                pname = pid[1] if isinstance(pid, tuple) else (product_info.get(pid, {}).get('name', 'N/A') if pid else 'N/A')
                                pid_id = pid[0] if isinstance(pid, tuple) else pid
                                on_hand = product_info.get(pid_id, {}).get('on_hand_qty', 0.0) if pid_id else 0.0
                                ol_list.append({
                                    'Orderline ID': line.get('id'),
                                    'Sale Order Record ID': so_id,
                                    'Product Name': pname,
                                    'On Hand Qty': round(on_hand, 2),
                                    'Unit Price': round(float(line.get('price_unit') or 0.0), 2),
                                    'Discount %': round(float(line.get('discount') or 0.0), 2)
                                })
                        orderlines_table = ol_list

                    # ── Build main aggregated table ──
                    # Exclude product/customer detail cols and drop cols from main view
                    exclude_from_main = DROP_COLS | set(PRODUCT_COLS) | set(CUSTOMER_COLS)
                    exclude_from_main.update([
                        'Opportunity ID', 'Opportunity Name', 'Leads & Opportunity', 'Campaign', 
                        'Holiday Sequence', 'Website Visitors vs Orders', 'Active Customer'
                    ])
                    if aggregate == 'M':
                        exclude_from_main.add('Order Week')
                    elif aggregate == 'Y':
                        exclude_from_main.update(['Order Week', 'Order Month', 'Order Quarter', 'Seasonality'])
                    
                    main_df = df.drop(columns=[c for c in exclude_from_main if c in df.columns], errors='ignore')

                    # Build aggregation rules for remaining columns
                    agg_dict = {}
                    for col in main_df.columns:
                        if col in ('_period', date_col):
                            continue
                        if col == amt_col:
                            agg_dict[col] = 'sum'
                        elif col in COMMA_JOIN_COLS:
                            agg_dict[col] = _safe_comma_join
                        elif col in MEAN_COLS:
                            agg_dict[col] = 'mean'
                        elif col in NUMERIC_COLS:
                            agg_dict[col] = 'sum'
                        elif col in FIRST_COLS:
                            agg_dict[col] = 'first'
                        else:
                            agg_dict[col] = 'first'

                    grouped = main_df.groupby('_period', sort=True).agg(agg_dict).reset_index()
                    grouped = grouped.rename(columns={'_period': date_col})

                    if amt_col in df.columns and 'Sale Order Record ID' in df.columns:
                        unique_orders_df = df.drop_duplicates(subset=['_period', 'Sale Order Record ID'])
                        correct_period_sums = unique_orders_df.groupby('_period')[amt_col].sum()
                        grouped[amt_col] = grouped[date_col].map(correct_period_sums).fillna(0.0)

                    if aggregate == 'W' and amt_col in grouped.columns:
                        grouped_amounts = grouped[amt_col].tolist()
                        min_grouped = min(grouped_amounts) if grouped_amounts else 0.0
                        max_grouped = max(grouped_amounts) if grouped_amounts else 0.0
                        grouped_scores = []
                        for amt in grouped_amounts:
                            if max_grouped > min_grouped:
                                score = 1.0 + ((amt - min_grouped) * 9.0) / (max_grouped - min_grouped)
                            else:
                                score = 1.0
                            grouped_scores.append(round(max(1.0, min(10.0, score)), 2))
                        grouped['Trend Seasonality Score'] = grouped_scores

                    # Round float columns
                    for c in grouped.columns:
                        if pd.api.types.is_float_dtype(grouped[c]):
                            grouped[c] = grouped[c].round(2)

                    grouped = grouped.where(pd.notnull(grouped), None)
                    dataset = json.loads(grouped.to_json(orient='records', date_format='iso'))

                    # ── Number of Holidays and Sale Order IDs logic ──
                    for row in dataset:
                        period_val = row.get(date_col)
                        if period_val:
                            if aggregate == 'W':
                                end_dt = pd.to_datetime(period_val)
                                start_dt = end_dt - pd.Timedelta(days=6)
                                h_count = sum(1 for d in holiday_dates if start_dt.date() <= d <= end_dt.date())
                            elif aggregate == 'M':
                                year, month = int(period_val[:4]), int(period_val[5:7])
                                h_count = sum(1 for d in holiday_dates if d.year == year and d.month == month)
                            else: # Y
                                year = int(period_val)
                                h_count = sum(1 for d in holiday_dates if d.year == year)
                            row['No of Holidays'] = h_count
                        else:
                            row['No of Holidays'] = 0

                        # Get all unique sale order IDs for this period
                        if 'Sale Order Record ID' in df.columns:
                            period_df = df[df['_period'] == period_val]
                            period_orders = period_df['Sale Order Record ID'].dropna().unique()
                            row['Sale Order IDs'] = ', '.join(map(str, map(int, period_orders)))
                            
                            # Count of opportunities
                            if 'Opportunity ID' in period_df.columns:
                                opps = period_df['Opportunity ID'].dropna().unique()
                                row['No of Opportunities'] = len([o for o in opps if str(o) not in ('nan', 'N/A', 'False', 'None')])
                            
                            # Count of Website/Direct orders
                            if 'Website Visitors vs Orders' in period_df.columns:
                                so_website = period_df.drop_duplicates(subset=['Sale Order Record ID'])['Website Visitors vs Orders'].dropna().astype(str)
                                row['No of Website Orders'] = int(sum(so_website == 'Website Order'))
                                row['No of Direct Orders'] = int(sum(so_website == 'Direct / Backend'))
                                
                            # Count of Active Customers
                            if 'Active Customer' in period_df.columns:
                                so_active = period_df.drop_duplicates(subset=['Sale Order Record ID'])['Active Customer'].dropna().astype(str)
                                row['No of Active Customers'] = int(sum(so_active == 'Yes'))
                                
                            # Count of Campaigns
                            if 'Campaign' in period_df.columns:
                                row['No of Campaigns'] = len(period_df['Campaign'].dropna().unique())
                                
                            # Product metrics (Inventory & Price)
                            if 'On Hand Qty' in period_df.columns:
                                row['Total On Hand Qty'] = float(period_df['On Hand Qty'].dropna().sum())
                            if 'Unit Price' in period_df.columns:
                                row['Avg Unit Price'] = float(period_df['Unit Price'].dropna().mean()) if len(period_df['Unit Price'].dropna()) > 0 else 0.0
                            if 'Discount %' in period_df.columns:
                                row['Avg Discount'] = float(period_df['Discount %'].dropna().mean()) if len(period_df['Discount %'].dropna()) > 0 else 0.0


                except Exception as agg_err:
                    _logger.exception("Cyllo analytics: aggregation failed")
                    raise agg_err

            ema3_running = None
            ema6_running = None
            amount_history = []   # sliding window of raw amounts, needed for rolling mean

            for dataset_row in dataset:
                current_amount = float(
                    dataset_row.get('Sale Order Amount') or
                    dataset_row.get('amount_total') or 0.0
                )

                # ── Lag features ──
                dataset_row['sales_lag_1'] = round(amount_history[-1], 2) if len(amount_history) >= 1 else None
                dataset_row['sales_lag_2'] = round(amount_history[-2], 2) if len(amount_history) >= 2 else None
                dataset_row['sales_lag_3'] = round(amount_history[-3], 2) if len(amount_history) >= 3 else None

                # ── Rolling mean of the 3 preceding values ──
                if len(amount_history) >= 3:
                    dataset_row['rolling_mean_3'] = round(sum(amount_history[-3:]) / 3, 2)
                else:
                    dataset_row['rolling_mean_3'] = None

                # ── EMA-3 (span=3, α=0.5) ──
                if ema3_running is None:
                    ema3_running = current_amount
                else:
                    ema3_running = EMA3_ALPHA * current_amount + (1 - EMA3_ALPHA) * ema3_running
                dataset_row['EMA3'] = round(ema3_running, 2)

                # ── EMA-6 (span=6, α≈0.286) ──
                if ema6_running is None:
                    ema6_running = current_amount
                else:
                    ema6_running = EMA6_ALPHA * current_amount + (1 - EMA6_ALPHA) * ema6_running
                dataset_row['EMA6'] = round(ema6_running, 2)

                # Append current amount AFTER writing lag/rolling fields
                # so this row's amount only appears as a lag in FUTURE rows
                amount_history.append(current_amount)

            # ── Shared Forecasting Engine (AI & Algorithm) ──
            if mode in ['ai', 'algorithm']:
                forecast_data = {}
                historical_data = {}
                forecast_reasons = {}
                sentimental_scores = {}
                ai_status = None  # AI-mode only: 'ok' when the AI ran, else a message
                baseline_forecast = {}  # algorithm forecast kept so AI can be recomputed later
                if len(dataset) >= 5:
                    date_col = 'Order Date' if dataset and 'Order Date' in dataset[0] else 'date_order'
                    amt_col = 'Sale Order Amount' if dataset and 'Sale Order Amount' in dataset[0] else 'amount_total'

                    # Normalise historical keys to match forecast key format per aggregate.
                    # After aggregation: weekly=YYYY-MM-DD, monthly=YYYY-MM, yearly=YYYY.
                    def _fmt_date_key(raw_val, agg):
                        import pandas as _pd
                        try:
                            dt = _pd.to_datetime(raw_val, errors='coerce')
                            if _pd.isnull(dt):
                                return str(raw_val)
                            if agg == 'M':
                                return dt.strftime('%Y-%m')
                            elif agg == 'Y':
                                return dt.strftime('%Y')
                            else:
                                return dt.strftime('%Y-%m-%d')
                        except Exception:
                            return str(raw_val)

                    historical_dict = {
                        _fmt_date_key(row.get(date_col), aggregate): float(row.get(amt_col) or 0.0)
                        for row in dataset if row.get(date_col)
                    }
                    historical_data = dict(list(historical_dict.items())[-10:])
                    # 1. Run Algorithm Baseline
                    try:
                        pdf = pd.DataFrame(dataset)

                        if aggregate == 'W':
                            # After weekly aggregation the date column holds the calendar
                            # date of the week's end (formatted %Y-%m-%d at line ~710),
                            # not an ISO-week string, so parse it as a plain date.
                            pdf['ds'] = pd.to_datetime(pdf[date_col], errors='coerce')
                        elif aggregate == 'M':
                            pdf['ds'] = pd.to_datetime(pdf[date_col] + '-01', errors='coerce')
                        elif aggregate == 'Y':
                            pdf['ds'] = pd.to_datetime(pdf[date_col] + '-01-01', errors='coerce')
                        else:
                            pdf['ds'] = pd.to_datetime(pdf[date_col], errors='coerce')
                            
                        # Prophet does not support timezone-aware dates. Strip timezone if present.
                        pdf['ds'] = pdf['ds'].dt.tz_localize(None)

                        pdf['y'] = pd.to_numeric(pdf[amt_col], errors='coerce').fillna(0)

                        regressors = [
                            'sales_lag_1', 'sales_lag_2', 'rolling_mean_3', 'EMA3', 'EMA6',
                            'Trend Seasonality Score',
                            'No of Holidays', 'No of Opportunities', 'No of Website Orders',
                            'Total On Hand Qty', 'Avg Unit Price', 'Avg Discount', 'No of Active Customers', 'No of Campaigns'
                        ]
                        valid_regressors = [r for r in regressors if r in pdf.columns]
                        for r in valid_regressors:
                            pdf[r] = pd.to_numeric(pdf[r], errors='coerce').bfill().ffill().fillna(0)

                        m = Prophet(
                            growth='flat',
                            yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False,
                            changepoint_range=0.95, changepoint_prior_scale=0.1
                        )
                        for r in valid_regressors:
                            m.add_regressor(r)

                        m.fit(pdf[['ds', 'y'] + valid_regressors].dropna(subset=['ds']))

                        future_periods = 10
                        freq = 'D'
                        if aggregate == 'W': freq = 'W'
                        elif aggregate == 'M': freq = 'MS'
                        elif aggregate == 'Y': freq = 'YS'

                        future_dates = pd.date_range(start=pdf['ds'].max(), periods=future_periods + 1, freq=freq)[1:]

                        exog_proj = {}
                        for r in ['No of Opportunities', 'No of Website Orders', 'Total On Hand Qty', 'Avg Unit Price', 'Avg Discount', 'No of Active Customers', 'No of Campaigns', 'Trend Seasonality Score']:
                            if r in valid_regressors:
                                hist_vals = pdf[r].tolist()
                                proj = []
                                while len(proj) < future_periods:
                                    proj.extend(hist_vals[-future_periods:] if len(hist_vals) >= future_periods else hist_vals)
                                exog_proj[r] = proj[:future_periods]

                        history_y = list(pdf['y'])
                        running_ema3 = pdf['EMA3'].iloc[-1] if 'EMA3' in valid_regressors else 0
                        running_ema6 = pdf['EMA6'].iloc[-1] if 'EMA6' in valid_regressors else 0

                        for i, future_dt in enumerate(future_dates):
                            row_dict = {'ds': [future_dt]}

                            # All aggregates feed raw recency values to Prophet's regressors.
                            if 'sales_lag_1' in valid_regressors: row_dict['sales_lag_1'] = [history_y[-1]]
                            if 'sales_lag_2' in valid_regressors: row_dict['sales_lag_2'] = [history_y[-2] if len(history_y) >= 2 else history_y[-1]]
                            if 'rolling_mean_3' in valid_regressors: row_dict['rolling_mean_3'] = [np.mean(history_y[-3:]) if len(history_y) >= 3 else history_y[-1]]

                            if 'EMA3' in valid_regressors: row_dict['EMA3'] = [running_ema3]
                            if 'EMA6' in valid_regressors: row_dict['EMA6'] = [running_ema6]

                            if 'No of Holidays' in valid_regressors:
                                if aggregate == 'W':
                                    start = future_dt - pd.Timedelta(days=6)
                                    hc = sum(1 for d in holiday_dates if start.date() <= d <= future_dt.date())
                                elif aggregate == 'M':
                                    hc = sum(1 for d in holiday_dates if d.year == future_dt.year and d.month == future_dt.month)
                                elif aggregate == 'Y':
                                    hc = sum(1 for d in holiday_dates if d.year == future_dt.year)
                                else:
                                    hc = sum(1 for d in holiday_dates if d == future_dt.date())
                                row_dict['No of Holidays'] = [hc]

                            if 'No of Opportunities' in valid_regressors: row_dict['No of Opportunities'] = [exog_proj['No of Opportunities'][i]]
                            if 'No of Website Orders' in valid_regressors: row_dict['No of Website Orders'] = [exog_proj['No of Website Orders'][i]]
                            if 'Total On Hand Qty' in valid_regressors: row_dict['Total On Hand Qty'] = [exog_proj['Total On Hand Qty'][i]]
                            if 'Avg Unit Price' in valid_regressors: row_dict['Avg Unit Price'] = [exog_proj['Avg Unit Price'][i]]
                            if 'Avg Discount' in valid_regressors: row_dict['Avg Discount'] = [exog_proj['Avg Discount'][i]]
                            if 'No of Active Customers' in valid_regressors: row_dict['No of Active Customers'] = [exog_proj['No of Active Customers'][i]]
                            if 'No of Campaigns' in valid_regressors: row_dict['No of Campaigns'] = [exog_proj['No of Campaigns'][i]]
                            if 'Trend Seasonality Score' in valid_regressors: row_dict['Trend Seasonality Score'] = [exog_proj['Trend Seasonality Score'][i]]

                            future_df = pd.DataFrame(row_dict)
                            forecast_out = m.predict(future_df)

                            y_pred_prophet = max(0.0, float(forecast_out['yhat'].iloc[0]))

                            pct_changes = []
                            history_ds = pdf['ds'].tolist()
                            history_y_vals = pdf['y'].tolist()

                            if aggregate == 'M':
                                get_key = lambda dt: dt.month
                            elif aggregate == 'W':
                                get_key = lambda dt: dt.isocalendar()[1]
                            elif aggregate == 'D':
                                get_key = lambda dt: dt.weekday()
                            else:
                                get_key = lambda dt: 0

                            target_key = get_key(future_dt)

                            # Weekly uses the same seasonal logic as Monthly/Yearly:
                            # average period-over-period change for the matching cycle key,
                            # applied to the most recent value, blended 50/50 with Prophet.
                            for idx in range(1, len(history_ds)):
                                if get_key(history_ds[idx]) == target_key:
                                    prev_val = history_y_vals[idx - 1]
                                    curr_val = history_y_vals[idx]
                                    if prev_val and prev_val != 0:
                                        pct_changes.append((curr_val - prev_val) / abs(prev_val))

                            if pct_changes:
                                pct_change = float(np.mean(pct_changes))
                            else:
                                pct_change = 0.0

                            recent_baseline = history_y[-1]
                            seasonal_pred = max(0.0, recent_baseline * (1 + pct_change))
                            y_pred = max(0.0, (y_pred_prophet * 0.5) + (seasonal_pred * 0.5))

                            date_str = future_dt.strftime('%Y-%m-%d')
                            if aggregate == 'M': date_str = future_dt.strftime('%Y-%m')
                            if aggregate == 'Y': date_str = future_dt.strftime('%Y')

                            reasons = []
                            lag1 = row_dict.get('sales_lag_1', [None])[0]
                            ema3_val = row_dict.get('EMA3', [None])[0]
                            if lag1 is not None and y_pred > lag1:
                                reasons.append(f"Sales up from previous period (Lag1: {round(lag1/1000, 1)}K -> {round(y_pred/1000, 1)}K)")
                            elif lag1 is not None and y_pred < lag1:
                                reasons.append(f"Sales down from previous period (Lag1: {round(lag1/1000, 1)}K -> {round(y_pred/1000, 1)}K)")

                            hc = row_dict.get('No of Holidays', [0])[0]
                            if hc and hc > 0:
                                reasons.append(f"{hc} holiday(s) in this period - activity typically dips")

                            inv = row_dict.get('Total On Hand Qty', [None])[0]
                            if inv is not None and inv <= 0:
                                reasons.append("Inventory at or near zero - likely supply-driven slowdown")
                            elif inv is not None and inv > 0:
                                reasons.append(f"On-hand qty: {round(inv, 0)} - stock available to drive sales")

                            opps = row_dict.get('No of Opportunities', [None])[0]
                            if opps is not None:
                                reasons.append(f"{int(opps)} opportunity/opportunities projected for this period")

                            web = row_dict.get('No of Website Orders', [None])[0]
                            if web is not None and web > 0:
                                reasons.append(f"{int(web)} website order(s) expected - online channel active")

                            if ema3_val is not None and ema3_val > 0:
                                if y_pred > ema3_val:
                                    reasons.append(f"EMA3 ({round(ema3_val/1000,1)}K) signals upward momentum")
                                else:
                                    reasons.append(f"EMA3 ({round(ema3_val/1000,1)}K) signals downward pressure")

                            if pct_change > 0.05:
                                reasons.append(f"Historical pattern shows a similar spike in this cycle (+{round(pct_change*100,1)}%)")
                            elif pct_change < -0.05:
                                reasons.append(f"Historical pattern shows a similar drop in this cycle ({round(pct_change*100,1)}%)")
                            else:
                                reasons.append("Historically stable period - no major cyclical swing expected")

                            forecast_reasons[date_str] = reasons
                            forecast_data[date_str] = round(y_pred, 2)

                            history_y.append(y_pred)
                            running_ema3 = EMA3_ALPHA * y_pred + (1 - EMA3_ALPHA) * running_ema3
                            running_ema6 = EMA6_ALPHA * y_pred + (1 - EMA6_ALPHA) * running_ema6

                    except Exception as algo_err:
                        _logger.warning("Algorithm forecast failed", exc_info=True)
                        raise algo_err

                    
                    # 2. AI Mode Specific Processing — adjust the algorithm baseline with
                    #    real news, semantic-searched using the user's keywords.
                    if mode == 'ai':
                        # Keep the raw algorithm forecast so the AI layer can be recomputed
                        # later (via recompute_forecast) with different keywords.
                        baseline_forecast = {k: float(v) for k, v in forecast_data.items()}
                        ai_result = self._forecast_ai_adjust(
                            baseline_forecast, orig_params.get('keywords'))
                        forecast_data = ai_result.get('forecast') or forecast_data
                        if ai_result.get('forecast_reasons'):
                            forecast_reasons = ai_result['forecast_reasons']
                        sentimental_scores = ai_result.get('sentimental_scores') or {}
                        ai_status = ai_result.get('ai_status')

                # Hover context ("Why this forecast?") is AI-only: expose reasons and
                # sentiment scores just when the AI actually produced them. In Algorithm
                # mode (or when AI could not run) return empty dicts so the chart tooltip
                # shows no reasoning context.
                ai_ran = (mode == 'ai' and ai_status == 'ok')
                res_payload = {
                    'dataset': dataset,
                    'forecast': forecast_data,
                    'baseline_forecast': baseline_forecast,
                    'forecast_reasons': forecast_reasons if ai_ran else {},
                    'sentimental_scores': sentimental_scores if ai_ran else {},
                    'historical': historical_data,
                    'sale_orders_table': sale_orders_table,
                    'orderlines_table': orderlines_table,
                    'ai_status': ai_status,
                    'column_labels': self._column_labels_for(extra_fields),
                }
                self.env['sale.forecast.result']._save_forecast(orig_params, res_payload)
                return res_payload

            res_payload = {
                'dataset': dataset,
                'sale_orders_table': sale_orders_table,
                'orderlines_table': orderlines_table,
                'column_labels': self._column_labels_for(extra_fields),
            }
            self.env['sale.forecast.result']._save_forecast(orig_params, res_payload)
            return res_payload
        except ValidationError:
            # Configuration errors (e.g. missing AI API key) must surface to the
            # user as a proper validation dialog, not be swallowed as a generic
            # "Server Error" string.
            raise
        except MemoryError:
            return {'error': 'The requested date range contains too much data to be processed at once (Memory Limit Exceeded). Please select a smaller date range.'}
        except Exception as e:
            _logger.exception("Sales forecast extraction failed")
            return {'error': str(e) or repr(e)}

    @api.model
    def get_last_forecast(self):
        saved = self.env['sale.forecast.result'].search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if saved:
            results = saved.results
            # Attach fresh, current-language column labels, and trim the
            # (potentially huge) sub-tables down to the number of rows the UI
            # actually renders. The stored result keeps every row (57k+ / 189k+
            # on large datasets), but the wizard only displays the first
            # PREVIEW_LIMIT rows of each sub-table; shipping them all back would
            # bloat this reload to tens of MB and make reopening the menu fail
            # intermittently (the page then stays on the guidelines screen).
            # The full tables remain in the DB and are read server-side for the
            # Excel export, so trimming here does not affect the download.
            PREVIEW_LIMIT = 200
            try:
                data = json.loads(results) if results else {}
                saved_params = json.loads(saved.params) if saved.params else {}
                data['column_labels'] = self._column_labels_for(saved_params.get('extra_fields'))
                for _table_key in ('sale_orders_table', 'orderlines_table'):
                    rows = data.get(_table_key)
                    if isinstance(rows, list) and len(rows) > PREVIEW_LIMIT:
                        data[_table_key] = rows[:PREVIEW_LIMIT]
                results = json.dumps(data, default=str)
            except Exception:
                pass
            return {
                'params': saved.params,
                'results': results,
            }
        return False

    # ──────────────────────────────────────────────────────────────────
    #  News-driven AI adjustment helpers (shared by generate + recompute)
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_keywords(keywords):
        """Normalise the comma-separated keyword input into a clean list."""
        if not keywords:
            return []
        if isinstance(keywords, (list, tuple)):
            items = keywords
        else:
            items = str(keywords).split(',')
        seen, out = set(), []
        for kw in items:
            kw = (kw or '').strip()
            if kw and kw.lower() not in seen:
                seen.add(kw.lower())
                out.append(kw)
        return out

    @api.model
    def check_ai_credentials(self):
        """Raise a ValidationError if AI mode has no OpenAI API key configured.

        Called up-front from the Sales Forecasting wizard (before any heavy
        processing) so the user gets a proper validation dialog instead of a
        failed dataset generation."""
        self.env.cr.execute("SELECT api_key FROM cyllo_ai_config LIMIT 1")
        row = self.env.cr.fetchone()
        if not (row and row[0]):
            raise ValidationError(_(
                'AI mode is not configured: no OpenAI API key found in AI '
                'Credentials.\n\nPlease configure the API key in the AI '
                'settings, or switch to Algorithm mode.'))
        return True

    def _forecast_ai_adjust(self, baseline_forecast, keywords):
        """Adjust a baseline forecast (period -> amount) using the AI model's own
        knowledge of recent news/events (no external news API). The AI returns a
        multiplier / sentiment / reasons per period; the multiplication against the
        real baseline is done here for reliable arithmetic.

        Returns a dict: forecast, forecast_reasons, sentimental_scores,
        important_news, keywords, ai_status ('ok' or an explanation)."""
        baseline_forecast = {k: float(v) for k, v in (baseline_forecast or {}).items()}
        out = {
            'forecast': dict(baseline_forecast),
            'forecast_reasons': {},
            'sentimental_scores': {},
            'important_news': [],
            'keywords': self._parse_keywords(keywords),
            'ai_status': None,
        }
        # OpenAI credentials + selected model from the AI config.
        self.env.cr.execute("""
            SELECT c.api_key, m.name
            FROM cyllo_ai_config c
            LEFT JOIN cyllo_llm m ON m.id = c.llm_model_id
            LIMIT 1
        """)
        row = self.env.cr.fetchone()
        api_key = row[0] if row else False
        model_name = (row[1] if row and row[1] else 'gpt-4o-mini')
        if not api_key:
            raise ValidationError(_(
                'AI mode is not configured: no OpenAI API key found in AI '
                'Credentials.\n\nPlease configure the API key in the AI '
                'settings, or switch to Algorithm mode.'))
        if not baseline_forecast:
            out['ai_status'] = 'No baseline forecast available to adjust.'
            return out
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            kw_list = out['keywords']
            focus = ((
                'The user provided these focus keywords: %s. Semantically search your '
                'knowledge of recent news and events for items related to these keywords, '
                'and give that keyword-matched news the HIGHEST preference when judging '
                'sentiment and the multiplier. You may also weigh other major market news, '
                'but at lower priority.' % ', '.join(kw_list)
            ) if kw_list else (
                'No keywords were provided, so consider ALL relevant recent global and '
                'market news broadly, giving no topic any special emphasis or preference '
                '- weigh each item purely by its likely impact on sales demand.'))
            prompt = f"""
                You are an expert business forecasting analyst who is aware of recent
                global and market news and events.
                {focus}

                Using the CURRENT NEWS AND EVENTS YOU ARE AWARE OF, adjust the algorithmic
                baseline sales forecast below (period -> predicted sale amount):
                1. Identify the key recent news / events that could affect sales demand.
                2. Judge the overall market sentiment they imply.
                3. For EACH period key in the baseline, output:
                   - "sentimental_score": number from -1.0 (very negative) to 1.0 (very
                     positive) reflecting the news impact on demand.
                   - "multiplier": factor to multiply the baseline by. Positive news -> > 1.0,
                     negative news -> < 1.0. Keep it realistic (0.80 - 1.20) unless the news is
                     extreme. Impact is strongest on the NEAREST periods and fades for later ones.
                   - "reasons": 1-3 short strings naming the SPECIFIC news / event.
                4. Also return "important_news": the news/events you considered.

                ALGORITHMIC BASELINE FORECAST (period -> amount):
                {json.dumps(baseline_forecast, default=str)}

                RETURN ONLY VALID JSON with the SAME period keys as the baseline:
                {{
                    "important_news": ["news 1", "news 2"],
                    "multiplier": {{ "PERIOD": number }},
                    "sentimental_score": {{ "PERIOD": number }},
                    "forecast_reasons": {{ "PERIOD": ["reason 1", "reason 2"] }}
                }}
                """
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You adjust sales forecasts using your knowledge of current news and events. Reply with strict JSON only."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )
            response_data = json.loads(response.choices[0].message.content or '{}')
            multipliers = response_data.get('multiplier', {}) or {}
            ai_reasons = response_data.get('forecast_reasons', {}) or {}
            ai_scores = response_data.get('sentimental_score', {}) or {}
            out['important_news'] = response_data.get('important_news', []) or []

            # Multiply the AI's per-period factor with the real baseline here.
            adjusted = {}
            for period, base_val in baseline_forecast.items():
                try:
                    mult = float(multipliers.get(period, 1.0))
                except (TypeError, ValueError):
                    mult = 1.0
                mult = max(0.5, min(1.5, mult))  # guard against extremes
                adjusted[period] = round(max(0.0, base_val * mult), 2)
            out['forecast'] = adjusted
            out['forecast_reasons'] = ai_reasons
            out['sentimental_scores'] = ai_scores
            out['ai_status'] = 'ok'
        except Exception as e:
            _logger.warning("AI forecast adjustment failed", exc_info=True)
            out['ai_status'] = ('AI adjustment failed (%s). Showing the algorithm baseline.'
                                % (str(e) or repr(e)))
        return out

    @api.model
    def recompute_forecast(self, params):
        """Re-run ONLY the news/AI layer on the previously computed algorithm
        baseline, using new keywords. Does not re-run the (expensive) algorithm."""
        params = params or {}
        keywords = params.get('keywords')
        saved = self.env['sale.forecast.result'].search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not saved or not saved.results:
            return {'error': 'No previous forecast found to recompute.'}
        try:
            results = json.loads(saved.results)
            saved_params = json.loads(saved.params) if saved.params else {}
        except Exception:
            return {'error': 'Saved forecast could not be read.'}

        baseline = results.get('baseline_forecast') or results.get('forecast') or {}
        if not baseline:
            return {'error': 'No baseline forecast stored; please run a new query first.'}

        # If the keywords are unchanged from the last run, nothing new was added:
        # return the already-computed result without calling the AI again.
        new_kw = self._parse_keywords(keywords)
        old_kw = self._parse_keywords(saved_params.get('keywords'))
        if [k.lower() for k in new_kw] == [k.lower() for k in old_kw]:
            return {
                'forecast': results.get('forecast') or {},
                'forecast_reasons': results.get('forecast_reasons') or {},
                'sentimental_scores': results.get('sentimental_scores') or {},
                'historical': results.get('historical') or {},
                'important_news': [],
                'ai_status': results.get('ai_status') or 'ok',
                'unchanged': True,
            }

        ai_result = self._forecast_ai_adjust(baseline, keywords)
        ai_ran = ai_result.get('ai_status') == 'ok'

        # Update and persist the saved forecast so a reload keeps the new values.
        results['forecast'] = ai_result['forecast']
        results['forecast_reasons'] = ai_result['forecast_reasons'] if ai_ran else {}
        results['sentimental_scores'] = ai_result['sentimental_scores'] if ai_ran else {}
        results['ai_status'] = ai_result['ai_status']
        saved_params['keywords'] = params.get('keywords') or ''
        self.env['sale.forecast.result']._save_forecast(saved_params, results)

        return {
            'forecast': results['forecast'],
            'forecast_reasons': results['forecast_reasons'],
            'sentimental_scores': results['sentimental_scores'],
            'historical': results.get('historical') or {},
            'important_news': ai_result.get('important_news') or [],
            'ai_status': ai_result['ai_status'],
        }


