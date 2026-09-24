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


class DomainAccess(models.Model):
    _name = 'domain.access'
    _description = 'Domain Access'
    _rec_name = 'model_id'

    profile_management_id = fields.Many2one(
        'profile.management',
        string='Profile Management ID',
        help="The profile management record this domain rule belongs to."
    )
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        help="The Cyllo model to which this domain rule applies."
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Model Name',
        help="Technical name of the target Cyllo model."
    )

    domain = fields.Text(
        default='[]',
        string='Domain',
        help="Python/domain expression to filter records (e.g. [('state', '=', 'draft')])."
    )

    @api.constrains('domain')
    def _check_domain(self):
        """Validate that the domain field is not empty."""
        for record in self:
            if record.domain == '[]':
                raise ValidationError('Domain cannot be empty')
