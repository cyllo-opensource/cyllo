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


class FieldAccess(models.Model):
    _name = 'field.access'
    _description = 'Field Access'
    _rec_name = 'model_id'

    profile_management_id = fields.Many2one(
        'profile.management',
        string='Profile Management ID',
        help="The profile management record this field access rule belongs to."
    )
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        help="The Cyllo model containing the target field."
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Model Name',
        help="Technical name of the target Cyllo model."
    )
    field_id = fields.Many2one(
        'ir.model.fields',
        string='Field',
        required=True,
        ondelete='cascade',
        help="The specific field to which access rules apply."
    )
    field_attribute = fields.Selection(
        string="Field Attribute",
        selection=[('readonly', 'Readonly'),
                  ('invisible', 'Invisible'),
                  ('required', 'Required'),
                  ('remove_link', 'Remove External Link'),
                  ],
        default='readonly',
        required=True,
        help="Action to apply to the field: Readonly, Invisible, Required, or Remove External Link."
    )
    domain = fields.Text(
        default='[]',
        string='Domain',
        help="Optional Python/domain expression to conditionally apply this rule."
    )
