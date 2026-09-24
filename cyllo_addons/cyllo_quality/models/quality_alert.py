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
from odoo import api, fields, models


class QualityAlert(models.Model):
    _name = 'quality.alert'
    _description = 'Quality Alerts'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(default='', readonly=True, copy=False)
    quality_check_id = fields.Many2one('quality.check', required=True)
    quality_check_line_id = fields.Many2one('quality.check.line')
    product_id = fields.Many2one('product.product', string="Variants", readonly=True, copy=False)
    product_template_id = fields.Many2one(
        'product.template', string='Product',
        compute='_compute_product_template_id', store=True, readonly=False, copy=False)
    picking_id = fields.Many2one('stock.picking', readonly=True, copy=False)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    quality_team_id = fields.Many2one('quality.team', string='Team')
    description = fields.Html(string="Issue Description",)
    corrective_action = fields.Html(string="Corrective Action",)
    preventive_action = fields.Html(string="Preventive Action",)
    stage_id = fields.Many2one('quality.alert.stage', group_expand='read_group_stage_ids',
                               default=lambda self: self.env.ref('cyllo_quality.quality_alert_stage_quarantine').id)
    date = fields.Date(default=fields.Date.context_today, required=True)
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, help='Select the company')
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')])
    color = fields.Integer(string='Color Index')

    @api.depends('product_id', 'quality_check_id.product_id')
    def _compute_product_template_id(self):
        for record in self:
            product = record.product_id or (record.quality_check_id and record.quality_check_id.product_id)
            record.product_template_id = product.product_tmpl_id if product else False

    @api.onchange('quality_check_id')
    def _onchange_quality_check_id(self):
        if self.quality_check_id:
            self.update({
                'product_id': False,
                'product_template_id': False,
                'picking_id': False,
                'quality_team_id': False,
            })
            if self.quality_check_id.quality_team_id:
                self.quality_team_id= self.quality_check_id.quality_team_id
            if self.quality_check_id.product_id:
                self.product_id = self.quality_check_id.product_id
                self.product_template_id = self.quality_check_id.product_id.product_tmpl_id
            if self.quality_check_id.picking_id:
                self.picking_id = self.quality_check_id.picking_id

    @api.model
    def create(self, vals):
        """Supering create function to add reference"""
        if vals.get('name', '') == '':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'quality.alert') or ''
        if vals.get('quality_check_id') and not vals.get('product_id'):
            qc = self.env['quality.check'].browse(vals['quality_check_id'])
            if qc.product_id:
                vals['product_id'] = qc.product_id.id
        if vals.get('product_id') and not vals.get('product_template_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            vals['product_template_id'] = product.product_tmpl_id.id
        return super(QualityAlert, self).create(vals)

    @api.model
    def read_group_stage_ids(self, stage_id, domain, order):
        return self.env['quality.alert.stage'].search([])

