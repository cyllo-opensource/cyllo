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
from odoo import _, api, fields, models


class WhatsappTemplatePreview(models.TransientModel):
    """Model for Template Preview of Whatsapp."""
    _name = 'whatsapp.template.preview'
    _description = 'Template Preview of Whatsapp'

    template_id = fields.Many2one("whatsapp.template", string="Templates",
                                  help="The whatsapp template for previewing")
    wa_template_preview = fields.Html(compute="_compute_wa_template_preview", string="Message Preview",
                                      help="Whatsapp template preview")

    @api.depends('template_id')
    def _compute_wa_template_preview(self):
        """Compute the WhatsApp template preview for each record.
          This method calculates the WhatsApp template preview based on the
          selected template's information.
          It takes into account the template's body, header type, footer text,
          and language direction.
          :return: None"""
        for preview in self:
            preview_data = {
                'header_type': preview.template_id.header_type,
                'attachment': self.template_id.attachment_ids,
                'header_text': preview.template_id._get_formatted_template_header(demo_value=True, record=False),
                'body': preview.template_id._get_formatted_template_body(demo_value=True, record=False),
                'footer_text': preview.template_id.footer_text,
                'button': preview.template_id.is_button,
                'button_name': preview.template_id.button_name,
                'button_url': preview.template_id.button_url,
            } if preview.template_id else None
            preview.wa_template_preview = self.env['ir.qweb']._render(
                'cyllo_whatsapp.whatsapp_template_preview_templates', preview_data) if preview_data else None
