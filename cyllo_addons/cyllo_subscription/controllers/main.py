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
from odoo import _, fields, http
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.sale.controllers.portal import CustomerPortal

class MyCustomerPortal(CustomerPortal):

    def _prepare_quotations_domain(self, partner):
        # Get the original domain you shared
        domain = super()._prepare_quotations_domain(partner)
        # Add the filter to exclude subscription orders
        domain.append(('is_subscription', '=', False))
        return domain

    def _prepare_orders_domain(self, partner):
        # Get the original domain you shared
        domain = super()._prepare_orders_domain(partner)
        # Add the filter to exclude subscription orders
        domain.append(('is_subscription', '=', False))
        return domain

class SubscriptionPortal(CustomerPortal):
    """ Class to define the portal views """

    def _prepare_home_portal_values(self, counters):
        """ Function to get the count of total number of orders """
        vals = super()._prepare_home_portal_values(counters)
        if 'subscription_count' in counters:
            vals['subscription_count'] = request.env[
                'subscription.order'].sudo().search_count(
                [('partner_id', '=', request.env.user.partner_id.id)])
        return vals


class PortalControl(CustomerPortal):
    """Class created to render datas to portal"""

    @http.route(['/your_sub_orders'], type='http', auth="public", website=True)
    def _portal_sub_order_tree(self):
        """Method used to return datas to create a tree view with orders of the current user in the portal"""
        subscription_ids = request.env['subscription.order'].sudo().search(
            [('partner_id', '=', request.env.user.partner_id.id),
             ('state', 'in', ['posted', 'sale', 'requested'])], order='create_date desc')
        values = {
            'orders': subscription_ids,
            'active_records': subscription_ids.filtered(
                lambda sub: sub.state_subscription == 'active'),
            'to_renew': subscription_ids.filtered(
                lambda sub: sub.state_subscription == 'renew'),
            'churned': subscription_ids.filtered(
                lambda sub: sub.state_subscription == 'churned'),
            'trial': subscription_ids.filtered(
                lambda sub: sub.state_subscription == 'trial'),
            'requested_orders': subscription_ids.filtered(lambda sub: sub.state== 'requested'),
            'page_name': 'Subscription Orders',
        }
        return request.render("cyllo_subscription.subscription_orders", values)

    @http.route(['/details/<int:order_id>'], type='http', auth='public',
                website=True)
    def _portal_sub_order_form(self, order_id, report_type=None,
                               access_token=None, download=True):
        """Method to render data to the details page of the portal"""
        current_record = request.env['subscription.order'].sudo().browse(
            order_id)
        existing_order = request.env['subscription.order'].sudo().search([
            ('parent_id', '=', current_record.id),
            ('state_subscription', '=', 'active')], limit=1)

        values = {
            'each_order': current_record,
            'reasons': request.env[
                'subscription.order.close.reason'].sudo().search(
                [('available_in_portal', '=', True)]),
            'existing_order': bool(existing_order),
            'page_name': 'Details'
        }
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(
                model=current_record,
                report_type=report_type,
                report_ref='cyllo_subscription.subscription_report',
                download=download,
            )
        return request.render('cyllo_subscription.subscription_details', values)

    @http.route(['/your_sub_orders/close/<int:order_id>'], type='http',
                auth='public', website=True)
    def _subscription_close(self, order_id, **kwargs):
        """Method render values to the subscription close page"""
        record = request.env['subscription.order'].sudo().browse(order_id)
        records = {
            'page_name': 'Close order',
            'order': record,
            'orders': record
        }
        record.state_subscription = 'churned'
        if kwargs.get('custom_reason'):
            record.message_post(body=_('Reason to close the subscription: %s',
                                       kwargs.get('custom_reason')),
                                message_type='comment',
                                subtype_xmlid='mail.mt_comment')
        else:
            record.message_post(body=_('Reason to close the subscription: %s',
                                       kwargs.get('reasons')),
                                message_type='comment',
                                subtype_xmlid='mail.mt_comment')
        return request.render('cyllo_subscription.subscription_closed', records)

    @http.route(['/renew_sub'], type='http', auth='public', website=True)
    def renew_order(self, **kwargs):
        """Method used to render values to renew subscription from portal"""

        old_order = request.env['subscription.order'].sudo().browse(int(kwargs.get('order_id')))
        
        today = fields.Datetime.now()
        new_renewal_date = old_order.renewal_date
        
        if new_renewal_date:
            if new_renewal_date.year < today.year or (new_renewal_date.year == today.year and new_renewal_date.month < today.month):
                new_renewal_date = today
        else:
            new_renewal_date = today

        new_order = request.env['subscription.order'].sudo().create({
            'partner_id': kwargs.get('partner'),
            'time_based_price_id': kwargs.get('plan'),
            'state': 'requested',
            'state_subscription': 'active',
            'parent_id' :kwargs.get('order_id'),
            'sale_order_id': old_order.sale_order_id.id,
            'renewal_date': new_renewal_date,
            'sale_order_template_id': kwargs.get('sale_order_template_id'),
            'subscription_order_line_ids': [(fields.Command.create({
                'product_id': kwargs.get('product'),
                'time_based_price_id': kwargs.get('plan'),
                'subtotal': old_order.subscription_order_line_ids[:1].subtotal if old_order.subscription_order_line_ids else 0.0,
                'quantity' : int(kwargs.get('quantity', 1)),
                'tax_ids' : old_order.subscription_order_line_ids[:1].tax_ids.ids if old_order.subscription_order_line_ids else [],
                'total_price' : old_order.subscription_order_line_ids[:1].total_price if old_order.subscription_order_line_ids else 0.0

        }))]})
        return request.redirect(f"/details/{new_order.id}")
