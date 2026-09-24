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
from odoo import api, fields, models


class ResCompany(models.Model):
    """inherit res.company model to store fields related to auto currency rates"""
    _inherit = 'res.company'

    # Currency update settings
    enable_currency_update = fields.Boolean(
        string='Enable Auto Currency Update',
        default=False
    )

    currency_update_interval = fields.Selection([
        ('manual', 'Manual'),
        ('days', 'Daily'),
        ('weeks', 'Weekly'),
        ('months', 'Monthly')
    ],
        string='Update Interval Type',
        compute='_compute_currency_update_interval',
        inverse='_inverse_currency_update_interval',
        store=True
    )

    currency_update_service = fields.Selection([
        ('erapi', 'ExchangeRate-API'),
        ('ecb', 'European Central Bank'),
        ('fixer', 'Fixer-API')
    ],
        string='Service', default='erapi',
    )

    fixer_api_key = fields.Char(string='Fixer API-key')

    currency_next_execution_date = fields.Datetime(
        string='Next Execution',
        related='currency_cron_id.nextcall',
    )

    currency_cron_id = fields.Many2one(
        'ir.cron',
        string='Scheduled Action',
        readonly=True,
        copy=False
    )

    @api.depends('currency_cron_id.interval_type')
    def _compute_currency_update_interval(self):
        """Get interval_type from cron and assign it to currency_update_interval"""
        for company in self:
            if company.currency_cron_id:
                company.currency_update_interval = company.currency_cron_id.interval_type
            else:
                # Default values when no cron exists
                company.currency_update_interval = 'manual'

    def _inverse_currency_update_interval(self):
        """Allow manual editing of currency_update_interval from config settings"""
        for company in self:
            pass  # or save it somewhere else if needed

    def _update_currency_cron(self):
        """Create or update scheduled action for currency updates"""
        self.ensure_one()
        if not self.enable_currency_update or self.currency_update_interval == 'manual':
            # Disable cron if exists
            if self.currency_cron_id:
                self.currency_cron_id.active = False
            return

        cron_vals = {
            'name': f'Currency Rate Update - {self.name}',
            'model_id': self.env['ir.model']._get('res.currency').id,
            'state': 'code',
            'code': f'model.update_currency_rates({self.id})',
            'interval_number': 1,
            'interval_type': self.currency_update_interval,
            'numbercall': -1,
            'active': True,
            'doall': False,
            'user_id': self.env.ref('base.user_admin').id,
        }

        if self.currency_cron_id:
            self.currency_cron_id.write(cron_vals)
        else:
            cron = self.env['ir.cron'].sudo().create(cron_vals)
            self.currency_cron_id = cron.id
