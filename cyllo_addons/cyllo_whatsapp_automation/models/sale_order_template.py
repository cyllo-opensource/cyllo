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


class SaleOrderTemplate(models.Model):
    """
    Inherits from the 'sale.order.template' model to add fields for WhatsApp
    integration.
    """
    _inherit = 'sale.order.template'

    flow_id = fields.Many2one(
        comodel_name='whatsapp.flows',
        copy=False,
        string="Whatsapp Flow",
        help="Flow of the quotation template"
    )
    template_id = fields.Many2one(
        comodel_name='whatsapp.template',
        copy=False,
        string="Whatsapp Template",
        help="Whatsapp template of the quotation template"
    )

    def action_remove_wa_template(self):
        """
        Removes the associated WhatsApp template from the sale order.

        This method clears the `template_id` field by setting it to `False`,
        effectively dissociating any linked WhatsApp template from the current
        quotation template.
        """
        self.write({
            'template_id': False,
        })
        # self.action_create_whatsapp_template()

    def action_view_template(self):
        """
        Opens the WhatsApp template associated with the sale order template.

        This action triggers a form view to display the WhatsApp template
        linked to the current sale order template, allowing the user to view
        and manage the template.

        Returns:
            dict: Action dictionary to open the WhatsApp template in a form view.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Whatsapp Template',
            'view_mode': 'form',
            'res_model': 'whatsapp.template',
            'res_id': self.template_id.id,
            'context': "{'create': False}"
        }

    def action_create_whatsapp_template(self):
        """
        Creates a WhatsApp template linked to the current WhatsApp flow.

        This method ensures that a WhatsApp flow exists and is in the 'published'
        state before allowing the creation of a WhatsApp template. Once validated,
        it opens a form view to create the template, pre-filling relevant
        information such as the associated flow and model.

        Raises:
            ValidationError: If no WhatsApp flow is linked, or if the flow is
            not published.

        Returns:
            dict: Action dictionary to open the WhatsApp template creation form.
        """
        if not self.flow_id:
            raise ValidationError(
                "To create a Whatsapp  template, You must create a whatsapp flow first.")
        if self.flow_id.state != 'published':
            raise ValidationError(
                "The Whatsapp flow must be published before creating a template.")
        return {
            'name': _('Create Whatsapp Template'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'whatsapp.template',
            'target': 'new',
            'view_id': self.env.ref(
                'cyllo_whatsapp_automation.view_whatsapp_template_form_custom').id,
            'context': {
                'default_template_type': 'flows',
                'default_flows_id': self.flow_id.id,
                'default_model_id': self.env['ir.model']._get(self._name).id,
                'default_action': 'create_sale_order',
            }
        }

    def action_view_flow(self):
        """
        Opens the form view for the WhatsApp flow linked to this sale order
        template.

        Returns:
            dict: A dictionary containing action information to open the
            WhatsApp flow form view.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Whatsapp Flows',
            'view_mode': 'form',
            'res_model': 'whatsapp.flows',
            'res_id': self.flow_id.id,
            'context': "{'create': False, 'edit': False}"
        }

    def action_create_whatsapp_flow(self):
        """
        Creates a WhatsApp flow based on the quotation template.

        This method checks if there are products in the quotation template. If
        no products are present, it raises a validation error. It then generates
        a WhatsApp flow with two screens: one for collecting user information
        (name, email, mobile) and another for choosing products from the sale
        order template lines. The created flow is linked to the current record.

        Raises:
            ValidationError: If no products are added to the quotation template.

        Returns:
            None
        """
        if not self.sale_order_template_line_ids:
            raise ValidationError(
                _("Add minimum one product in the quotation template to create a flow"))
        flow_screens = []
        for index, line in enumerate(self.sale_order_template_line_ids):
            product_image = line.product_id.image_1920
            if product_image:
                image_data = product_image
            else:
                image_data = None
            screen_data = [
                (0, 0, {
                    'content_type': 'text',
                    'content_text_type': 'large_heading',
                    'text': line.product_id.name,
                }),
                (0, 0, {
                    'content_type': 'text',
                    'content_text_type': 'body',
                    'text': line.product_id.description_sale or "No description available.",
                }),
                (0, 0, {
                    'content_type': 'text_answer',
                    'content_text_answer_type': 'short_answer',
                    'shot_answer_type': 'number',
                    'label': 'Enter your Quantity',
                    'product_id': line.product_id.id,
                    'required': False
                }),
            ]
            if image_data:
                screen_data.insert(0, (0, 0, {
                    'content_type': 'media',
                    'image_1920': image_data,
                }))
            flow_screens.append((0, 0, {
                'name': line.product_id.name,
                'button_name': 'Next',
                'content_ids': screen_data,
            }))
        flow_data = {
            'name': f"{self.name} [Whatsapp Flow {self.id}]",
            'screen_ids': flow_screens,
        }
        flow_id = self.env['whatsapp.flows'].create(flow_data)
        if flow_id:
            self.flow_id = flow_id

    def action_send_whatsapp_template(self):
        """
        Initiates the process to send a WhatsApp template message associated
        with the current record.

        This action checks if the associated WhatsApp template is approved.
        If the template is not yet approved, it raises a ValidationError with
        instructions to send the template for approval. Once approved, it opens
        a form view to compose and send the WhatsApp template message.

        Raises:
            ValidationError: If the WhatsApp template is not in the 'approved'
            state.

        Returns:
            dict: An Odoo action to open the form view for sending the WhatsApp
            template message.
        """
        if self.template_id.state != 'approved':
            raise ValidationError(
                _("The WhatsApp Template is not yet approved. Please click the 'Template' smart tab and click on the 'Send for Approval' button inside the template. Approval by the WhatsApp team may take up to 24 hours."))
        return {
            'name': _('Send Whatsapp Template'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'cyllo_whatsapp_automation.view_whatsapp_template_message_quotation_template_form').id,
            'res_model': 'whatsapp.template.message',
            'target': 'new',
            'context': {
                'default_wa_template_id': self.template_id.id,
                'default_model_id': self.env['ir.model'].sudo().search(
                    [('model', '=', self._name)], limit=1).id,
            }
        }
