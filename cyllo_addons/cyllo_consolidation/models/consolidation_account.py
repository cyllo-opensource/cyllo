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
from odoo.exceptions import ValidationError


class ConsolidationAccount(models.Model):
    """This model handles the creation and management of consolidation
    accounts"""
    _name = 'consolidation.account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Consolidation Account'
    _check_company_auto = True
    _order = 'chart_id, name'

    name = fields.Char(string='Account Name', required=True,
                       help='Name of the consolidation account')
    view_name = fields.Char(
        string='Account Name', compute='_compute_view_name',
        help='Displayed name of the account')
    chart_id = fields.Many2one(
        'consolidation.chart', string='Consolidation', required=True,
        help='Select the consolidation chart associated with this account.')
    is_invert_sign = fields.Boolean(
        string='Invert Balance Sign', default=False,
        help='Check this if the balance sign should be inverted')
    group_id = fields.Many2one(
        'consolidation.group',
        help='Select the group associated with this consolidation account.',
        check_company=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        related='chart_id.company_id', store=True, readonly=True,
        help='Company this consolidation account belongs to')
    account_ids = fields.Many2many(
        'account.account', string="Accounts",
        help='Associated accounts from the same company or shared companies')

    @api.depends('name', 'group_id.view_name')
    def _compute_view_name(self):
        """Compute the displayed name of the account based on group and
         name."""
        for record in self:
            group_id = record.group_id
            name = record.name
            record.view_name = name
            if group_id and group_id.group_id:
                record.view_name = f'{group_id.view_name} /{name}'
            elif group_id:
                record.view_name = f'{group_id.name} /{name}'

    @api.constrains('group_id', 'chart_id')
    def _check_parent_group(self):
        """
        Ensures that if the 'group_id' is set, the 'chart_id' of the group must
        match the 'chart_id' of the current record.
        """
        if self.group_id and self.group_id.chart_id != self.chart_id:
            raise ValidationError(
                "The group's consolidation chart and the account's "
                "consolidation chart must be the same.")
