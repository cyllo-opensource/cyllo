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
import xlsxwriter

from odoo import models, api


class TaxReportPrinting(models.AbstractModel):
    """
       This model is responsible for generating tax reports in various formats.
    """
    _name = 'report.cyllo_accounting.tax_report'
    _description = 'TaxReportPrinting'

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Retrieve the data required for generating the tax report.

        Args:
            docids: The document IDs.
            data (dict): Additional data for generating the report.

        Returns:
            dict: A dictionary containing the data required for generating the tax report.

        """
        period_data = data['period_data']
        filters = data['filters']
        args = data['args']

        report_data = self.env['tax.report'].get_report(args[0], args[1], **filters)
        return {
            'title': 'Tax Report',
            'report_data': report_data,
            'period_data': period_data,
            'report_name': data['report_name'],
            'filters': filters,
            'comparison': args,
        }

    @api.model
    def get_xlsx_report(self, data, response, report_name):
        """
            Generate an XLSX tax report.
            Args:
                data (str): JSON-encoded data required for report generation.
                response (obj): Response object for writing the report.
                report_name (str): Name of the report.
            Returns:
                None
        """
        arguments = json.loads(data)
        period_data = arguments['period_data']
        filters = arguments['filters']
        args = arguments['args']

        report_data = self.env['tax.report'].get_report(args[0], args[1], **filters)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        # Set up the formatting
        header_format = workbook.add_format({'bold': True, 'bg_color': '#808080', 'font_color': 'white', 'align': 'center'})
        subheader_format = workbook.add_format({'bold': True, 'bg_color': '#dfdfdf', 'align': 'left'})
        total_format = workbook.add_format({'bold': True, 'bg_color': '#fff0f0', 'align': 'left'})
        num_format = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
        filter_format = workbook.add_format({'align': 'center'})

        # worksheet.write(0, 1, 'Tax Report')
        worksheet.merge_range(0, 1, 2, 2, arguments['report_name'], workbook.add_format({'bold': True, 'bg_color': '#808080', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'font_size': 15}))

        # Write the filter header
        worksheet.set_column(1, 1, 18)
        worksheet.set_column(2, 2, 18)
        for col, filter in enumerate(['Date Range', 'Comparison', 'Options', 'Report']):
            worksheet.write(col + 4, 1, filter, header_format)

        # Write the filter information
        if int(args[0]) == 1:
            worksheet.write(4, 2, f"{filters['startDate']} to {filters['endDate']}", filter_format)
        elif int(args[0]) > 1:
            worksheet.write(5, 2, f"{args[1]}: {args[0]}", filter_format)
        worksheet.write(6, 2, ', '.join(filters['options']), filter_format)
        worksheet.write(7, 2, arguments['report_name'], filter_format)

        col = 1
        for period in period_data:
            worksheet.set_column(col, col+1, 18)
            worksheet.merge_range(9, col, 9, col + 1, period, header_format)
            worksheet.write(10, col, 'NET', header_format)
            worksheet.write(10, col + 1, 'TAX', header_format)
            col += 2

        row = 11
        worksheet.set_column(0, 0, 35)
        if report_data['report_type'] == 'generic':
            for data in report_data['report_data']:
                worksheet.write(row, 0, f"{'Sales' if data['key'] == 'sale' else 'Purchase'}", subheader_format)
                row += 1
                for value in data['values']:
                    worksheet.write(row, 0, value['display_name'])
                    col = 1
                    for val in value['values']:
                        worksheet.write(row, col, val['net'], num_format)
                        worksheet.write(row, col + 1, val['tax'], num_format)
                        col += 2
                    row += 1
                worksheet.write(row, 0, f"{'Sales' if data['key'] == 'sale' else 'Purchase'} Total", total_format)
                col = 1
                for total in data['totals']:
                    worksheet.write(row, col, total['net'], num_format)
                    worksheet.write(row, col + 1, total['tax'], num_format)
                    col += 2
                row += 2

        elif report_data['report_type'] == 'account':
            for data in report_data['report_data']:
                worksheet.write(row, 0, 'Sales' if data['key'] == 'sale' else 'Purchase', subheader_format)
                row += 1
                for line in data['data']:
                    worksheet.write(row, 0, line['account']['name'])
                    row += 1
                    for value in line['values']:
                        worksheet.write(row, 0, value['display_name'])
                        col = 1
                        for val in value['values']:
                            worksheet.write(row, col, val['net'], num_format)
                            worksheet.write(row, col + 1, val['tax'], num_format)
                            col += 2
                        row += 1
                worksheet.write(row, 0, f"{'Sales' if data['key'] == 'sale' else 'Purchase'} Total", total_format)
                col = 1
                for total in data['totals']:
                    worksheet.write(row, col, total['net'], num_format)
                    worksheet.write(row, col + 1, total['tax'], num_format)
                    col += 2
                row += 2

        elif report_data['report_type'] == 'tax':
            for data in report_data['report_data']:
                worksheet.write(row, 0, 'Sales' if data['key'] == 'sale' else 'Purchase', subheader_format)
                row += 1
                for line in data['data']:
                    worksheet.write(row, 0, line['display_name'])
                    row += 1
                    for value in line['values']:
                        worksheet.write(row, 0, value['account']['name'])
                        col = 1
                        for val in value['values']:
                            worksheet.write(row, col, val['net'], num_format)
                            worksheet.write(row, col + 1, val['tax'], num_format)
                            col += 2
                        row += 1
                worksheet.write(row, 0, f"{'Sales' if data['key'] == 'sale' else 'Purchase'} Total", total_format)
                col = 1
                for total in data['totals']:
                    worksheet.write(row, col, total['net'], num_format)
                    worksheet.write(row, col + 1, total['tax'], num_format)
                    col += 2
                row += 2

        # Save the workbook
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

