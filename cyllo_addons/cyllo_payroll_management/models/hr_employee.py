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


class HrEmployee(models.Model):
    """To add understand the employee which is resigned"""
    _inherit = 'hr.employee'

    is_resigned = fields.Boolean(string='Resigned', help='To check if the employee has resigned or not')
    payslip_count = fields.Integer(compute='_compute_payslip_count', help='Total number of payslip for the employee')
    payslip_ids = fields.One2many('employee.payslip', 'employee_id', string='Payslips', help='Payslips related to this employee')

    def _compute_payslip_count(self):
        """Compute the number of payslips generated for each employee"""
        for record in self:
            record.payslip_count = self.env['employee.payslip'].sudo().search_count([('employee_id', '=', record.id)])

    def action_view_payslip(self):
        """To view corresponding payslip of the employee"""
        return {
            'name': 'Payslip',
            'view_mode': 'tree,form',
            'res_model': 'employee.payslip',
            'type': 'ir.actions.act_window',
            'domain': [('employee_id', '=', self.id)],
        }

    @api.model
    def update_employee_state(self):
        """Method to update employee state based on resignation data."""
        today = fields.Date.today()
        resignations_to_update = self.env['employee.resignation'].sudo().search(
            [('leaving_date', '<=', today), ('state', '=', 'approved')])
        for resignation in resignations_to_update:
            resignation.employee_id.write({'active': False})

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    is_resigned = fields.Boolean(string='Resigned', readonly=True)
