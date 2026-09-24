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
from odoo.http import request, route

from odoo.addons.website_sale.controllers.main import WebsiteSale



class ProductReferral(WebsiteSale):
    """For refer customer purchased product to their friends or family"""

    def _prepare_shop_payment_confirmation_values(self, order):
        """Super the function to pass the referral setting """
        res = super()._prepare_shop_payment_confirmation_values(order)
        config = request.env['ir.config_parameter'].sudo()
        res['referral'] = config.get_param(
            'cyllo_crm_advance_lead.create_lead_referral')
        return res

    @route('/referral', type='http', auth='public', website=True)
    def product_referral(self, **kwargs):
        """Render the referral form and pass the order_id"""
        # Get order_id from URL
        order_id = request.params.get('order_id')
        return request.render(
            'cyllo_crm_advance_lead.product_referral_template', {
                'order_id': order_id
            })

    @route('/referral/submit', type='http', auth='public', website=True,
           methods=['POST'])
    def create_referral_lead(self, **kwargs):
        """Create referral lead from the referral form"""
        product_ids = request.env['sale.order.line'].sudo().search([
            ('order_id', '=', int(kwargs.get('sale_order')))
        ]).mapped('product_id')
        products = product_ids.filtered(
            lambda p: p.product_tmpl_id.is_published == True)
        lead = request.env['crm.lead'].sudo().create({
            'is_advance_lead': True,
            'name': f"Product Referral",
            'type': 'lead',
            'contact_name': kwargs.get('friend_name'),
            'email_from': kwargs.get('friend_email'),
            'phone': kwargs.get('friend_phone') if kwargs.get(
                'friend_phone') else '',
            'referral_product_ids': products.ids,
            'referral_product_count': len(products),
            'referred': request.env.user.partner_id.name
        })

        template = request.env.ref(
            'cyllo_crm_advance_lead.mail_template_referral_friend',
            raise_if_not_found=False)
        if template and kwargs.get('friend_email'):
            template.sudo().with_context(
                friend_name=kwargs.get('friend_name'),
                referrer_name=request.env.user.partner_id.name,
                product_list=products,
            ).send_mail(lead.id)

        return request.render('cyllo_crm_advance_lead.referral_thank_you')
