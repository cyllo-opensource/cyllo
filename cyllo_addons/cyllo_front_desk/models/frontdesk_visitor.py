# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import uuid
import pytz

class FrontdeskVisitor(models.Model):
    _name = 'frontdesk.visitor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Frontdesk Visitor'
    _order = 'check_in desc, id desc'

    def _default_state(self):
        visitor_type = self._context.get('default_visitor_type', 'meeting')
        return 'draft' if visitor_type == 'meeting' else 'planned'

    name = fields.Char(
        string='Reference',
        required=True, copy=False, readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    visitor_type = fields.Selection([
        ('meeting', 'Meeting'),
        ('enquiry', 'Enquiry'),
    ], string='Visitor Type', default='meeting', required=True, tracking=True)

    partner_id = fields.Many2one('res.partner', string='Customer/Partner',
                                 tracking=True)
    visitor_name = fields.Char(string='Visitor Name', required=True,
                               tracking=True)

    phone = fields.Char(string='Phone', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    company = fields.Char(string='Company', tracking=True)
    enquiry_id = fields.Many2one(
        'frontdesk.enquiry',
        string='Enquiry Reference',
        readonly=True,
        copy=False,
        tracking=True,
    )
    host_id = fields.Many2one('hr.employee', string='Host', help='Employee being visited', tracking=True)
    station_id = fields.Many2one('frontdesk.frontdesk', string='Station', required=True, tracking=True)
    is_host = fields.Boolean(related='station_id.is_host', string='Host Selection', readonly=True)
    is_drink = fields.Boolean(related='station_id.is_drink', string='Offer Drinks', readonly=True)
    drink_selection_ids = fields.Many2many('frontdesk.drink', related='station_id.drink_selection_ids', string='Drinks Offered', readonly=True)
    host_domain_ids = fields.Many2many(
        'hr.employee',
        compute='_compute_host_domain_ids',
        string='Available Hosts',
    )
    check_in = fields.Datetime(string='Check-In Time', readonly=True, tracking=True)
    check_out = fields.Datetime(string='Check-Out Time', readonly=True, tracking=True)
    drink_id = fields.Many2one('frontdesk.drink', string='Drink Requested', tracking=True)
    drink_served = fields.Boolean(string='Drink Served', default=False, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled')
    ], string='Status', default=_default_state, required=True, tracking=True)
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)
    user_id= fields.Many2one('res.users', string="Responsible User",default= lambda self: self.env.user.id)
    is_frontdesk_manager = fields.Boolean(compute='_compute_is_frontdesk_manager')
    # Meeting approval workflow fields
    expected_arrival = fields.Datetime(string='Expected Arrival', tracking=True)
    purpose = fields.Char(string='Meeting Purpose', tracking=True)
    access_token = fields.Char(string='Access Token', copy=False, readonly=True)
    is_approval_email_sent = fields.Boolean(string='Approval Email Sent', default=False, copy=False)
    approved_by_id = fields.Many2one('hr.employee', string='Approved By', readonly=True, tracking=True)
    approved_datetime = fields.Datetime(string='Approval Date/Time', readonly=True, tracking=True)
    rejected_by_id = fields.Many2one('hr.employee', string='Rejected By', readonly=True, tracking=True)
    rejected_datetime = fields.Datetime(string='Rejection Date/Time', readonly=True, tracking=True)

    @api.depends('station_id', 'station_id.responsible_ids')
    def _compute_host_domain_ids(self):
        for visitor in self:
            if visitor.station_id:
                visitor.host_domain_ids = visitor.station_id.responsible_ids
            else:
                visitor.host_domain_ids = self.env['hr.employee']

    @api.depends_context('uid')
    def _compute_is_frontdesk_manager(self):
        is_manager = self.env.user.has_group(
            'cyllo_front_desk.group_frontdesk_admin'
        )
        for rec in self:
            rec.is_frontdesk_manager = is_manager

    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for visitor in self:
            if visitor.check_in and visitor.check_out:
                diff = visitor.check_out - visitor.check_in
                visitor.duration = diff.total_seconds() / 3600.0
            elif visitor.check_in:
                diff = fields.Datetime.now() - visitor.check_in
                visitor.duration = diff.total_seconds() / 3600.0
            else:
                visitor.duration = 0.0

    @api.onchange('station_id')
    def _onchange_station_id(self):
        if self.station_id:
            if not self.station_id.is_host:
                self.host_id = False
            if not self.station_id.is_drink:
                self.drink_id = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.visitor_name = self.partner_id.name
            self.phone = self.partner_id.phone or self.partner_id.mobile
            self.email = self.partner_id.email
            self.company = self.partner_id.parent_id.name if self.partner_id.parent_id else (
                self.partner_id.name if self.partner_id.is_company else False
            )

    @api.model_create_multi
    def create(self, vals_list):
        is_manager = self.env.user.has_group('cyllo_front_desk.group_frontdesk_admin')
        for vals in vals_list:
            if 'user_id' in vals and vals.get('user_id') != self.env.user.id and not is_manager:
                raise UserError(_("Only a Front Desk Manager can assign a visitor to another user."))

            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'frontdesk.visitor') or _('New')
            if vals.get('station_id'):
                station = self.env['frontdesk.frontdesk'].browse(
                    vals['station_id'])
                if not station.is_host:
                    vals['host_id'] = False
                if not station.is_drink:
                    vals['drink_id'] = False
            
            # Control state and generate access token based on visitor_type
            visitor_type = vals.get('visitor_type', 'meeting')
            if visitor_type == 'meeting':
                vals['state'] = 'draft'
                if not vals.get('access_token'):
                    vals['access_token'] = uuid.uuid4().hex
            else:
                vals['state'] = 'planned'

        records = super(FrontdeskVisitor, self).create(vals_list)
        return records

    def write(self, vals):
        if 'user_id' in vals and not self.env.user.has_group('cyllo_front_desk.group_frontdesk_admin'):
            raise UserError(_("Only a Front Desk Manager can modify the assigned user."))

        if any(f in vals for f in ('station_id', 'host_id', 'drink_id')):
            for visitor in self:
                station = self.env['frontdesk.frontdesk'].browse(vals.get('station_id', visitor.station_id.id))
                if not station.is_host:
                    vals['host_id'] = False
                if not station.is_drink:
                    vals['drink_id'] = False
        
        if 'visitor_type' in vals:
            if vals['visitor_type'] == 'meeting':
                vals['state'] = 'draft'
                for visitor in self:
                    if not visitor.access_token:
                        vals['access_token'] = uuid.uuid4().hex
            elif vals['visitor_type'] == 'enquiry':
                vals['state'] = 'planned'

        res = super(FrontdeskVisitor, self).write(vals)
        return res

    def action_send_request(self):
        """Send meeting approval request email to the host."""
        for visitor in self:
            if visitor.visitor_type != 'meeting':
                raise UserError(_("Approval requests can only be sent for Meeting type visitors."))
            if not visitor.host_id:
                raise UserError(_("Please assign a host before sending the request."))
            if not visitor.host_id.work_email:
                raise UserError(_("The assigned host does not have a work email configured."))
            if visitor.is_approval_email_sent:
                raise UserError(_("An approval request has already been sent for this visitor."))
            visitor.send_approval_request_email()
            visitor._message_log(body=_("Meeting approval request sent to %s.") % visitor.host_id.name)

    def action_check_in(self):
        for visitor in self:
            visitor.write({
                'state': 'checked_in',
                'check_in': fields.Datetime.now()
            })
            visitor._message_log(body=_("Visitor checked in."))
            visitor._send_notifications()

    def action_check_out(self):
        for visitor in self:
            if visitor.state != 'checked_in':
                raise UserError(_('Only checked in visits can be checked out.'))
            visitor.write({
                'state': 'checked_out',
                'check_out': fields.Datetime.now()
            })
            visitor._message_log(body=_("Visitor checked out. Duration: %s hours.") % round(visitor.duration, 2))

    def action_cancel(self):
        for visitor in self:
            if visitor.state == 'checked_out':
                raise UserError(_('You cannot cancel a visit that is already checked out.'))
            visitor.write({
                'state': 'cancelled'
            })
            visitor._message_log(body=_("Visit cancelled."))

    def action_drink_served(self):
        for visitor in self:
            visitor.write({'drink_served': True})
            visitor._message_log(body=_("Drink served: %s") % (visitor.drink_id.name or _("N/A")))

    def action_create_enquiry(self):
        self.ensure_one()
        if self.visitor_type != 'enquiry':
            raise UserError(_("Only enquiry visitors can create an enquiry."))
        if self.enquiry_id:
            raise UserError(_("An enquiry is already linked to this visitor."))
        return {
            'name': _('Create Enquiry'),
            'type': 'ir.actions.act_window',
            'res_model': 'frontdesk.visitor.enquiry.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_visitor_id': self.id,
                'default_visitor_name': self.visitor_name,
                'default_phone': self.phone,
                'default_email': self.email,
                'default_company': self.company,
                'default_station_id': self.station_id.id,
                'default_handled_by': self.host_id.id,
            },
        }

    def _format_datetime(self, dt):
        if not dt:
            return ""
        tz = self.env.user.tz or self.host_id.user_id.tz or 'UTC'
        try:
            timezone = pytz.timezone(tz)
        except pytz.UnknownTimeZoneError:
            timezone = pytz.utc
        
        if dt.tzinfo is None:
            utc_dt = pytz.utc.localize(dt)
        else:
            utc_dt = dt.astimezone(pytz.utc)
            
        local_dt = utc_dt.astimezone(timezone)
        return local_dt.strftime('%d-%b-%Y %I:%M %p')

    def send_approval_request_email(self):
        for visitor in self:
            if not visitor.host_id or not visitor.host_id.work_email or visitor.is_approval_email_sent:
                continue

            if not visitor.access_token:
                visitor.access_token = uuid.uuid4().hex

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            from urllib.parse import urljoin
            approve_url = urljoin(base_url, f'/frontdesk/meeting/approve/{visitor.access_token}')
            reject_url = urljoin(base_url, f'/frontdesk/meeting/reject/{visitor.access_token}')

            expected_arrival_str = visitor._format_datetime(visitor.expected_arrival)

            subject = _("Meeting Approval Request - %s") % visitor.visitor_name
            body_html = f"""
            <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #ffffff;">
                <h3 style="color: #333333; margin-top: 0; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px;">Meeting Approval Request</h3>
                <p style="color: #555555; font-size: 15px; line-height: 1.5; margin-bottom: 20px;">
                    A new visitor meeting request has been submitted.
                </p>
                <div style="background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin-bottom: 25px; border-radius: 4px;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 14px; color: #444444;">
                        <tr>
                            <td style="padding: 6px 0; font-weight: bold; width: 120px; vertical-align: top;">Visitor:</td>
                            <td style="padding: 6px 0; vertical-align: top;">{visitor.visitor_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 6px 0; font-weight: bold; vertical-align: top;">Purpose:</td>
                            <td style="padding: 6px 0; vertical-align: top;">{visitor.purpose or ''}</td>
                        </tr>
                        <tr>
                            <td style="padding: 6px 0; font-weight: bold; vertical-align: top;">Date &amp; Time:</td>
                            <td style="padding: 6px 0; vertical-align: top;">{expected_arrival_str}</td>
                        </tr>
                    </table>
                </div>
                <p style="color: #555555; font-size: 15px; margin-bottom: 20px;">Please review and take action:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{approve_url}" style="background-color: #28a745; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: bold; margin-right: 15px; display: inline-block; box-shadow: 0 2px 4px rgba(40,167,69,0.2); transition: background-color 0.2s;">Approve Meeting</a>
                    <a href="{reject_url}" style="background-color: #dc3545; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block; box-shadow: 0 2px 4px rgba(220,53,69,0.2); transition: background-color 0.2s;">Reject Meeting</a>
                </div>
            </div>
            """

            mail = self.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body_html,
                'email_to': visitor.host_id.work_email,
            })
            mail.send()
            visitor.is_approval_email_sent = True

    def _send_notifications(self):
        """Send notifications to host and/or station responsibles upon visitor check-in."""
        for visitor in self:
            station = visitor.station_id
            host = visitor.host_id
            
            # Formulate notification message
            drink_msg = f" (Requested Drink: {visitor.drink_id.name})" if visitor.drink_id else ""
            company_msg = f" from {visitor.company}" if visitor.company else ""
            msg_body = _("Visitor <b>%(visitor_name)s</b>%(company)s has checked in for <b>%(host_name)s</b> at %(station_name)s%(drink)s.") % {
                'visitor_name': visitor.name,
                'company': company_msg,
                'host_name': host.name if host else _("No Host Specified"),
                'station_name': station.name,
                'drink': drink_msg
            }

            # 1. Notify Host by Email / Discuss if configured
            if host:
                if station.notify_by_email and host.work_email:
                    self.env['mail.mail'].sudo().create({
                        'subject': _("Visitor Check-In: %(visitor_name)s") % {'visitor_name': visitor.name},
                        'body_html': f"<p>{msg_body}</p>",
                        'email_to': host.work_email,
                    }).send()

                if station.notify_by_discuss and host.user_id:
                    host.user_id.partner_id.message_post(
                        body=msg_body,
                        message_type='notification',
                        subtype_xmlid='mail.mt_comment'
                    )

            # 2. Notify Station Responsibles
            for responsible in station.responsible_ids:
                if station.notify_by_email and responsible.work_email:
                    self.env['mail.mail'].sudo().create({
                        'subject': _("Visitor Check-In at %(station_name)s: %(visitor_name)s") % {
                            'station_name': station.name,
                            'visitor_name': visitor.name
                        },
                        'body_html': f"<p>{msg_body}</p>",
                        'email_to': responsible.work_email,
                    }).send()

                if station.notify_by_discuss and responsible.user_id:
                    responsible.user_id.partner_id.message_post(
                        body=msg_body,
                        message_type='notification',
                        subtype_xmlid='mail.mt_comment'
                    )

            # 3. Notify Drink preparation team if visitor requested a drink
            if visitor.drink_id and visitor.drink_id.notify_user_ids:
                drink_body = _("Drink requested: <b>%(drink_name)s</b> for visitor <b>%(visitor_name)s</b> at %(station_name)s.") % {
                    'drink_name': visitor.drink_id.name,
                    'visitor_name': visitor.name,
                    'station_name': station.name
                }
                for drink_notify in visitor.drink_id.notify_user_ids:
                    if drink_notify.work_email:
                        self.env['mail.mail'].sudo().create({
                            'subject': _("Drink Request: %(drink_name)s") % {'drink_name': visitor.drink_id.name},
                            'body_html': f"<p>{drink_body}</p>",
                            'email_to': drink_notify.work_email,
                        }).send()
                    if drink_notify.user_id:
                        drink_notify.user_id.partner_id.message_post(
                            body=drink_body,
                            message_type='notification',
                            subtype_xmlid='mail.mt_comment'
                        )
