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
from odoo import api, models


class PlanAllocation(models.Model):
    """This module extends the `plan.allocation` model to automatically synchronize
       shifts with work entries in the HR module."""
    _inherit = "plan.allocation"

    @api.model_create_multi
    def create(self, vals_list):
        """Extend create to generate related work entries automatically."""
        records = super().create(vals_list)
        records._generate_related_work_entries()
        return records

    def write(self, vals):
        """Extend write to update related work entries automatically."""
        res = super().write(vals)
        self._generate_related_work_entries()
        return res

    def unlink(self):
        """Remove linked work entries when a shift is deleted."""
        self.env["hr.work.entry"].search([
            ("planning_allocation_id", "in", self.ids),
        ]).unlink()
        return super().unlink()

    def _generate_related_work_entries(self):
        """Generate or update work entries when a shift is created/updated."""
        hr_work_entry = self.env["hr.work.entry"]
        for rec in self:
            contract = rec.employee_id.contract_id
            if contract and contract.work_entry_source == "planning":
                work_entry = hr_work_entry.search([
                    ("planning_allocation_id", "=", rec.id),
                ], limit=1)
                vals = {
                    "name": f"Planning: {rec.name or rec.employee_id.name}",
                    "employee_id": rec.employee_id.id,
                    "contract_id": contract.id,
                    "date_start": rec.start_datetime,
                    "date_stop": rec.end_datetime,
                    "planning_allocation_id": rec.id,
                }
                if work_entry:
                    work_entry.write(vals)  # update instead of creating new
                else:
                    hr_work_entry.create(vals)
