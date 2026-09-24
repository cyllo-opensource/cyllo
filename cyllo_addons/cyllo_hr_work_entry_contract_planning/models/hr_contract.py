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


class HrContract(models.Model):
    """Inherit hr.contract to extend work entry generation logic."""
    _inherit = "hr.contract"

    work_entry_source = fields.Selection(
        selection_add=[("planning", "Planning")],
        ondelete={"planning": "set default"},
    )

    def _get_work_entries_values(self, date_start, date_stop):
        """Extend work entry generation to include Planning allocations. """
        contract_vals = []
        for contract in self:
            if contract.work_entry_source == "planning":
                allocations = self.env["plan.allocation"].search([
                    ("employee_id", "=", contract.employee_id.id),
                    ("start_datetime", "<", date_stop),
                    ("end_datetime", ">", date_start),
                ])
                for alloc in allocations:
                    # Check if a work entry already exists for this allocation
                    existing_entry = self.env["hr.work.entry"].search([
                        ("planning_allocation_id", "=", alloc.id),
                        ("contract_id", "=", contract.id),
                    ], limit=1)

                    if not existing_entry:
                        contract_vals.append({
                            "name": f"Planning: {alloc.name or contract.employee_id.name}",
                            "employee_id": contract.employee_id.id,
                            "contract_id": contract.id,
                            "date_start": alloc.start_datetime,
                            "date_stop": alloc.end_datetime,
                            "planning_allocation_id": alloc.id,
                        })
            else:
                contract_vals += super(HrContract, contract)._get_work_entries_values(
                    date_start, date_stop
                )
        return contract_vals
