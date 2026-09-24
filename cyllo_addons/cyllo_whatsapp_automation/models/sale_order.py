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


class SaleOrder(models.Model):
    _inherit = "sale.order"

    whatsapp_order = fields.Boolean(
        string="Created from WhatsApp?",
        copy=False,
        help="Indicates whether this sale order was created from a WhatsApp flow."
    )
    template_id = fields.Many2one(
        comodel_name='whatsapp.template',
        string="WhatsApp Template",
        copy=False,
        help="The WhatsApp template associated with this sale order."
    )
    flow_id = fields.Many2one(
        comodel_name='whatsapp.flows',
        string="WhatsApp Flow",
        copy=False,
        help="The WhatsApp flow that triggered the creation of this sale order."
    )

    def action_view_wa_template(self):
        """
        Opens the WhatsApp template form view associated with this sale order.

        Returns:
            dict: A dictionary containing action information to open the
            template form.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Whatsapp Template',
            'view_mode': 'form',
            'res_model': 'whatsapp.template',
            'res_id': self.template_id.id,
            'context': "{'create': False}"
        }

    def action_send_by_whatsapp(self):
        """
        Opens a wizard to send the WhatsApp template message for this sale order.

        Returns:
            dict: A dictionary containing action information to open the wizard.
        """
        return {
            'name': _('Send Whatsapp Template'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'whatsapp.template.message',
            'target': 'new',
            'context': {
                'default_wa_template_id': self.template_id.id,
                'default_res_id': self.id,
                'default_model_id': self.env['ir.model']._get(self._name).id
            }
        }

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_delivery_status(self):
        """
        Extends the delivery status computation to include WhatsApp
        notifications.

        - If delivery is pending, sends a WhatsApp notification with the order
          details and a link to view them.
        - If delivery is fully completed, sends a WhatsApp notification
          confirming delivery.

        Creates a WhatsApp template for the respective status and links it to
        the sale order.
        """
        super(SaleOrder, self)._compute_delivery_status()
        for order in self:
            if order.whatsapp_order:
                if order.delivery_status == 'pending':
                    portal_url = order.get_portal_url()
                    base_url = self.env['ir.config_parameter'].sudo().get_param(
                        'web.base.url')
                    order_url = f"{base_url}{portal_url}"
                    confirmation_template = self.env[
                        'whatsapp.template'].sudo().create({
                        'name': f"order_confirmation_template_for_quotation_{order.name.lower()}",
                        'template_type': 'custom',
                        'category': 'marketing',
                        'header_type': 'text',
                        'header_text': 'Order Confirmed',
                        'body': f"\nHello {order.partner_id.name}, \n\nYour order is confirmed and your order number is {order.name}. \n\nDelivery has started and estimated delivery is on {order.expected_date}.",
                        'is_button': True,
                        'button_name': 'View Order Details',
                        'button_url': order_url,
                        'model_id': self.env['ir.model'].sudo().search(
                            [('model', '=', order._name)], limit=1).id
                    })
                    self.write({
                        'template_id': confirmation_template.id
                    })
                elif order.delivery_status == 'full':
                    portal_url = order.get_portal_url()
                    base_url = self.env['ir.config_parameter'].sudo().get_param(
                        'web.base.url')
                    order_url = f"{base_url}{portal_url}"
                    delivered_template = self.env[
                        'whatsapp.template'].sudo().create({
                        'name': f"delivery_successful_template_for_quotation_{order.name.lower()}",
                        'template_type': 'custom',
                        'category': 'marketing',
                        'header_type': 'text',
                        'header_text': 'Delivery Order',
                        'body': f"\nHello {order.partner_id.name}, \n\nYour order is successfully delivered.",
                        'is_button': True,
                        'button_name': 'View Order Details',
                        'button_url': order_url,
                        'model_id': self.env['ir.model'].sudo().search(
                            [('model', '=', order._name)], limit=1).id
                    })
                    self.write({
                        'template_id': delivered_template.id
                    })

    @api.depends('state', 'order_line.invoice_status')
    def _compute_invoice_status(self):
        """
        Extends the invoice status computation to include WhatsApp notifications.

        - If the invoice status is 'invoiced', sends a WhatsApp notification
          with the order details.

        Creates a WhatsApp template for invoicing and links it to the sale order.
        """
        super(SaleOrder, self)._compute_invoice_status()
        for order in self:
            if order.whatsapp_order and order.invoice_status == 'invoiced':
                portal_url = order.get_portal_url()
                base_url = self.env['ir.config_parameter'].sudo().get_param(
                    'web.base.url')
                order_url = f"{base_url}{portal_url}"
                invoiced_template = self.env[
                    'whatsapp.template'].sudo().create({
                    'name': f"invoice_template{order.name.lower()}",
                    'template_type': 'custom',
                    'category': 'marketing',
                    'header_type': 'text',
                    'header_text': 'Invoice',
                    'body': f"\nHello {order.partner_id.name}, \n\nWe have successfully invoiced your order.",
                    'is_button': True,
                    'button_name': 'View Order Details',
                    'button_url': order_url,
                    'model_id': self.env['ir.model'].sudo().search(
                        [('model', '=', order._name)], limit=1).id
                })
                self.write({
                    'template_id': invoiced_template.id
                })
