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

class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    is_zoom_meet = fields.Boolean(
        string='Zoom Meet',
        help='Create the calendar meeting with a Zoom Meet link.',
    )

    @api.onchange('activity_type_id')
    def _onchange_activity_type_id_zoom_meet(self):
        """A Zoom Meet is available only for meeting activities."""
        if self.activity_category != 'meeting':
            self.is_zoom_meet = False

    def action_create_calendar_event(self):
        """Pass the selected meeting provider to the calendar event form."""
        self.ensure_one()
        action = super().action_create_calendar_event()
        if self.is_zoom_meet:
            action['context'] = {
                **action.get('context', {}),
                'default_is_zoom_meet': True,
            }
        return action
