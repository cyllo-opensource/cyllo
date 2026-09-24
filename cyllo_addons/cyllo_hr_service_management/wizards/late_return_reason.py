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
from odoo import _, fields, models


class LateReturnReason(models.TransientModel):
    """
    Wizard to capture and handle the reason for late return of custody items
    in a service request (e.g., equipment or asset).

    This model is opened as a popup when the user clicks "Return" on a custody
    request that is being returned late. It:
      - Updates the service request state to "quality"
      - Records the return date
      - Sends a notification email to the assigned handler
      - Posts a message in the chatter with the late return reason
    """
    _name = 'late.return.reason'
    _description = "Service Request"

    service_request_id = fields.Many2one('hr.service',
                                         help="Related service request")
    reason = fields.Text(help='The reason for late return')

    def action_return(self):
        """Handle the RETURN button action in Custody Request form."""
        self.service_request_id.write({
            'state': 'quality',
            'return_date': fields.Datetime.today(),
        })
        msg = _("Late Return Reason :%s", self.reason)
        email_values_handler = {
            'email_to': self.service_request_id.service_handler_id.private_email}
        mail_template_handler = self.env.ref(
            'cyllo_hr_service_management.mail_template_equipment_ready_to_return')
        mail_template_handler.send_mail(self.service_request_id.id,
                                        email_values=email_values_handler,
                                        force_send=True)
        self.service_request_id._message_log(
            body="Equipment have been ready to return")
        self.service_request_id._message_log(body=msg)
