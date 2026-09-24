# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """
        Automatically create intercompany vendor bills when customer invoices
        are posted.

        For invoices originating from intercompany Sale Orders, the system
        locates the linked Purchase Order in the other company and creates
        the corresponding vendor bill if one does not already exist.
        If no Sale Order is attached but the customer is another company, 
        a bill is created directly with the same lines, raising an error if 
        any product does not exist in the target company.
        Duplicate bill creation is prevented through origin checks.
        """
        res = super().action_post()
        create_bills = self.env['ir.config_parameter'].sudo().get_param(
            'cyllo_intercompany_transfer.create_vendor_bills'
        )
        if not create_bills:
            return res
            
        invoices = self.filtered(lambda m: m.move_type == 'out_invoice')
        for invoice in invoices:
            sale_order = invoice.invoice_line_ids.sale_line_ids.order_id[:1]
            if sale_order:
                purchase_order = sale_order.sudo().intercompany_purchase_order_id
                if not purchase_order:
                    continue
                existing_bills = self.env['account.move'].sudo().search([
                    ('move_type', '=', 'in_invoice'),
                    ('invoice_origin', '=', purchase_order.name),
                    ('company_id', '=', purchase_order.company_id.id),
                ], limit=1)
                if existing_bills:
                    continue
                purchase_order.with_company(
                    purchase_order.company_id
                ).sudo().action_create_invoice()
            else:
                target_company = self.env['res.company'].sudo().search([('partner_id', '=', invoice.partner_id.id)], limit=1)
                if not target_company:
                    continue
                
                existing_bills = self.env['account.move'].sudo().search([
                    ('move_type', '=', 'in_invoice'),
                    ('invoice_origin', '=', invoice.name),
                    ('company_id', '=', target_company.id),
                ], limit=1)
                
                if existing_bills:
                    continue
                    
                invoice_vals = {
                    'move_type': 'in_invoice',
                    'company_id': target_company.id,
                    'partner_id': invoice.company_id.partner_id.id,
                    'invoice_origin': invoice.name,
                    'invoice_date': invoice.invoice_date,
                    'invoice_line_ids': [],
                }
                
                for line in invoice.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note')):
                    if line.product_id and line.product_id.company_id and line.product_id.company_id.id != target_company.id:
                        raise UserError(_("The product '%s' is restricted to company '%s' and cannot be used in the intercompany bill for '%s'.") % (
                            line.product_id.name, line.product_id.company_id.name, target_company.name
                        ))
                        
                    line_vals = {
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'quantity': line.quantity,
                        'price_unit': line.price_unit,
                        'discount': line.discount,
                    }
                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
                    
                self.env['account.move'].with_company(target_company).sudo().create(invoice_vals)

        return res
