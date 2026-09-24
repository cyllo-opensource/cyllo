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
from odoo import _, Command, fields, models


class CrmLead(models.Model):
    """Inherits the base crm.lead model for lead creation for wishlist products."""
    _inherit = 'crm.lead'

    is_advance_lead = fields.Boolean(string='Cyllo Advance lead')
    wishlist_product_ids = fields.Many2many(comodel_name='product.product',
                                            string='Wishlist Products')
    wishlist_ids = fields.One2many(comodel_name='product.wishlist',
                                   inverse_name='lead_id')
    wishlist_product_count = fields.Integer(string='Count')
    referral_product_ids = fields.Many2many(comodel_name='product.product',
                                            string='Referred Products',
                                            relation='crm_lead_products_rel',
                                            column1='lead_id',
                                            column2='product_id', )
    referral_product_count = fields.Integer(string='Count')
    count = fields.Integer(compute='_compute_count',
                           string="Count",
                           help="Total number of Automations")

    def _prepare_opportunity_quotation_context(self):
        """ Extend the context to include default sale order lines from CRM lead. """
        quotation_context = super()._prepare_opportunity_quotation_context()
        order_lines = []
        products = self.wishlist_product_ids or self.referral_product_ids
        if products:
            for product in products:
                order_lines.append(Command.create({
                    'product_id': product.id,
                    'name': product.name,
                    'product_uom_qty': 1,
                    'price_unit': product.lst_price,
                }))
        quotation_context['default_order_line'] = order_lines
        return quotation_context

    def _compute_count(self):
        """Function for finding the count of automations"""
        if self.is_installed:
            model = self.env['ir.model'].sudo().search(
                [('model', '=', self._name)],
                limit=1
            )
            domain = f"[('id', '=', {self.id})]"
            self.count = self.env['base.automation'].sudo().search_count(
                [('filter_pre_domain', '=', domain),
                 ('model_id', '=', model.id)])
        else:
            self.count = 0

    def action_view_abandoned_sale_quotation(self):
        """Action to view abandoned sale orders"""
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Abandoned Sale Orders',
            'view_mode': 'list,form',
            'res_model': 'sale.order',
            'domain': [('id', 'in', self.order_ids.ids)],
        }
        if len(self.order_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.order_ids.id,
            })
        return action

    def action_view_wishlist_products(self):
        """Action to view abandoned wishlist products"""
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Wishlist Products',
            'view_mode': 'list,form',
            'res_model': 'product.product',
            'domain': [('id', 'in', self.wishlist_product_ids.ids)],
        }
        if len(self.wishlist_product_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.wishlist_product_ids.id,
            })
        return action

    def action_view_referral_products(self):
        """Action to view referred products by a customer to his friend"""
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Wishlist Products',
            'view_mode': 'list,form',
            'res_model': 'product.product',
            'domain': [('id', 'in', self.referral_product_ids.ids)],
        }
        if len(self.wishlist_product_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.referral_product_ids.id,
            })
        return action

    def action_create_automation(self):
        """function for creating automation"""
        model = self.env['ir.model'].sudo().search(
            [('model', '=', self._name)],
            limit=1
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Automation'),
            'res_model': 'base.automation',
            'view_mode': 'form',
            'target': 'new',
            'views': [(
                self.env.ref(
                    'cyllo_crm_advance_lead.view_base_automation_quick_form'
                ).id,
                'form'
            )],
            'context': {
                'default_model_id': model.id if model else False,
                'default_trigger': 'on_time',
                'default_filter_pre_domain': "[('id', '=', %d)]" % self.id,
                'default_temporary_filter_pre_domain': "[('id', '=', %d)]" % self.id,
            },
        }

    def action_get_automation(self):
        """Action for getting the popup view of all related changes of current lead"""
        model = self.env['ir.model'].sudo().search(
            [('model', '=', self._name)],
            limit=1
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Automation'),
            'res_model': 'base.automation',
            'domain': [
                ('filter_pre_domain', '=', "[('id', '=', %d)]" % self.id),
                ('model_id', '=', model.id)],
            'view_mode': 'tree',
            'target': 'current',
            'order': 'id asc',
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
            },
        }

    def _create_lead_for_wishlist_products(self):
        """ Daily job for check and create lead for abandoned wishlist"""
        config = self.env['ir.config_parameter'].sudo()
        if config.get_param(
                'cyllo_crm_advance_lead.create_lead_wishlist') == 'True':
            partners = self.env['res.partner'].search(
                [('wishlist_ids', '!=', False)])
            abandoned_wishlist_days = int(
                config.get_param('cyllo_crm_advance_lead.wishlist_days', '0'))
            today = fields.datetime.now()
            for partner in partners:
                abandoned_wishlist = partner.wishlist_ids.filtered(
                    lambda o: (
                                      today - o.create_date).days >= abandoned_wishlist_days and not o.lead_id)
                products = self.env['product.product'].search([
                    ('id', 'in', abandoned_wishlist.mapped('product_id').ids)
                ])
                if abandoned_wishlist:
                    lead = self.env['crm.lead'].sudo().create({
                        'is_advance_lead': True,
                        'name': f'Wishlist Products {partner.name}',
                        'type': 'lead',
                        'wishlist_product_ids': products,
                        'wishlist_product_count': len(products),
                        'partner_id': partner.id
                    })
                    abandoned_wishlist.write({
                        'lead_id': lead.id
                    })

    def _create_lead_for_abandoned_cart(self):
        """Daily job for check and create lead for abandoned cart"""
        config = self.env['ir.config_parameter'].sudo()
        if config.get_param(
                'cyllo_crm_advance_lead.create_lead_abandoned_cart') == 'True':
            abandoned_orders = self.env['sale.order'].sudo().search(
                [('is_abandoned_cart', '=', True)])
            partners = self.env['res.partner'].search([
                ('id', 'in', abandoned_orders.mapped('partner_id').ids)
            ])
            abandoned_cart_days = int(
                config.get_param('cyllo_crm_advance_lead.abandoned_cart_days',
                                 '0'))
            today = fields.datetime.now()
            for partner in partners:
                website_visitor = self.env['website.visitor'].sudo().search(
                    [('partner_id', '=', partner.id)])
                if website_visitor:
                    abandoned_carts = self.env['sale.order'].sudo().search(
                        [('is_abandoned_cart', '=', True),
                         ('partner_id', '=', partner.id),
                         ('opportunity_id', '=', False)])
                    if abandoned_carts:
                        overdue_orders = abandoned_carts.filtered(
                            lambda o: (
                                              today - o.date_order).days >= abandoned_cart_days)
                        lead = self.env['crm.lead'].sudo().create({
                            'is_advance_lead': True,
                            'name': f"{partner.name}'s Abandoned Cart",
                            'type': 'lead',
                            'partner_id': partner.id,
                        })
                        overdue_orders.write({
                            'opportunity_id': lead.id
                        })
