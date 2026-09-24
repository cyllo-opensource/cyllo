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


class ResignationRequestConfirm(models.Model):
    """The model is used to perform the functions
     when an employee confirm the resignation request"""
    _name = 'resignation.request.confirm'
    _description = 'Resignation Request Confirm'

    employee_id = fields.Many2one('hr.employee', help='To choose the employee',
                                  default=lambda self: self.env.user.employee_id.id)
    reference = fields.Char(help='To get the reference of the request', readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', required=True)

    def action_confirm_resignation(self):
        """The function is used to confirm the employee resignation request,
         if yes an email send to the department manager"""
        if self.employee_id:
            self.employee_id.is_resigned = True
        request = self.env['employee.resignation'].sudo().search([('reference', '=', self.reference)])
        for rec in request:
            rec.write({
                'confirmed_date': fields.datetime.now(),
                'state': 'confirm'
            })
