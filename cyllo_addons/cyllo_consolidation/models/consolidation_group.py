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


class ConsolidationGroup(models.Model):
    """This model represents groups used for categorizing consolidation
    accounts within a consolidation chart."""
    _name = 'consolidation.group'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Account Group'
    _rec_name = 'view_name'

    name = fields.Char(
        string='Group Name', required=True, help='Name of the account group')
    view_name = fields.Char(
        string='Account Group', compute='_compute_view_name',
        help='Displayed name of the account group')
    chart_id = fields.Many2one(
        'consolidation.chart', string='Consolidation',
        help='Associated consolidation chart', required=True)
    group_id = fields.Many2one('consolidation.group', string='Parent',
                               help='Parent group of this account group')
    group_ids = fields.One2many(
        'consolidation.group', 'group_id', string='Children',
        help='Children groups under this group')
    account_ids = fields.One2many(
        'consolidation.account', 'group_id', string='Consolidation Accounts',
        help='Accounts associated with this group')

    def _compute_view_name(self):
        """This method constructs the view name for the account group based on
        its associated parent group and its own name."""
        for record in self:
            name = record.name
            group_id = record.group_id
            record.view_name = f'{group_id.name} /{name}' if group_id else name


    @api.constrains('group_id', 'chart_id')
    def _check_parent_group(self):
        """
        Ensures that if the 'group_id' is set, the 'chart_id' of the group must
        match the 'chart_id' of the current record.
        """
        if self.group_id and self.group_id.chart_id != self.chart_id:
            raise ValidationError(
                "The parent group's consolidation chart and the group's"
                " consolidation chart must be the same.")
        for rec in self.account_ids:
            if rec.chart_id != self.chart_id:
                raise ValidationError("The chart in the consolidation group and the consolidation accounts must be the same.")
