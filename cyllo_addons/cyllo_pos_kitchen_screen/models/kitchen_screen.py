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
from odoo.exceptions import ValidationError


class KitchenScreenStage(models.Model):
    """Kitchen Screen Stage model for dynamic stages"""
    _name = 'kitchen.screen.stage'
    _description = 'Kitchen Screen Stage'
    _order = 'sequence'

    name = fields.Char(string='Stage Name', required=True)
    is_done = fields.Boolean(string='Is Completed Stage', default=False)
    is_cancelled = fields.Boolean(string='Is Cancelled Stage', default=False)
    image = fields.Binary(string='Stage Image')
    stage_color = fields.Char(string='Color', default='#000000')
    sequence = fields.Integer(string='Sequence', default=10)
    kitchen_screen_id = fields.Many2one('kitchen.screen', string='Kitchen Screen', ondelete='cascade')
    company_id = fields.Many2one(
        'res.company', string='Company',
        related='kitchen_screen_id.company_id', store=True,
        index=True)

    @api.constrains('is_done', 'is_cancelled')
    def _check_stage_flags(self):
        """A stage cannot be both completed and cancelled, and only one of each is allowed per screen"""
        for rec in self:
            if rec.is_done and rec.is_cancelled:
                raise ValidationError("A kitchen stage cannot be both 'Completed' and 'Cancelled'.")
            
            if rec.is_done:
                if any(s.is_done and s._origin != rec._origin for s in rec.kitchen_screen_id.stage_ids):
                    raise ValidationError("Only one stage can be marked as 'Completed'.")
                    
            if rec.is_cancelled:
                if any(s.is_cancelled and s._origin != rec._origin for s in rec.kitchen_screen_id.stage_ids):
                    raise ValidationError("Only one stage can be marked as 'Cancelled'.")


class KitchenScreen(models.Model):
    """Kitchen Screen model for the cook"""
    _name = 'kitchen.screen'
    _description = 'Pos Kitchen Screen'
    _rec_name = 'sequence'

    def _pos_shop_id(self):
        """Domain for the Pos Shop"""
        return [('module_pos_restaurant', '=', True)]

    sequence = fields.Char(readonly=True, default='New',
                           copy=False, tracking=True, help="Sequence of items")
    pos_config_id = fields.Many2one('pos.config', string='Allowed POS',
                                    help="Allowed POS for kitchen" ,required=True)
    pos_categ_ids = fields.Many2many('pos.category',
                                     string='Allowed POS Category',
                                     help="Allowed POS Category"
                                          "for the corresponding Pos")
    allowed_pos_categ_ids = fields.Many2many('pos.category',
                                             compute='_compute_allowed_pos_categ_ids',
                                             string='Allowed POS Category Domain')
    shop_number = fields.Integer(related='pos_config_id.id', string='Customer',
                                 help="Id of the POS")
    stage_ids = fields.One2many('kitchen.screen.stage', 'kitchen_screen_id',
                                string='Stages', help="Dynamic stages for the kitchen screen")
    company_id = fields.Many2one(
        'res.company', string='Company',
        required=True, index=True,
        default=lambda self: self.env.company)

    @api.constrains('pos_config_id')
    def _check_unique_pos_config(self):
        """Ensure only one kitchen screen is allowed per POS/shop"""
        for rec in self:
            if rec.pos_config_id:
                duplicate = self.search([
                    ('pos_config_id', '=', rec.pos_config_id.id),
                    ('id', '!=', rec.id),
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        "A kitchen screen already exists for '%s'. "
                        "Only one kitchen screen is allowed per Point of Sale."
                        % rec.pos_config_id.display_name)

    def kitchen_screen(self):
        """Redirect to corresponding kitchen screen for the cook"""
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': '/pos/kitchen?pos_config_id= %s' % self.pos_config_id.id,
        }

    @api.model
    def create(self, vals):
        """Used to create sequence and default stages"""
        if vals.get('sequence', 'New') == 'New':
            vals['sequence'] = self.env['ir.sequence'].next_by_code(
                'kitchen.screen')

        # Add default stages if no stages are provided
        if not vals.get('stage_ids'):
            vals['stage_ids'] = [
                (0, 0, {
                    'name': 'Draft',
                    'is_done': False,
                    'is_cancelled': False,
                    'sequence': 1,
                    'stage_color': '#3498db',
                }),
                (0, 0, {
                    'name': 'Completed',
                    'is_done': True,
                    'is_cancelled': False,
                    'sequence': 100,
                    'stage_color': '#2ecc71',
                }),
                (0, 0, {
                    'name': 'Cancelled',
                    'is_done': False,
                    'is_cancelled': True,
                    'sequence': 101,
                    'stage_color': '#e74c3c',
                }),
            ]

        result = super(KitchenScreen, self).create(vals)
        return result

    @api.constrains('stage_ids')
    def _check_stages(self):
        """Ensures that each kitchen screen has one completed and one cancelled stage"""
        for rec in self:
            completed_stages = rec.stage_ids.filtered(lambda s: s.is_done)
            cancelled_stages = rec.stage_ids.filtered(lambda s: s.is_cancelled)
            if len(completed_stages) != 1:
                raise ValidationError(
                    "Each kitchen screen must have exactly one stage marked as 'Completed'.")
            if len(cancelled_stages) != 1:
                raise ValidationError(
                    "Each kitchen screen must have exactly one stage marked as 'Cancelled'.")

    @api.depends('pos_config_id')
    def _compute_allowed_pos_categ_ids(self):
        """Compute allowed categories based on POS restriction"""
        for rec in self:
            if rec.pos_config_id:
                if rec.pos_config_id.limit_categories and rec.pos_config_id.iface_available_categ_ids:
                    categ_ids = self.env['pos.category'].search([
                        ('id', 'child_of', rec.pos_config_id.iface_available_categ_ids.ids)
                    ]).ids
                else:
                    products = self.env['product.product'].search([
                        ('available_in_pos', '=', True),
                    ])
                    categ_ids = products.mapped('pos_categ_ids').ids
                rec.allowed_pos_categ_ids = [(6, 0, categ_ids)]
            else:
                rec.allowed_pos_categ_ids = [(5, 0, 0)]

    @api.onchange('pos_config_id')
    def _onchange_pos_config_id(self):
        """Clear categories when POS changes"""
        self.pos_categ_ids = [(5, 0, 0)]