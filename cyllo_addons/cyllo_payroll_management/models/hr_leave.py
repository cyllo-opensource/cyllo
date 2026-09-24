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
import datetime
from datetime import date

from odoo import models


class HrLeave(models.Model):
    """To get the leave of the employee during the training period,
    based on that it changes the end date of the training"""
    _inherit = 'hr.leave'

    def action_validate(self):
        """The function is used to update the end date of the
        training period of the employee if the time off is approved """
        res = super(HrLeave, self).action_validate()
        contract_id = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id),
                                                      ('state', '=', 'training')], limit=1)
        # check valid contract and probation details.
        if contract_id and contract_id.employee_training_period_id:
            training_period_details = contract_id.employee_training_period_id
            number_of_days = 0
            time_off_details = []

            # calculating full day leaves and updating period :
            if (contract_id.state == "training" and
                    training_period_details and not self.request_unit_half and not self.request_unit_hours):
                date_from = date(self.request_date_from.year, self.request_date_from.month, self.request_date_from.day)
                date_to = date(self.request_date_to.year, self.request_date_to.month, self.request_date_to.day)
                if date_from >= training_period_details.start_date and date_to <= training_period_details.end_date:
                    updated_end_date = training_period_details.end_date + datetime.timedelta(
                        days=self.number_of_days_display)
                    time_off_details = []
                    for time in training_period_details.time_off_ids:
                        time_off_details.append(time.id)
                    time_off_details.append(self.id)
                    training_period_details.write({
                        'time_off_ids': time_off_details
                    })
                    contract_id.write({'date_end': updated_end_date})

            # updating period based on half day leave:
            elif (contract_id.state == "training"
                  and training_period_details and self.request_unit_half):
                date_from = date(self.request_date_from.year, self.request_date_from.month, self.request_date_from.day)
                if training_period_details.end_date >= date_from >= training_period_details.start_date:
                    updated_end_date = training_period_details.end_date + datetime.timedelta(days=number_of_days)
                    for leave in training_period_details.time_off_ids:
                        time_off_details.append(leave.id)
                    time_off_details.append(self.id)
                    training_period_details.write({
                        'time_off_ids': time_off_details
                    })
                    contract_id.write({'training_date_to': updated_end_date})
        return res
