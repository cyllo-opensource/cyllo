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
from odoo import fields, models


class HrWorkEntry(models.Model):
    """Inherits hr.work.entry model to link work entries with planning allocations."""
    _inherit = "hr.work.entry"

    planning_allocation_id = fields.Many2one(
        "plan.allocation",
        string="Planning Allocation",
        groups="hr.group_hr_user",
    )

    def create(self, vals_list):
        """Extend work entry creation to also generate worked days
        when entries are based on planning allocations.
        """
        records = super().create(vals_list)
        worked_days = self.env["employee.worked.days"]
        for rec in records:
            if rec.planning_allocation_id:
                alloc = rec.planning_allocation_id
                contract = rec.contract_id

                # Find payslip covering allocation period
                payslip = self.env["employee.payslip"].search([
                    ("employee_id", "=", contract.employee_id.id),
                    ("start_date", "<=", alloc.start_datetime),
                    ("to_date", ">=", alloc.end_datetime),
                ], limit=1)
                hours = (alloc.end_datetime - alloc.start_datetime).total_seconds() / 3600
                days = (alloc.end_datetime.date() - alloc.start_datetime.date()).days + 1
                amount = worked_days._compute_amount()
                # Create worked days line
                worked_days.create({
                    "type": alloc.allocation_type_id.name,
                    "days": days,
                    "hour": hours,
                    "contract_id": contract.id,
                    "employee_payslip_id": payslip.id if payslip else False,
                    "work_entry_type_id": rec.work_entry_type_id.id,
                    "amount": amount,
                })
        return records

    def _get_duration_batch(self):
        """Compute duration for work entries using company calendar hours/day logic."""
        result = {}
        calendar = self.env.company.resource_calendar_id
        hours_per_day = calendar.hours_per_day if calendar else 12

        for work_entry in self:
            date_start = work_entry.date_start
            date_stop = work_entry.date_stop

            if not date_start or not date_stop or date_stop < date_start:
                result[work_entry.id] = 0.0
                continue

            if date_start.date() == date_stop.date():
                duration = (date_stop - date_start).total_seconds() / 3600
                duration = round(min(duration, hours_per_day), 2)
            else:
                days = (date_stop.date() - date_start.date()).days + 1
                duration = round(days * hours_per_day, 2)

            result[work_entry.id] = duration

        return result
