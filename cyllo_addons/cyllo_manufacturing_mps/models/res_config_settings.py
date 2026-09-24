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
from odoo import Command, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_mps = fields.Boolean(
        config_parameter='cyllo_manufacturing_mps.is_mps',
        help='Turn on the MPS scheduler and related automation settings.',
    )

    mps_default_timerange = fields.Selection(
        [
            ('day', 'Daily'),
            ('week', 'Weekly'),
            ('month', 'Monthly'),
            ('year', 'Yearly')
        ],
        config_parameter='cyllo_manufacturing_mps.default_timerange',
        default='month',
        help='Select the planning period used by the MPS board and automated cron.',

    )

    def set_values(self):
        super().set_values()

        self._update_cron()
        self._update_user_group()

    def _update_cron(self):
        cron = self.env.ref('cyllo_manufacturing_mps.ir_cron_mps_automate_orders', raise_if_not_found=False)
        if not cron:
            return

        cron.active = self.is_mps

        interval_map = {
            'day': ('days', 1),
            'week': ('weeks', 1),
            'month': ('months', 1),
            'year': ('months', 12),
        }

        if self.mps_default_timerange in interval_map:
            interval_type, interval_number = interval_map[self.mps_default_timerange]
            cron.write({
                'interval_type': interval_type,
                'interval_number': interval_number,
            })

    def _update_user_group(self):
        group = self.env.ref('cyllo_manufacturing_mps.group_mps_enabled')
        manager_group = self.env.ref('mrp.group_mrp_manager', raise_if_not_found=False)
        if not manager_group:
            return
        group.users = (
            [Command.set(manager_group.users.ids)] if self.is_mps else [Command.clear()]
        )
