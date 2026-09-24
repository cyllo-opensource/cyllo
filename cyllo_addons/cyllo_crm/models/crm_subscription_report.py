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
import base64
from datetime import datetime, timedelta
from io import BytesIO

import xlsxwriter
from odoo import api, fields, models


def _get_next_execution_date(frequency):
    """To get the next execution date for the cron job, based on the frequency passed"""
    if frequency == 'weekly':
        return datetime.now() + timedelta(days=7)
    elif frequency == 'monthly':
        return datetime.now() + timedelta(days=30)
    elif frequency == 'yearly':
        return datetime.now() + timedelta(days=365)
    return datetime.now() + timedelta(days=7)


def _get_interval(frequency):
    """To get the Interval for the cron job, based on the frequency passed"""
    if frequency == 'weekly':
        return 'weeks', 1
    elif frequency == 'monthly':
        return 'months', 1
    elif frequency == 'yearly':
        return 'months', 12
    else:
        return 'days', 7  # default fallback


class CrmSubscriptionReport(models.Model):
    """ This model represents CRM Subscription Report."""
    _name = 'crm.subscription.report'
    _description = 'CRM Subscription Report'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(default=True)
    frequency = fields.Selection(selection=[
        ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('yearly', 'Yearly')
    ], required=True, copy=False,
        help="Choose how frequently you would like to receive the report.")

    lead_fields = fields.Many2many(
        comodel_name='ir.model.fields',
        relation='crm_subscription_report_fields_rel',
        column1='report_id',
        column2='field_id',
        domain="""[
                ('model', '=', 'crm.lead'), 
                ('name', 'in', [
                    'id','name','contact_name',
                    'partner_id','user_id','team_id',
                    'type','stage_id','priority',
                    'source_id','medium_id','referred',
                    'expected_revenue','prorated_revenue','recurring_revenue',
                    'recurring_revenue_monthly','recurring_revenue_prorated',
                    'recurring_revenue_monthly_prorated',
                    'probability',
                    'date_open','date_last_stage_update','date_closed',
                  ]),
            ]""",
        string="Report Fields",
        help="Select the fields from the Lead/Opportunity model to include in the report. "
             "The order in which you select the fields will be preserved and used as the column order in the final report.",
        required=True,
        default=lambda self: self.env['ir.model.fields'].search([
            ('model', '=', 'crm.lead'),
            ('name', 'in', [
                'id', 'name',
                'user_id', 'team_id', 'type',
            ])
        ])
    )
    rule_to_apply = fields.Char(string="Rule",
                                help="Set Rules to filter the records")

    company_id = fields.Many2one('res.company', store=True, copy=False,
                                 string="Company",
                                 default=lambda
                                     self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  related='company_id.currency_id',
                                  default=lambda
                                      self: self.env.user.company_id.currency_id.id)
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.context.get('user_id', self.env.user.id),
        index=True,
    )
    _sql_constraints = [
        ('report_name', 'unique(name)', 'Name already exist')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Override create function to create cron job along with it"""
        records = super().create(vals_list)
        for record in records:
            nextcall = _get_next_execution_date(record.frequency)
            interval_type, interval_number = _get_interval(
                record.frequency)

            self.env['ir.cron'].create({
                'name': f"Report - {record.name}",
                'model_id': self.env.ref(
                    'cyllo_crm.model_crm_subscription_report').id,
                'state': 'code',
                'code': f"env['crm.subscription.report'].send_report_email({record.id})",
                'interval_number': interval_number,
                'interval_type': interval_type,
                'numbercall': -1,
                'nextcall': nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': record.user_id.id,
                'ref_model_id': record.id
            })
        return records

    def write(self, vals):
        """Override write function to change the created cron job to change the frequency of the frequency is changed"""
        res = super().write(vals)

        if 'frequency' in vals or 'name' in vals:
            for record in self:
                # Get updated values or fallback to current values
                frequency = vals.get('frequency', record.frequency)
                name = vals.get('name', record.name)
                cron_model = self.env['ir.cron'].search([
                    ('ref_model_id', '=', record.id)
                ])

                if cron_model:
                    update_vals = {
                        'name': f"Report - {name}",
                    }

                    if 'frequency' in vals:
                        nextcall = _get_next_execution_date(frequency)
                        interval_type, interval_number = _get_interval(
                            frequency)
                        update_vals.update({
                            'code': f"env['crm.subscription.report'].send_report_email({record.id})",
                            'interval_number': interval_number,
                            'interval_type': interval_type,
                            'numbercall': -1,
                            'nextcall': nextcall.strftime('%Y-%m-%d %H:%M:%S'),
                        })

                    cron_model.write(update_vals)

        return res

    def send_report_email(self, model_id):
        """Email sending function along with the attached xml of the report"""
        file_data = self.get_xlsx_report(model_id)
        model_id = self.env['crm.subscription.report'].browse(model_id)

        # Step 5: Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'{model_id.name}_report.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'res_model': 'crm.subscription.report',
            'res_id': model_id.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        template = self.env.ref(
            'cyllo_crm.crm_subscription_report_email_template')
        template.send_mail(
            model_id.id,
            force_send=True,
            email_values={'attachment_ids': [(4, attachment.id)]})

    def get_xlsx_report(self, model_id):
        """Create xml report for the subscription report"""
        report_rule = self.browse(model_id)
        corn_job = self.env['ir.cron'].search([('ref_model_id', '=', model_id)])
        last_call = corn_job.lastcall
        next_call = corn_job.nextcall
        last_call_str = last_call.strftime(
            "%Y-%m-%d %H:%M:%S") if last_call else None
        next_call_str = next_call.strftime(
            "%Y-%m-%d %H:%M:%S") if next_call else None
        report_domain = eval(report_rule.rule_to_apply or '[]')
        # for the first time run of cron job there is no last call date so it will take all the leads from the beginning of time to scheduled date
        # Afterwards it will take leads from last call date to scheduled date
        if not last_call:
            domain = report_domain + [('write_date', '<=', next_call_str)]
        else:
            domain = report_domain + [('write_date', '>=', last_call_str),
                                  ('write_date', '<=', next_call_str)]
        self.env.cr.execute("""
                select field_id from crm_subscription_report_fields_rel WHERE report_id = %s
                """, (report_rule.id,))
        heads = [row[0] for row in self.env.cr.fetchall()]
        report_fields = self.env['ir.model.fields'].browse(heads)
        leads = self.env['crm.lead'].search(domain, order='id')
        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        worksheet = workbook.add_worksheet()

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 28,
            'align': 'center',
            'valign': 'vcenter',
        })

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',  # Light gray background
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })

        cell_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
        })
        created_format = workbook.add_format({
            'italic': True,
            'font_size': 10,
            'align': 'center',
            'valign': 'vcenter',
        })

        start_row = 9  # Row 10 in Excel
        start_col = 2  # Column C in Excel
        num_columns = len(report_fields)
        title_row = start_row - 4
        info_row = start_row - 3
        worksheet.set_row(title_row, 30)

        worksheet.merge_range(title_row, start_col, title_row,
                              start_col + num_columns - 1, report_rule.name,
                              title_format)
        worksheet.merge_range(
            info_row, start_col,
            info_row, start_col + num_columns - 1,
            f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            created_format
        )

        col_width = [len(field.field_description) for field in report_fields]

        # Header row starting at C10
        for col, field in enumerate(report_fields):
            worksheet.write(start_row, start_col + col, field.field_description,
                            header_format)

        # Data rows starting at row below header (row 11)
        for row_num, lead in enumerate(leads, start=start_row + 1):
            for col_num, field in enumerate(report_fields):
                val = getattr(lead, field.name, False)
                if not val:
                    if field.ttype in ('float', 'integer', 'monetary'):
                        val = 0.0
                    else:
                        val = 'NULL'
                elif isinstance(val, models.BaseModel):
                    val = val.name
                elif field.ttype == 'datetime' and isinstance(val,
                                                              datetime):
                    val = val.strftime('%Y-%m-%d')  # Extract only the date
                col_width[col_num] = max(col_width[col_num], len(str(val)))
                worksheet.write(row_num, start_col + col_num, str(val),
                                cell_format)

        for col_num, width in enumerate(col_width):
            worksheet.set_column(start_col + col_num, start_col + col_num,
                                 width + 2)

        workbook.close()
        buffer.seek(0)
        file_data = buffer.read()
        return file_data




class IrCron(models.Model):
    """Inherit add a field for subscription Report"""
    _inherit = 'ir.cron'

    ref_model_id = fields.Many2one('crm.subscription.report',
                                   string="Reference Model",
                                   ondelete='cascade')
