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


class FieldServiceRequestPrint(models.AbstractModel):
    """class to print form view"""
    _name = 'report.cyllo_field_service.report_field_service_request_form'
    _description = 'Field service request form report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """function to print form view"""
        field_service_request = self.env['field.service.request'].browse(docids)
        amount = sum(field_service_request.move_ids.filtered_domain(
            [('state', '=', 'posted')]).mapped('amount_total'))
        amount_due = sum(
            field_service_request.move_ids.filtered_domain(
                [('state', '=', 'posted')]).mapped('amount_residual'))
        paid_amount = amount - amount_due
        return {
            'fs_request': field_service_request,
            'amount': amount,
            'paid_amount': paid_amount,
            'balance_amount': amount_due
        }
