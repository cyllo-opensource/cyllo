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
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    """Extension of Repair Order to track operators and exact working durations."""
    _inherit = 'repair.order'

    operator_ids = fields.Many2many(
        comodel_name='hr.employee',
        string="Operators"
    )
    current_start_time = fields.Datetime(
        string="Current Session Start",
        copy=False
    )
    total_accumulated_time = fields.Float(
        string="Accumulated Time (Hours)",
        default=0.0,
        copy=False
    )
    is_timer_running = fields.Boolean(
        string="Timer is Running",
        default=False,
        copy=False
    )
    actual_duration = fields.Float(
        string="Actual Duration (Hours)",
        compute="_compute_actual_duration"
    )
    allocation_policy_id = fields.Many2one(
        comodel_name='repair.time.allocation.policy',
        string="Time Allocation Policy",
        compute="_compute_allocation_policy",
        store=True,
    )
    allocated_duration = fields.Float(
        string="Allocated Duration (Hours)",
        compute="_compute_allocated_duration",
        store=True,
        readonly=False
    )
    progress_percentage = fields.Float(
        string="Progress (%)",
        compute="_compute_time_progress"
    )
    time_status = fields.Selection([
        ('on_track', 'On Track'),
        ('warning', 'Warning'),
        ('overdue', 'Overdue')
    ], string="Time Status", compute="_compute_time_progress")

    @api.depends('product_id')
    def _compute_allocation_policy(self):
        """Compute applicable repair time allocation policy based on product or category."""
        for rec in self:
            domain = [('active', '=', True)]
            if rec.product_id:
                domain_product = domain + [
                    '|', '&', ('target_type', '=', 'product'), ('product_id', '=', rec.product_id.id),
                    '&', ('target_type', '=', 'category'),
                    ('product_category_id', 'parent_of', rec.product_id.categ_id.id)
                ]
                policy = self.env['repair.time.allocation.policy'].search(domain_product, order='sequence, id', limit=1)
                rec.allocation_policy_id = policy
            else:
                rec.allocation_policy_id = False

    @api.depends('allocation_policy_id')
    def _compute_allocated_duration(self):
        """Set allocated duration from selected allocation policy."""
        for rec in self:
            if rec.allocation_policy_id:
                rec.allocated_duration = rec.allocation_policy_id.allocated_duration
            elif not rec.allocated_duration:
                rec.allocated_duration = 0.0

    @api.depends('actual_duration', 'allocated_duration')
    def _compute_time_progress(self):
        """Calculate repair progress percentage and time status."""
        for rec in self:
            if rec.allocated_duration > 0:
                progress = (rec.actual_duration / rec.allocated_duration) * 100
                rec.progress_percentage = min(100.0, progress)
                if progress < 80:
                    rec.time_status = 'on_track'
                elif progress <= 100:
                    rec.time_status = 'warning'
                else:
                    rec.time_status = 'overdue'
            else:
                rec.progress_percentage = 0.0
                rec.time_status = False

    @api.depends('current_start_time', 'total_accumulated_time', 'is_timer_running')
    def _compute_actual_duration(self):
        """Calculates total time dynamically even while the timer is running."""
        for rec in self:
            if rec.is_timer_running and rec.current_start_time:
                delta = fields.Datetime.now() - rec.current_start_time
                session_hours = delta.total_seconds() / 3600.0
                rec.actual_duration = rec.total_accumulated_time + session_hours
            else:
                rec.actual_duration = rec.total_accumulated_time

    def action_repair_start(self):
        """Start repair and enforce maximum active repairs per operator."""
        limit = int(self.env['ir.config_parameter'].sudo().get_param('repair.max_active_orders',default=0))
        if limit > 0:
            for repair in self:
                for operator in repair.operator_ids:
                    running_count = self.env['repair.order'].search_count([
                        ('is_timer_running', '=', True),
                        ('operator_ids', 'in', operator.id),
                        ('id', '!=', repair.id),
                    ])
                    if running_count >= limit:
                        raise UserError(
                            f"Operator '{operator.name}' has reached the "
                            f"maximum limit of {limit} active repairs."
                        )
        records_to_start = self.filtered(lambda rec: rec.state != 'under_repair')
        res = super(RepairOrder, records_to_start).action_repair_start() if records_to_start else True
        self.write({
            'current_start_time': fields.Datetime.now(),
            'is_timer_running': True,
        })
        return res

    def action_repair_pause(self):
        """Custom action to pause the timer without ending the repair."""
        for rec in self:
            if rec.is_timer_running and rec.current_start_time:
                delta = fields.Datetime.now() - rec.current_start_time
                session_hours = delta.total_seconds() / 3600.0
                rec.write({
                    'total_accumulated_time': rec.total_accumulated_time + session_hours,
                    'current_start_time': False,
                    'is_timer_running': False
                })
        return True

    def action_repair_end(self):
        """Overrides native end action to stop the timer and finalize duration."""
        for rec in self:
            if rec.is_timer_running and rec.current_start_time:
                delta = fields.Datetime.now() - rec.current_start_time
                session_hours = delta.total_seconds() / 3600.0
                rec.write({
                    'total_accumulated_time': rec.total_accumulated_time + session_hours,
                    'current_start_time': False,
                    'is_timer_running': False
                })
        res = super().action_repair_end()
        return res
