# -*- coding: utf-8 -*-
#############################################################################
#
#   Cyllo Pvt. Ltd.
#
#   Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
#   Author: Cyllo(<https://www.cyllo.com>)
#
#   You can modify it under the terms of the GNU LESSER
#   GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#   You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#   (LGPL v3) along with this program.
#   If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models, fields, api


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    shopfloor_blocking_wo_id = fields.Many2one(
        'mrp.workorder',
        string="Currently Blocked By",
        compute='_compute_shopfloor_blocking_wo_id'
    )

    @api.depends('state', 'blocked_by_workorder_ids.state')
    def _compute_shopfloor_blocking_wo_id(self):
        """Get work order that is blocking the current WO if blocked """
        for wo in self:
            if wo.state == 'pending' and wo.blocked_by_workorder_ids:
                blocking_wos = wo.blocked_by_workorder_ids.filtered(
                    lambda w: w.state not in ('done', 'cancel')
                )
                wo.shopfloor_blocking_wo_id = blocking_wos[0].id if blocking_wos else False
            else:
                wo.shopfloor_blocking_wo_id = False

    def _update_shopfloor_view(self):
        """For updating state changes from shop floor"""
        for record in self:
            is_from_shopfloor = self.env.context.get('from_shopfloor', False)
            self.env['bus.bus']._sendone(
                'shopfloor_channel',
                'workorder_updated',
                {
                    'workcenter_id': record.workcenter_id.id,
                    'source': 'shopfloor' if is_from_shopfloor else 'backend'
                }
            )

    def button_start(self):
        """Override of button_start for assigning operator for work order from shop floor"""
        res = super().button_start()

        employee_id = self.env.context.get('employee_id')
        if employee_id:
            for wo in self:
                if wo.production_id:
                    wo.production_id.write({'employee_ids': [(4, employee_id)]})
        self._update_shopfloor_view()
        return res

    def button_pending(self):
        for wo in self:
            if getattr(wo.production_id, 'is_automated', False):
                active_timers = wo.time_ids.filtered(lambda t: not t.date_end)
                if active_timers:
                    active_timers.write({'date_end': fields.Datetime.now()})
        res = super().button_pending()
        self._update_shopfloor_view()
        return res

    def button_finish(self):
        """
        Extends workorder finish to notify shop floor and auto-close the MO when all operations are completed,
        especially when triggered from shop floor.
        """
        res = super().button_finish()

        for workorder in self:
            production = workorder.production_id
            if production and production.state not in ('done', 'cancel'):
                incomplete_workorders = production.workorder_ids.filtered(
                    lambda w: w.state not in ('done', 'cancel')
                )
                if not incomplete_workorders:
                    self._update_shopfloor_view()
                    if self.env.context.get('from_shopfloor'):
                        return {
                            'type': 'trigger_close_production',
                            'mo_id': production.id
                        }
        self._update_shopfloor_view()
        if self.env.context.get('from_shopfloor') and isinstance(res, dict) and res.get(
                'type') == 'ir.actions.act_window_close':
            return False

        return res

    def button_block(self):
        res = super().button_pending()
        self._update_shopfloor_view()
        return res

    def button_unblock(self):
        res = super().button_unblock()
        self._update_shopfloor_view()
        return res

    def action_show_shopfloor_worksheet(self):
        """For showing worksheet view on shop floor."""
        self.ensure_one()
        worksheet_view_id = self.env.ref('cyllo_shopfloor.view_shopfloor_worksheet_popup').id
        return {
            'name': f'Worksheet: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(worksheet_view_id, 'form')],
            'target': 'new',
        }

    def _compute_working_users(self):
        """
        Override of _compute_working_users for setting working users to WO started by cron job.
        so it will update the ui
        """
        super()._compute_working_users()

        for wo in self:
            if getattr(wo.production_id, 'is_automated', False) and wo.state == 'progress':
                has_active_timer = any(not t.date_end for t in wo.time_ids)
                wo.is_user_working = has_active_timer

    @api.model
    def _cron_finish_automated_workorders(self):
        """
        Evaluates running work orders. If an order belongs to an automated MO
        and has exceeded its expected duration, it is marked as finished.
        """
        running_wos = self.search([
            ('state', 'in', ['progress', 'ready']),
            ('production_id.is_automated', '=', True),
            ('duration_expected', '>', 0)
        ])
        now = fields.Datetime.now()
        for wo in running_wos:
            if wo.state == 'ready' and wo.production_id.date_start < now:
                wo.button_start()
                wo._update_shopfloor_view()
                continue

            if wo.state == 'progress':
                real_duration = 0.0

                for time_line in wo.time_ids:
                    if time_line.date_end:
                        real_duration += time_line.duration
                    elif time_line.date_start:
                        elapsed = now - time_line.date_start
                        real_duration += elapsed.total_seconds() / 60.0

                if real_duration >= wo.duration_expected:
                    wo.button_finish()
                    mo = wo.production_id
                    if mo.state == 'to_close':
                        mo.move_raw_ids.write({'picked': True})
                        if mo.product_id.tracking in ['lot', 'serial'] and not mo.lot_producing_id:
                            mo.action_generate_serial()
                        mo.button_mark_done()
                    elif mo.state == 'progress':
                        mo.workorder_ids.filtered(lambda w: w.state == 'ready')[:1].button_start()
