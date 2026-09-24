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
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    """Extends res.config.settings model to customize form views."""
    _inherit = "res.config.settings"

    # currency auto update fields
    enable_currency_update = fields.Boolean(
        string='Automatic Currency Rate Update',
        related='company_id.enable_currency_update',
        readonly=False
    )

    currency_update_interval = fields.Selection([
        ('manual', 'Manual'),
        ('days', 'Daily'),
        ('weeks', 'Weekly'),
        ('months', 'Monthly')
    ],
        string='Update Interval',
        related='company_id.currency_update_interval',
        readonly=False
    )

    currency_update_service = fields.Selection([
        ('erapi', 'ExchangeRate-API'),
        ('ecb', 'European Central Bank'),
        ('fixer', 'Fixer-API')
    ],
        string='Service',
        related='company_id.currency_update_service',
        readonly=False
    )

    fixer_api_key = fields.Char(
        string='Fixer API-key',
        related='company_id.fixer_api_key',
        readonly=False
    )

    currency_next_execution_date = fields.Datetime(
        string='Next Execution',
        compute='_compute_currency_next_execution_date',
        inverse='_inverse_currency_next_execution_date',
        readonly=False
    )

    currency_cron_id = fields.Many2one(
        'ir.cron',
        string='Currency Update Cron',
        related='company_id.currency_cron_id',
        readonly=False
    )

    @api.depends('company_id.currency_next_execution_date')
    def _compute_currency_next_execution_date(self):
        """Get next execution date from company and assign value to currency_next_execution_date"""
        for rec in self:
            if rec.company_id:
                rec.currency_next_execution_date = rec.company_id.currency_next_execution_date
            else:
                # Default values when no cron exists
                rec.currency_next_execution_date = False

    def _inverse_currency_next_execution_date(self):
        """Assign changed currency_next_execution_date to
         company currency_next_execution_date field"""
        for rec in self:
            if rec.company_id.currency_cron_id:
                rec.company_id.currency_cron_id.nextcall = rec.currency_next_execution_date

    def set_values(self):
        """Override set values to create/update cron after saving"""
        res = super().set_values()
        self.company_id._update_currency_cron()
        return res

    def action_update_currency_rates_now(self):
        """Manual update button action - reuses the same cron function"""
        self.ensure_one()

        # Get currencies count before update
        currencies = self.env['res.currency'].search([
            ('active', '=', True),
            ('id', '!=', self.env.company.currency_id.id)
        ])

        if not currencies:
            raise UserError(_('No active currencies found to update.'))

        # Call the same function used by scheduled action
        result = self.env['res.currency'].update_currency_rates(
            self.env.company.id)

        # Show notification
        if result:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Currency Rates Updated'),
                    'message': _(
                        'Currency rates have been updated successfully.'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Update Failed'),
                    'message': _('Failed to update currency rates.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
