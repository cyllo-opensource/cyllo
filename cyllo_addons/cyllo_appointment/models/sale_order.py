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
import logging
from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    appointment_ids = fields.One2many(
        'appointment.appointment', 'sale_order_id', string='Appointments'
    )
    appointment_count = fields.Integer(
        string='Appointments', compute='_compute_appointment_count'
    )

    @api.depends('appointment_ids')
    def _compute_appointment_count(self):
        for order in self:
            order.appointment_count = len(order.appointment_ids)

    def action_view_appointments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Appointments',
            'res_model': 'appointment.appointment',
            'view_mode': 'tree,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'create': False,},
        }

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            if not order.sudo().appointment_ids:
                continue
            pending = order.appointment_ids.filtered(
                lambda a: a.state == 'pending_payment'
            )
            for appt in pending:
                if appt.partner_id and order.partner_id != appt.partner_id:
                    order.sudo().write({'partner_id': appt.partner_id.id})
                try:
                    appt.action_confirm()
                except Exception as e:
                    _logger.warning(
                        'Failed to confirm appointment %s: %s',
                        appt.name, str(e)
                    )
        return res
