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


class AccountAssetType(models.Model):
    """For Creating deferred revenue or expense type"""
    _name = "account.asset.type"
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _description = "Account Asset Type"

    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.company)
    name = fields.Char(string='Asset type', required=True, help='Name of the asset type')
    type = fields.Selection([('revenue', 'Deferred Revenue'), ('expense', 'Deferred Expense')],
                            compute='_compute_type', store=True, index=True, copy=True,
                            help='Type of asset: Deferred Revenue or Deferred Expense')
    active = fields.Boolean(default=True, help="Whether this asset type is active")
    journal_id = fields.Many2one('account.journal', required=True,
                                 domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
                                 help='Journal used for this asset type')
    computation_method = fields.Selection(selection=[('no_prorata', 'No Prorata'),
                                                     ('constant_period', 'Constant Period'),
                                                     ('daily_compute', 'Daily Computation')],
                                          required=True, default='no_prorata',
                                          help='Method used to compute depreciation entries')
    account_id = fields.Many2one('account.account', required=True,
                                 domain="[('company_id', '=', company_id)]",
                                 help='Account used for the asset value')
    expense_account_id = fields.Many2one('account.account', required=True,
                                         domain="[('company_id', '=', company_id)]",
                                         help='Account used for recognizing revenue or expense')
    number_of_entries = fields.Integer(string='Duration', default=6, required=True,
                                       help="Number of depreciation entries")
    period = fields.Selection([('1', 'Months'), ('12', 'Years')], default='1', required=True,
                              help="The time between the entries",)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)

    def copy_data(self, default=None):
        """ This method generates data for creating a copy of the record."""
        if default is None:
            default = {}
        default['name'] = self.name + _(' (copy)')
        return super().copy_data(default)

    @api.depends('name')
    @api.depends_context('type')
    def _compute_type(self):
        """Compute the asset type based on context.
        Sets the type field from context when creating new records
        if no type is already set.
        """
        for rec in self.filtered(lambda x: not x.type and 'type' in self.env.context):
            rec.type = self.env.context['type']
