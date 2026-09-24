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
from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError


class CommissionPlanUser(models.Model):
    """Sales people commission plans"""
    _name = 'commission.plan.user'
    _description = 'Sales people who uses the commission plan'

    plan_id = fields.Many2one(comodel_name='commission.plan',
                              string="Commission Plan",
                              readonly=True, required=True, ondelete='cascade')
    user_id = fields.Many2one(comodel_name='res.users', string='Salesperson',
                              required=True,
                              domain="[('id','not in',assigned_users)]")
    assigned_users = fields.Many2many(comodel_name='res.users')
    date_from = fields.Date(string='From', required=True)
    date_to = fields.Date(string='To', required=True)
    other_plan_ids = fields.Many2many(string='Other Plans',
                                      comodel_name='commission.plan',
                                      compute='_compute_other_plan_ids', )

    @api.depends('user_id', 'plan_id')
    def _compute_other_plan_ids(self):
        """Compute other commission plans for the user that are not the current plan."""
        for record in self:
            record.other_plan_ids = []
            if record.plan_id and isinstance(record.plan_id.id, int):
                plans = self.env['commission.plan'].search([
                    ('id', '!=', record.plan_id.id), ('state', '=', 'approved'),
                    ('sales_people_user_ids', 'in', record.user_id.id),
                    ('duplicate_user_ids', 'not in', record.user_id.id),
                ])
                record.other_plan_ids = plans.ids

    @api.constrains('date_from', 'date_to', 'plan_id.date_from',
                    'plan_id.date_to')
    def _check_dates(self):
        """Ensure that the date range of the commission plan user is within the plan's date range."""
        for record in self:
            if record.date_from < record.plan_id.date_from or record.plan_id.date_to < record.date_to:
                raise ValidationError(
                    "The Sales peoples start date and end date should comes in plans start date and end date")
            elif record.date_to < record.date_from:
                raise ValidationError(
                    "The Sales peoples end date should be greater than start date")

    @api.constrains('plan_id', 'user_id', 'date_from', 'date_to')
    def _check_duplicate_user_with_overlap(self):
        """Ensure that same user does not have overlapping periods in the same commission plan."""
        for rec in self:
            overlaps = self.search([
                ('id', '!=', rec.id),
                ('plan_id', '=', rec.plan_id.id),
                ('user_id', '=', rec.user_id.id),
                ('date_from', '<=', rec.date_to),
                ('date_to', '>=', rec.date_from),
            ])
            if overlaps:
                raise ValidationError(
                    f"User {rec.user_id.name} already has an overlapping period in this commission plan."
                )

    @api.onchange('plan_id')
    def _onchange_plan_id(self):
        """Set the date_from field to the plan's date_from when the plan_id is changed."""
        if self.plan_id:
            self.date_from = self.plan_id.date_from

    @api.model
    def create(self, vals):
        """Override create method to link the plan to the user."""
        res = super().create(vals)
        if res.plan_id:
            res.user_id.plan_ids = [Command.link(res.plan_id.id)]
        return res

    def unlink(self):
        """Override unlink method to remove the plan from the user if no other links exist."""
        for rec in self:
            user = rec.user_id
            plan = rec.plan_id
            other_links = self.search_count([
                ('user_id', '=', user.id),
                ('plan_id', '=', plan.id),
                ('id', '!=', rec.id),
            ])
            if other_links == 0:
                user.plan_ids = [Command.unlink(plan.id)]
        return super().unlink()
