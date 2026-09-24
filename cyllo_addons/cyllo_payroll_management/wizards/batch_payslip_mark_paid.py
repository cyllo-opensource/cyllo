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


class BatchPayslipMarkPaid(models.Model):
    _name = 'batch.payslip.mark.paid'
    _description = "Mark batch payslip paid"

    def action_paid(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            batch_payslip_id = self.env['employee.payslip.batch'].browse(active_id)
            batch_payslip_id.write({'state': 'paid'})
            batch_payslip_id.employee_payslip_ids.action_paid()