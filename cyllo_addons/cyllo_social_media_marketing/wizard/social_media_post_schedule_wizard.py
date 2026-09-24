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


class SocialMediaPostScheduleWizard(models.TransientModel):
    _name = 'social.media.post.schedule.wizard'
    _description = 'Schedule a Social Media Post'

    post_id = fields.Many2one('social.media.post', required=True, default=lambda self: self.env.context.get('active_id'))
    scheduled_date = fields.Datetime(string="Scheduled Date", required=True,
                                     default=lambda self: fields.Datetime.now())

    def action_confirm(self):
        self.ensure_one()
        self.post_id.posted_date = self.scheduled_date
        result = self.post_id.action_schedule()
        if result:
            # action_schedule() returns a warning notification dict when the
            # date/platform selection is invalid - surface it instead of
            # silently closing the dialog as if scheduling had succeeded.
            return result
        return {'type': 'ir.actions.act_window_close'}
