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


class HrPayrollStructureType(models.Model):
    _name = 'hr.payroll.structure.type'
    _inherit = ['hr.payroll.structure.type', 'mail.thread', 'mail.activity.mixin']

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    default_wage_type = fields.Selection([('hourly', 'Hourly Wage'), ('fixed', 'Monthly Fixed Wage')],
                                         help='To add the wage', default='fixed')
    default_schedule_pay = fields.Selection([('daily', 'Daily'), ('monthly', 'Monthly'), ('weekly', 'Weekly')],
                                            help='To add the schedule pay', default='monthly')
    default_work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', string='Default Work Entry', help='To add the work entry ',
        default=lambda self: self.env.ref('hr_work_entry.work_entry_type_attendance', raise_if_not_found=False))
