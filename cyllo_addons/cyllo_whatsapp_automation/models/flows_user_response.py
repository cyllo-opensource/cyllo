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
from odoo import fields, models


class FlowUserResponse(models.Model):
    """
    Model to store and manage responses from users in WhatsApp flows.

    This model captures all user inputs related to specific WhatsApp flows.
    It links to a flow, stores the associated template, the contact involved,
    and tracks the status and responses in the flow. The responses are stored
    in both individual lines and in an HTML format for ease of display and processing.
    """
    _name = "flows.user.response"
    _description = "Flows User Response"
    _rec_name = "flows_id"
    _order = "create_date desc"

    flows_id = fields.Many2one(
        comodel_name='whatsapp.flows',
        string='Flows',
        required=True,
        readonly=True,
        ondelete='cascade',
        help='The WhatsApp flow associated with the user response.'
    )
    template_id = fields.Many2one(
        comodel_name='whatsapp.template',
        string='Template',
        required=True,
        readonly=True,
        help='The WhatsApp template used for the flow.'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Contact',
        readonly=True,
        help='The contact (partner) associated with the user response.'
    )
    number = fields.Char(
        string='Whatsapp Number',
        readonly=True,
        help='The WhatsApp number of the user who submitted the response.'
    )
    flows_user_response_line_ids = fields.One2many(
        comodel_name='flows.user.response.line',
        inverse_name='response_id',
        string='Response',
        readonly=True,
        help='The individual lines of responses provided by the user.'
    )
    user_id = fields.Many2one(
        string='Responsible User',
        comodel_name='res.users', default=lambda self: self.env.user,
        help='The user is responsible for this flow'
    )
    company_id = fields.Many2one(
        comodel_name='res.company', required=True,
        default=lambda self: self.env.company,
        string='Associated Company',
        help='Select the company under which this WhatsApp response is managed.'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='The field describes the record is active or not'
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('lead_created', 'Lead Created'),
        ],
        string='Status',
        default='draft',
        required=True,
        help="The current status of the user response."
    )
    json_format = fields.Html(
        string='JSON format',
        help="The user response stored in HTML format for processing and display."
    )

    def action_create_lead(self):
        """
        Create a CRM lead and optionally a sale order based on WhatsApp flow
        data.

        This method performs the following actions:
        1. Creates a CRM lead associated with the partner and WhatsApp flow.
        2. Executes a specified template action if defined.
        3. If the action is 'create_sale_order', creates a sale order with the
           user's responses from the WhatsApp flow as order lines.
        4. Generates a review template for the created sale order, including a
           link for the customer to review and pay online.

        Returns:
            None
        """
        partner = self.partner_id
        crm_lead = self.env['crm.lead'].create({
            'partner_id': partner.id,
            'contact_name': partner.name,
            'phone': self.number,
            'source_id': self.env.ref(
                'cyllo_whatsapp_automation.utm_source_whatsapp').id,
            'name': f"Lead created from WhatsApp flow: {self.flows_id.name}",
        })
        if self.template_id.action == 'create_sale_order':
            sale_order_lines = self.flows_user_response_line_ids.mapped(
                lambda line: (0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.user_input,
                }))
            sale_order = self.env['sale.order'].sudo().create({
                'partner_id': partner.id,
                'order_line': sale_order_lines,
                'whatsapp_order': True,
                'opportunity_id': crm_lead.id,
            })
            if sale_order:
                portal_url = sale_order.get_portal_url()
                base_url = self.env['ir.config_parameter'].sudo().get_param(
                    'web.base.url')
                payment_link = f"{base_url}{portal_url}"
                review_template = self.env[
                    'whatsapp.template'].sudo().create({
                    'name': f"order_review_template_for_quotation_{sale_order.name.lower()}",
                    'template_type': 'custom',
                    'category': 'marketing',
                    'header_type': 'text',
                    'header_text': 'Review Your Quotation',
                    'body': f"Hello {sale_order.partner_id.name} Your quotation {sale_order.name} amounting in {sale_order.amount_total} is ready for review.",
                    'is_button': True,
                    'button_name': 'Review and Pay Online',
                    'button_url': payment_link,
                    'model_id': self.env['ir.model']._get(sale_order._name).id
                })
                if review_template:
                    sale_order.write({'template_id': review_template.id})
        self.state = 'lead_created'
