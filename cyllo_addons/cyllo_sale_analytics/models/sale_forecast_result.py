# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import models, fields, api
import io
import json
import math
import datetime

import xlsxwriter


class SaleForecastResult(models.Model):
    _name = 'sale.forecast.result'
    _description = 'Sales Forecast Result Persistence'

    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, ondelete='cascade')
    params = fields.Text(string='Parameters JSON')
    results = fields.Text(string='Results JSON')

    @api.model
    def _save_forecast(self, params, results):
        existing = self.search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)
        ])

        def json_serial(obj):
            if isinstance(obj, (datetime.date, datetime.datetime)):
                return obj.isoformat()
            return str(obj)

        params_json = json.dumps(params, default=json_serial)
        results_json = json.dumps(results, default=json_serial)

        if existing:
            existing.write({
                'params': params_json,
                'results': results_json
            })
        else:
            self.create({
                'user_id': self.env.user.id,
                'company_id': self.env.company.id,
                'params': params_json,
                'results': results_json
            })

    @staticmethod
    def _xlsx_cell_value(val):
        """Coerce a value into something xlsxwriter can write safely.

        The Sale Orders / Order Lines tables come from pandas ``to_dict`` and may
        contain NaN/Inf floats or numpy scalars, which crash xlsxwriter. This
        normalises them (NaN/Inf -> '', numpy -> native, list/dict -> JSON)."""
        if val is None:
            return ''
        if isinstance(val, (list, dict)):
            return json.dumps(val, default=str)
        # numpy / pandas scalar -> native python scalar
        if hasattr(val, 'item') and not isinstance(val, (str, bytes)):
            try:
                val = val.item()
            except Exception:
                return str(val)
        if isinstance(val, float):
            if math.isnan(val) or math.isinf(val):
                return ''
            return val
        if isinstance(val, (int, bool, str)):
            return val
        return str(val)

    def build_multisheet_xlsx(self):
        """Build an XLSX workbook with every generated table on its own sheet
        (Main Dataset, Sale Orders, Order Lines). Returns the file bytes."""
        self.ensure_one()
        try:
            results = json.loads(self.results) if self.results else {}
        except Exception:
            results = {}

        sheets = [
            ('Main Dataset', results.get('dataset') or []),
            ('Sale Orders', results.get('sale_orders_table') or []),
            ('Order Lines', results.get('orderlines_table') or []),
        ]
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(
            output, {'in_memory': True, 'nan_inf_to_errors': True})
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#9ea700', 'font_color': '#ffffff', 'border': 1,
        })
        cell_fmt = workbook.add_format({'border': 1})
        col_labels = self.env['sale.order']._column_labels_for()
        wrote_any = False
        for sheet_name, rows in sheets:
            if not rows:
                continue
            wrote_any = True
            sheet = workbook.add_worksheet(sheet_name[:31])
            # Column order: union of keys, preserving first-row order then extras.
            columns = list(rows[0].keys())
            for row in rows:
                for key in row.keys():
                    if key not in columns:
                        columns.append(key)
            for col_idx, col in enumerate(columns):
                sheet.write(0, col_idx, col_labels.get(col, col), header_fmt)
            for row_idx, row in enumerate(rows, start=1):
                for col_idx, col in enumerate(columns):
                    sheet.write(row_idx, col_idx,
                                self._xlsx_cell_value(row.get(col)), cell_fmt)
        if not wrote_any:
            # Always produce at least one (empty) sheet so the file is valid.
            workbook.add_worksheet('Main Dataset')
        workbook.close()
        output.seek(0)
        return output.read()
