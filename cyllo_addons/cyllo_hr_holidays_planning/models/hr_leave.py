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
from odoo import models


class HrLeave(models.Model):
    """Inherited model for hr.leave with additional methods"""
    _inherit = 'hr.leave'

    def action_approve(self):
        """Extends the approval function to generate planning if the planning
         allocation is set to time-off type."""
        res = super().action_approve()
        for record in self:
            allocation_type = record.holiday_status_id.planning_allocation_type_id
            if allocation_type and record.holiday_type == 'employee':
                self.env['plan.allocation'].create(
                    [{'allocation_type_id': allocation_type.id,
                      'employee_id': employee.id,
                      'start_datetime': record.date_from,
                      'end_datetime': record.date_to,
                      'leave_id': record.id} for employee in
                     record.employee_ids])
        return res

    def action_refuse(self):
        """Extends the refuse function to delete corresponding planning."""
        res = super().action_refuse()
        self.env['plan.allocation'].search(
            [('leave_id', 'in', self.ids)]).unlink()
        return res
