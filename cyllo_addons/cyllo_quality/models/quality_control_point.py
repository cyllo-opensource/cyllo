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
from odoo.exceptions import ValidationError


class QualityControlPoint(models.Model):
    _name = 'quality.control.point'
    _description = 'Quality Control Points'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='', readonly=True, tracking=True, copy=False)
    operation_type_ids = fields.Many2many('stock.picking.type',
                                          string='Operations', tracking=True,
                                          required=True)
    product_category_ids = fields.Many2many('product.category',
                                            string='Product Categories',
                                            tracking=True,
                                            help= "Quality Point will apply to every products in the selected product categories")
    product_ids = fields.Many2many('product.product', string='Products',
                                   tracking=True, help="Quality point will be applied to product")
    qc_check_for = fields.Selection(
        [('product', 'Products'), ('category', 'Category')],
        string='Quality Check For',
        default='')
    user_id = fields.Many2one('res.users', string='Responsible',
                              compute="_compute_user_id", store=True,
                              readonly=False,
                              default=lambda self: self.env.user)
    quality_team_id = fields.Many2one('quality.team', string='Team',
                                      tracking=True)
    quality_inspection_ids = fields.One2many('quality.inspection',
                                             'quality_control_id',
                                             string='Inspection')
    active = fields.Boolean(default=True, tracking=True, copy=False)
    control_type = fields.Selection([
        ('operation', 'Operation'),
        ('product', 'Product'),
        ('quantity', 'Quantity')
    ], default='operation', required=True, tracking=True,
    help="Operation : Quality check is requested at Operation Level."
         "Product : Quality check is requested for product"
        "Quantity : Quality checkis requested for each new product quantity")
    control_by = fields.Selection([
        ('all', 'All'),
        ('randomly', 'Randomly'),
        ('periodically', 'Periodically')
    ], default='all', required=True, tracking=True,)
    control_frequency = fields.Integer(string='Control Frequency')
    control_period = fields.Selection(
        [('day', 'Day'), ('week', 'Week'), ('month', 'Month')], default='day')
    control_quantity = fields.Integer()

    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, tracking=True)
    qc_check_count = fields.Integer(compute='_compute_quality_checks')
    failure_location_id = fields.Many2one('stock.location',
                                          string='Failure Location')
    is_measure= fields.Boolean(string="Is measurable type", compute="_compute_is_measure")

    @api.depends("quality_inspection_ids.is_measure")
    def _compute_is_measure(self):
        for record in self:
            record.is_measure = any(record.quality_inspection_ids.mapped("is_measure"))

    @api.model
    def create(self, vals):
        """Override create to add reference and send notification"""
        if vals.get('name', '') == '':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'quality.control.point') or ''

        # Create the record
        result = super(QualityControlPoint, self).create(vals)

        # Send notification email if quality team is assigned
        if vals.get('quality_team_id'):
            if result.quality_team_id.is_mail:
                template = self.env.ref(
                    'cyllo_quality.mail_template_quality_control_notification')
                if template:
                    # Prepare context for email template
                    ctx = {
                        'team_leader': result.quality_team_id.leader_id.name,
                        'name': result.name,
                        'control_type': dict(
                            self._fields['control_type'].selection).get(
                            result.control_type),
                        'team': result.quality_team_id.name,
                        'control_by': dict(
                            self._fields['control_by'].selection).get(
                            result.control_by),
                        'operations': ', '.join(
                            result.operation_type_ids.mapped('name')),

                    }

                    # Add conditional fields
                    if result.control_frequency:
                        ctx.update({
                            'frequency': result.control_frequency,
                            'period': dict(
                                self._fields['control_period'].selection).get(
                                result.control_period)
                        })

                    if result.qc_check_for == 'product':
                        ctx.update({'products': ', '.join(
                            result.product_ids.mapped('name'))})
                    elif result.qc_check_for == 'category':
                        ctx.update({'categories': ', '.join(
                            result.product_category_ids.mapped('name'))})

                    # Send mail with context
                    template.with_context(ctx).send_mail(result.id,
                                                         force_send=True)

        return result

    @api.depends('quality_team_id')
    def _compute_user_id(self):
        for qcp in self:
            if qcp.quality_team_id.leader_id.user_id:
                qcp.user_id = qcp.quality_team_id.leader_id.user_id.id
            elif not qcp.user_id:
                qcp.user_id = self.env.user

    def _compute_quality_checks(self):
        """Compute quality checks count"""
        for qcp in self:
            qcp.qc_check_count = self.env['quality.check'].search_count(
                [('quality_control_id', '=', qcp.id)])

    @api.constrains('quality_inspection_ids')
    def _check_quality_inspection_ids(self):
        for record in self:
            if not record.quality_inspection_ids:
                raise ValidationError(
                    "You must add at least one Quality Inspection line before saving.")

    def action_view_quality_checks(self):
        """Action view quality checks"""
        quality_check = self.env['quality.check'].search(
            [('quality_control_id', '=', self.id)])
        return {
            'name': 'Quality Checks',
            'view_mode': 'tree,form',
            'res_model': 'quality.check',
            'domain': [('id', 'in', quality_check.ids)],
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def is_matching_product(self, product, all_category_id=None):
        """Evaluate whether this Quality Control Point matches a given product."""
        self.ensure_one()
        if not self.product_ids and not self.product_category_ids:
            return True
        if self.qc_check_for == 'category' or (self.product_category_ids and not self.product_ids):
            if not self.product_category_ids:
                return True
            if all_category_id and all_category_id in self.product_category_ids.ids:
                return True
            categ = product.categ_id
            if categ and (categ.id in self.product_category_ids.ids or (categ.parent_id and categ.parent_id.id in self.product_category_ids.ids)):
                return True
            return False
        if self.qc_check_for == 'product' or self.product_ids:
            if not self.product_ids:
                return True
            return product.id in self.product_ids.ids
        return False

