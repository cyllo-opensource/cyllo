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


from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import timedelta


class TaxReturnWizard(models.TransientModel):
    """
    Tax Return Wizard

    This wizard:
    - Accepts date range + periodicity
    - Splits period automatically
    - Creates account.return records per period
    - Computes tax automatically
    """

    _name = 'tax.return.wizard'
    _description = 'Tax Return Wizard'

    periodicity = fields.Selection([('monthly', 'Monthly'),('bi_monthly', 'Every 2 months'),
                                    ('quarterly', 'Quarterly'),('four_months', 'Every 4 months'),
                                    ('semi_annually', 'Semi-annually'),('annually', 'Annually'),
                                    ('fiscal_year', 'Fiscal Year'),],string="Periodicity",required=True,
                                   default='monthly',help="Defines how tax returns should be grouped.")
    date_from = fields.Date(string="Start Date",required=True,help="Beginning of the overall period.")
    date_to = fields.Date(string="End Date",required=True,help="End of the overall period.",
                          default=fields.Datetime.today())
    journal_id = fields.Many2one('account.journal',string="Settlement Journal",
                                 domain="[('type','=','general')]",required=True,
                                 default=lambda self: self.env.ref('cyllo_accounting.journal_tax_returns',
                                                                   raise_if_not_found=False),
                                 help="Journal used to create settlement entries.")
    company_id = fields.Many2one('res.company',default=lambda self: self.env.company,required=True)

    @api.model
    def default_get(self, fields_list):
        """
        Load default values from Accounting Settings (ir.config_parameter)
        """
        res = super().default_get(fields_list)

        params = self.env['ir.config_parameter'].sudo()

        periodicity = params.get_param('cyllo_accounting.tax_return_periodicity')
        journal_id = params.get_param('cyllo_accounting.tax_return_journal_id')

        if periodicity:
            res['periodicity'] = periodicity

        if journal_id:
            res['journal_id'] = int(journal_id)

        return res
    def _generate_periods(self):
        """
        Split selected date range based on periodicity
        and return list of (date_from, date_to).
        """
        self.ensure_one()

        periods = []
        current_start = self.date_from

        # Determine grouping interval
        if self.periodicity == 'monthly':
            delta = relativedelta(months=1)
        elif self.periodicity == 'bi_monthly':
            delta = relativedelta(months=2)
        elif self.periodicity == 'quarterly':
            delta = relativedelta(months=3)
        elif self.periodicity == 'four_months':
            delta = relativedelta(months=4)
        elif self.periodicity == 'semi_annually':
            delta = relativedelta(months=6)
        elif self.periodicity == 'annually':
            delta = relativedelta(years=1)
        elif self.periodicity == 'fiscal_year':
            delta = relativedelta(years=1)
        else:
            delta = relativedelta(months=1)

        while current_start <= self.date_to:
            current_end = current_start + delta - timedelta(days=1)
            if current_end > self.date_to:
                current_end = self.date_to

            periods.append((current_start, current_end))
            current_start = current_end + timedelta(days=1)
        return periods

    # Apply

    def action_apply(self):
        """
        Create tax returns grouped by periodicity.
        """
        self.ensure_one()

        if self.date_from > self.date_to:
            raise UserError(_("Start date must be before end date."))

        periods = self._generate_periods()
        created_returns = []

        for start, end in periods:
            # Overlap check for better error message
            existing = self.env['account.return'].search([
                ('company_id', '=', self.company_id.id),
                ('state', '!=', 'cancel'),
                ('date_from', '<=', end),
                ('date_to', '>=', start),
            ])
            if existing:
                raise UserError(_("A Tax Return already exists for the period %s to %s.") % (start, end))

            record = self.env['account.return'].create({
                'name': _("Tax Return (%s to %s)") % (start, end),
                'periodicity': self.periodicity,
                'date_from': start,
                'date_to': end,
                'journal_id': self.journal_id.id,
                'company_id': self.company_id.id,
            })
            # Auto compute tax
            record.action_compute()

            # Create validation records from templates for this return
            template_checks = self.env['account.return.checks'].search([('company_id', '=', self.company_id.id)])
            for template in template_checks:
                validation = self.env['account.return.validation'].create({
                    'template_id': template.id,
                    'return_id': record.id,
                })
                # Run validation immediately
                validation.action_run_validation()

            created_returns.append(record.id)

        if not created_returns:
            return {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.act_window',
            'name': _('Tax Returns'),
            'res_model': 'account.return',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_returns)],
            'target': 'current',
        }