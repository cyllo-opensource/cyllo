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


class HrWorkEntryType(models.Model):
    """To inherit the field to make sure that the entry is for attendance"""
    _inherit = 'hr.work.entry.type'

    is_attendance = fields.Boolean(string='Attendance Entry', help='To choose entry for attendance')
    round_days = fields.Selection([('no', 'No Rounding'), ('half', 'Half Day'), ('full', 'Day')],
                                  string="Rounding", required=True, default='no',
                                  help="When the work entry is displayed in the payslip, the value is rounded "
                                       "accordingly.")
    round_type = fields.Selection([('closest', 'Closest'), ('down', 'Down'), ('up', 'UP')],
                                  help='Way of rounding work entry type', default='down')
    unpaid_structure_ids = fields.Many2many('employee.salary.structure',
                                            string="Unpaid in Structures Types",
                                            help="The work entry on the payslip does not result in any monetary "
                                                 "compensation for the employee.")