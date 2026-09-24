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
from odoo.exceptions import ValidationError



class WhatsappTemplateMessage(models.TransientModel):
    _inherit = 'whatsapp.template.message'

    partner_ids = fields.Many2many(
        comodel_name='res.partner',
        string="Partners",
        help="Select the partners to whom the WhatsApp template should be sent."
    )

    def action_send_template_multiple_users(self):
        """
        Action method to send a WhatsApp template to multiple users.

        This method is responsible for sending the selected WhatsApp template
        to multiple partners. It checks if a template is selected, retrieves
        the active record, and then calls the `action_send_template` method
        on the selected template to send it to the specified partners.

        Raises:
            ValidationError: If no template is selected for sending.
        """
        if not self.wa_template_id:
            raise ValidationError(_('Please add template you want to send'))
        record = self.env[self.model_id.model].browse(self.env.context.get('active_id'))
        self.wa_template_id.action_send_template(record, self.attachment_id, self.partner_ids)