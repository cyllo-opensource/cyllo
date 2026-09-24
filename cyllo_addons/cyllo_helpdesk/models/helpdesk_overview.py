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
from datetime import datetime, timedelta

from odoo import api, fields, models


class HelpDeskOverview(models.TransientModel):
    _name = "helpdesk.overview"
    _description = "HelpDesk Overview"

    @api.model
    def _get_default_team(self):
        ticket = self.env['helpdesk.ticket'].search(
            [('user_id', '=', self.env.user.id), ('team_id', '!=', False)],
            order='date desc, id desc',
            limit=1,
        )
        team = ticket.team_id or self.env['helpdesk.team'].search([], limit=1)
        return team

    @api.model
    def _get_daily_target(self):
        today = fields.Date.today()
        team = self._get_default_team()
        domain = [
            ('date', '=', today),
            ('user_id', '=', self.env.user.id),
        ]
        if team:
            domain.append(('team_id', '=', team.id))
        else:
            domain.append(('team_id', '=', False))
        target = self.env['daily.target'].search(domain, limit=1)
        if not target:
            target = self.env['daily.target'].create({
                'date': today,
                'user_id': self.env.user.id,
                'team_id': team.id if team else False,
            })
        return target

    @api.model
    def _get_average_rating(self, date_from=False, date_to=False):
        domain = [
            ('res_model', '=', 'helpdesk.ticket'),
            ('consumed', '=', True),
            ('helpdesk_user_id', '=', self.env.user.id),
        ]
        if date_from:
            domain.append(('create_date', '>=', date_from))
        if date_to:
            domain.append(('create_date', '<=', date_to))
        ratings = self.env['rating.rating'].search(domain)
        if not ratings:
            return 0
        return round(sum(ratings.mapped('rating')) / len(ratings), 2)

    @api.model
    def get_overview_data(self):
        overview = self.env['helpdesk.ticket'].get_overview()
        today = fields.Date.today()
        start_today = datetime.combine(today, datetime.min.time())
        end_today = datetime.combine(today, datetime.max.time())
        last_seven_days = datetime.now() - timedelta(days=6)
        daily_target = self._get_daily_target()
        overview.update({
            'daily_target_id': daily_target.id,
            'daily_target_ticket_count': daily_target.ticket_count,
            'daily_target_success_rate': daily_target.success_rate,
            'daily_target_average_rating': daily_target.average_rating,
            'my_average_rating': self._get_average_rating(start_today, end_today),
            'my_last_seven_days_average_rating': self._get_average_rating(last_seven_days),
        })
        return overview

    @api.model
    def set_daily_target(self, field_name, value):
        allowed_fields = {
            'ticket_count': int,
            'success_rate': float,
            'average_rating': float,
        }
        if field_name not in allowed_fields:
            raise ValueError("Unsupported daily target field.")
        target = self._get_daily_target()
        cast_value = allowed_fields[field_name](value or 0)
        target.write({field_name: cast_value})
        return {
            'ticket_count': target.ticket_count,
            'success_rate': target.success_rate,
            'average_rating': target.average_rating,
        }
