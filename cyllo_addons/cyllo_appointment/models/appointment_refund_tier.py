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
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AppointmentRefundTier(models.Model):
    _name = 'appointment.refund.tier'
    _description = 'Appointment Refund Tier'
    _order = 'hours_before desc'

    appointment_type_id = fields.Many2one(
        'appointment.type', string='Appointment Type',
        required=True, ondelete='cascade'
    )
    name = fields.Char(string='Label', required=True,
                       help='e.g. "Full Refund", "50% Refund"')
    hours_before = fields.Float(
        string='Cancelled More Than (hours before)',
        required=True,
        help='This tier applies if cancellation happens this many hours before the appointment'
    )
    refund_percentage = fields.Float(
        string='Refund %', required=True, default=100.0
    )

    @api.constrains('refund_percentage')
    def _check_percentage(self):
        for rec in self:
            if not (0.0 <= rec.refund_percentage <= 100.0):
                raise ValidationError(
                    _('Refund percentage must be between 0 and 100.'))
