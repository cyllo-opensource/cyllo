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
import base64
from odoo import _, api, fields, models
from odoo.tools.convert import safe_eval


class MarketingActivity(models.Model):
    """
    Model representing marketing activities, with extended functionality for WhatsApp messages.
    """
    _inherit = "marketing.activity"

    type = fields.Selection(selection_add=[
        ('whatsapp', 'Whatsapp Message'),
    ], ondelete={'whatsapp': 'cascade'}, help="Choose your activity type",
        required=True, default='mail')
    whatsapp_template_id = fields.Many2one(
        'whatsapp.template',
        string='Whatsapp template', help='Choose the whatsapp template')
    image_template = fields.Binary(
        string="Image for the message",
        help="Image will send with the whatsapp message", )
    attachment_id = fields.Many2one(
        'ir.attachment', compute='_compute_attachment_id',
        help='The attachment in the header of template')

    @api.depends('whatsapp_template_id')
    def _compute_attachment_id(self):
        """
         Compute method to determine the attachment based on the header type.
        """
        for rec in self:
            rec.attachment_id = False
            if rec.whatsapp_template_id.header_type in ['document']:
                model = self.env['ir.model'].browse(
                    rec.whatsapp_template_id.model_id.id)
                record = self.env[model.model].browse(rec.res_id)
                report_content = self.env['ir.actions.report']._render_qweb_pdf(
                    rec.whatsapp_template_id.report_id.id, record.id)[0]
                if rec.whatsapp_template_id.report_id.print_report_name:
                    report_name = safe_eval(
                        rec.whatsapp_template_id.report_id.print_report_name,
                        {'object': record}) + '.' + 'pdf'
                else:
                    report_name = f"{record.name}.pdf"
                ir_values = {
                    'name': report_name,
                    'type': 'binary',
                    'datas': base64.b64encode(report_content),
                    'mimetype': 'application/pdf',
                    'res_model': 'whatsapp.template.message',
                    'res_id': 0
                }
                attachment = self.env['ir.attachment'].create(ir_values)
                rec.attachment_id = attachment.id

    def _execute_whatsapp(self, participant, activity, activity_line,
                          test=None):
        """
        Execute WhatsApp sending action for a participant in a marketing activity.

        Args:
            participant (Recordset): The participant record.
            activity (Recordset): The marketing activity record.
            activity_line (Recordset): The marketing activity line record.
            test (bool): If True, indicates a test execution.

        Returns:
            bool: True if the execution is successful.
        """
        try:
            cloud_token = self.env.user.token
            phone_uid = self.env.user.phone_uid

            message = activity.whatsapp_template_id.action_send_template_marketing(
                activity, activity.attachment_id, participant.record,
                cloud_token,
                phone_uid)
            activity_line.write({
                'state': 'processed',
                'whatsapp_message_number': message,
            })
            participant.record_count -= 1
            if not test and participant.record_count == 0:
                participant.write({
                    'state': 'completed'
                })
        except Exception as e:
            activity_line.write({
                'state': 'error',
                'mail_failure_message': _(e),
            })
        return True
