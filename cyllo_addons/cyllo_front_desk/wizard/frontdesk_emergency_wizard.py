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


class FrontdeskEmergencyWizard(models.TransientModel):
    _name = 'frontdesk.emergency.wizard'
    _description = 'Trigger Emergency Alert Wizard'

    station_id = fields.Many2one('frontdesk.frontdesk', string='Station', required=True)
    alert_id = fields.Many2one(
        'frontdesk.emergency.alert', 
        string='Alert Type', 
        required=True,
        domain="[('station_ids', 'in', station_id)]"
    )
    message = fields.Text(string='Message', required=True)

    @api.onchange('alert_id')
    def _onchange_alert_id(self):
        if self.alert_id:
            self.message = self.alert_id.default_message

    def action_send_alert(self):
        self.ensure_one()
        alert = self.alert_id
        station = self.station_id
        partner_ids = set()
        no_user_employees = self.env['hr.employee']
        for user in alert.recipient_user_ids:
            if user.partner_id:
                partner_ids.add(user.partner_id.id)
        for employee in alert.recipient_employee_ids:
            if employee.user_id and employee.user_id.partner_id:
                partner_ids.add(employee.user_id.partner_id.id)
            elif employee.work_email:
                no_user_employees |= employee

        # 2. Build Recipient Summary
        recipients_names = []
        if alert.recipient_user_ids:
            recipients_names.append(f"Users: {', '.join(alert.recipient_user_ids.mapped('name'))}")
        if alert.recipient_employee_ids:
            recipients_names.append(f"Employees: {', '.join(alert.recipient_employee_ids.mapped('name'))}")
        if alert.recipient_channel_ids:
            recipients_names.append(f"Discuss Channels: {', '.join(alert.recipient_channel_ids.mapped('name'))}")
        recipient_summary = " | ".join(recipients_names) or _("None configured")

        # 3. Create Audit Log
        log_vals = {
            'station_id': station.id,
            'alert_id': alert.id,
            'message': self.message,
            'recipient_summary': recipient_summary,
            'user_id': self.env.user.id,
            'date': fields.Datetime.now()
        }
        log_record = self.env['frontdesk.emergency.log'].create(log_vals)

        # 4. Send Odoo notifications / emails (Discuss message on log record)
        formatted_message = _("EMERGENCY ALERT at %(station_name)s:\n%(message)s") % {
                                'station_name': station.name,
                                'message': self.message,
                            }
        ui_notification_message = _("Emergency alert '%(alert_name)s' at %(station_name)s: %(message)s") % {
            'alert_name': alert.name,
            'station_name': station.name,
            'message': self.message,
        }

        if partner_ids:
            log_record.message_post(
                body=formatted_message,
                partner_ids=list(partner_ids),
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )

        for user in alert.recipient_user_ids.filtered('partner_id'):
            self.env['bus.bus']._sendone(user.partner_id, 'simple_notification', {
                'type': 'danger',
                'title': _("Emergency Alert"),
                'message': ui_notification_message,
                'sticky': True,
            })

        # 5. Send direct email to employees without Odoo users
        for employee in no_user_employees:
            self.env['mail.mail'].create({
                'subject': _("EMERGENCY ALERT: %(alert_name)s at %(station_name)s") % {
                    'alert_name': alert.name,
                    'station_name': station.name
                },
                'body_html': f"<p>{formatted_message}</p>",
                'email_to': employee.work_email,
            }).send()

        # 6. Post message to all configured Discuss channels
        for channel in alert.recipient_channel_ids:
            channel.message_post(
                body=formatted_message,
                message_type='comment',
                subtype_xmlid='mail.mt_comment'
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Emergency Alert Sent!"),
                'message': _("Emergency alert '%(alert_name)s' was successfully broadcast.") % {'alert_name': alert.name},
                'type': 'danger',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window',
                    'res_model': 'frontdesk.emergency.log',
                    'res_id': log_record.id,
                    'views': [[False, 'form']],
                    'target': 'current',
                }
            }
        }
