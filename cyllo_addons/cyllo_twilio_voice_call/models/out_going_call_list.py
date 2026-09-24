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

try:
    from twilio.rest import Client
except ImportError:
    pass


class OutGoingCallList(models.Model):
    """The class is used to create the outgoing call list"""
    _name = 'out.going.call.list'
    _description = "OutGoing Call List"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reference'

    reference = fields.Char(readonly=True, copy=False, default='New',
                            help="Reference to the model")
    from_number = fields.Char('From', help='From number to call any number')
    to_number = fields.Char('To', help='Receiving number for testing')
    user_id = fields.Many2one('res.users',
                              default=lambda self: self.env.user.id,
                              string="Caller", readonly=True)
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company,
                                 readonly=True)
    start_time = fields.Datetime(
        help="To get the time and date, when the call is started")
    end_time = fields.Datetime(
        help="To get the time and date, when the call is ended")
    duration = fields.Char(help="Duration of the call",compute='_compute_duration')
    status = fields.Char(help="Status of the call")
    record_sid = fields.Char(string="Record Details",
                             help="Record Sid of the call")
    call_sid = fields.Char(help="To get the call sid")
    image_1920 = fields.Image(string="Image", help="To get the image")
    partner_id = fields.Many2one('res.partner', string="Name")

    @api.model_create_multi
    def create(self, vals):
        """Supering create function to add reference"""
        for val in vals:
            if val.get('reference', 'New') == 'New':
                val['reference'] = self.env['ir.sequence'].next_by_code(
                    'out.going.call.list') or 'New'
        return super(OutGoingCallList, self).create(vals)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.end_time and record.start_time:
                duration = record.end_time - record.start_time
                total_seconds = int(duration.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                if hours:
                    record.duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    record.duration = f"{minutes:02d}:{seconds:02d}"
            else:
                record.duration = False

    def action_call(self, num, Sid, id):
        """To create an outgoing call list when we're making a call """
        global partner_id
        account_sid = self.env["ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.account_sid")
        auth_token = self.env["ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.auth_token")
        from_number = self.env["ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.from_number")
        client = Client(account_sid, auth_token)
        call = client.calls(Sid).fetch()
        image_1920 = False
        if id:
            partner_id = id
            partner = self.env['res.partner'].browse(partner_id)
            partner = partner[0] if len(partner) > 1 else partner
            image_1920 = partner.image_1920
        if not id:
            partner_id = False
        if call:
            self.env['out.going.call.list'].sudo().create({
                'from_number': from_number,
                'to_number': num,
                'start_time': fields.datetime.now(),
                'duration': call.duration,
                'call_sid': Sid,
                'image_1920': image_1920,
                'partner_id': partner_id
            })

    def action_making_call(self, num, Sid):
        """To create an outgoing call list when we're making a call """
        account_sid = self.env["ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.account_sid")
        auth_token = self.env["ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.auth_token")
        from_number = self.env["ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.from_number")
        client = Client(account_sid, auth_token)
        call = client.calls(Sid).fetch()
        if call:
            self.env['out.going.call.list'].sudo().create({
                'from_number': from_number,
                'to_number': num,
                'start_time': fields.datetime.now(),
                'duration': call.duration,
                'call_sid': Sid,
            })

    def action_cancel(self, num, Sid):
        """The function performs when a call is disconnected"""
        # Retrieve Twilio credentials and phone numbers from configuration
        global partner_id
        account_sid = self.env["ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.account_sid")
        auth_token = self.env["ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.auth_token")
        from_number = self.env["ir.config_parameter"].sudo().get_param(
            "cyllo_twilio_voice_call.from_number")
        client = Client(account_sid, auth_token)
        image_1920 = False
        if num:
            partner = self.env['res.partner'].search(
                ['|', ('mobile', '=', num), ('phone', '=', num)])
            if partner:
                partner = partner[0] if len(partner) > 1 else partner
                image_1920 = partner.image_1920
                partner_id = partner.id
            if not partner:
                partner_id = False
        # Retrieve the active call by its SID
        try:
            if Sid and Sid.startswith('CA'):
                active_call = client.calls(Sid).fetch()
                if active_call:
                    # Retrieve existing record based on call SID
                    existing_record = self.env['out.going.call.list'].search(
                        [('call_sid', '=', Sid)])
                    if existing_record:
                        existing_record.sudo().write({
                            'end_time': fields.datetime.now(),
                            'to_number': num,
                            'from_number': from_number,
                            'image_1920': image_1920,
                            'partner_id': partner_id
                        })
                    else:
                        self.env['out.going.call.list'].sudo().create({
                            'from_number': from_number,
                            'to_number': num,
                            'start_time': fields.datetime.now(),
                            'call_sid': Sid,
                            'end_time': fields.datetime.now(),
                            'image_1920': image_1920,
                            'partner_id': partner_id
                        })
                        # Return a success message or perform any other necessary actions
                    return "Call details updated successfully."
            else:
                return "No active call found for the specified Partner."
        except Exception as e:
            return f"Error with Twilio API: {e}"
        return "Unexpected error occurred."

    def action_play_recording(self):
        """To play the recordings of the call"""
        if self.record_sid:
            return {
                'type': 'ir.actions.act_url',
                'url': self.record_sid,
                'target': 'new'
            }
        else:
            return False
