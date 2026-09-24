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
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProjectTask(models.Model):
    _inherit = 'project.task'


    allow_task_products = fields.Boolean(
        related='project_id.allow_task_products'
    )
    allow_extra_quotations = fields.Boolean(
        related='project_id.allow_extra_quotations'
    )
    extra_quotation_ids = fields.One2many(
        'sale.order', 'task_id',
        string="Extra Quotations",
        domain=[('is_task_extra_quotation', '=', True)],
    )
    extra_quotation_count = fields.Integer(
        compute='_compute_extra_quotation_count',
        string="Quotation Count",
    )

    related_sale_order_id = fields.Many2one("sale.order", string="Consume products in")


    @api.depends('extra_quotation_ids')
    def _compute_extra_quotation_count(self):
        """Compute the number of extra quotations linked to each task."""
        for task in self:
            task.extra_quotation_count = len(task._get_task_extra_quotations())


    def action_view_task_products(self):
        """Open the product catalog for the selected sales order or quotation."""
        self.ensure_one()
        if not self.related_sale_order_id:
            raise ValidationError("Choose a Sale order or Quotation to consume the Products.")

        return self.related_sale_order_id.with_context(
            {},
            order_id=self.related_sale_order_id.id,
            default_project_task_product_id=self.id,
        ).action_add_from_catalog()



    def _get_task_extra_quotations(self):
        """Retrieve all extra quotations linked to the current task."""
        self.ensure_one()
        return self.env['sale.order'].search([
            ('task_id', '=', self.id),
            ('is_task_extra_quotation', '=', True),
        ])

    def _get_product_catalog_sale_order_values(self, partner):
        """Prepare values for creating a quotation from the task product catalog."""
        self.ensure_one()
        return {
            'partner_id': partner.id,
            'task_id': self.id,
            'analytic_account_id': self.project_id.analytic_account_id.id if self.project_id.analytic_account_id else False,
        }


    def action_task_new_quotation(self):
        """Create a new extra quotation for the current task."""
        self.ensure_one()
        partner = self.partner_id or self.project_id.partner_id
        if not partner:
            raise UserError(_("Please set a Customer on the task or project before creating a quotation."))

        sale_order = self.env['sale.order'].create({
            **self._get_product_catalog_sale_order_values(partner),
            'is_task_extra_quotation': True,
        })

        return {
            'name': _('Sales Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': sale_order.id,
            'target': 'current',
        }

    def action_view_extra_quotations(self):
        """ Open the extra quotations associated with the current task."""
        self.ensure_one()
        quotations = self._get_task_extra_quotations()
        action = {
            'name': _('Quotations'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', quotations.ids)],
            'context': {
                'default_partner_id': (self.partner_id or self.project_id.partner_id).id,
                'default_task_id': self.id,
            },
        }
        if len(quotations) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = quotations.id
        return action
