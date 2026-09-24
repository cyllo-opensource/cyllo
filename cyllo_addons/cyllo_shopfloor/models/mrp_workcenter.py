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
from odoo import models, api


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    @api.model
    def get_shopfloor_dashboard_metrics(self):
        """ Returns workorder counts grouped by workcenter and state. (Work center card view)"""
        workorders = self.env['mrp.workorder'].read_group(
            [('state', '!=', 'draft'), ('production_state', '!=', 'draft')],
            ['workcenter_id', 'state'],
            ['workcenter_id', 'state'],
            lazy=False
        )

        metrics = {}
        for wo in workorders:
            wc_id = wo.get('workcenter_id')
            if not wc_id:
                continue
            wc_id = wc_id[0]
            state = wo.get('state')
            count = wo.get('__count', 0)

            if wc_id not in metrics:
                metrics[wc_id] = {
                    'in_progress': 0,
                    'completed': 0,
                    'canceled': 0,
                    'total': 0
                }

            metrics[wc_id]['total'] += count
            if state in ('ready', 'progress', 'pending', 'waiting'):
                metrics[wc_id]['in_progress'] += count
            elif state == 'done':
                metrics[wc_id]['completed'] += count
            elif state == 'cancel':
                metrics[wc_id]['canceled'] += count

        return metrics
