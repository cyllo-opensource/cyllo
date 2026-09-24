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


class CommissionType(models.Model):
    """Commission type which helps to compute Commission"""
    _name = 'commission.type'
    _description = "Commission type will help to compute Commission based of conditions"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, copy=False)
    active = fields.Boolean(string='Active', default=True)
    type = fields.Selection(
        selection=[
            ('crm', 'Lead'),
            ('sale', 'Sale')
        ],
        default='sale',
        required=True,
    )
    crm_rule_to_apply = fields.Char(string="Rule",
                                    help="Set Rules to filter the records")
    sales_rule_to_apply = fields.Char(string="Rule",
                                      help="Set Rules to filter the records")

    user_id = fields.Many2one('res.users', string='User',
                              default=lambda self: self.env.user,
                              )

    @api.constrains('crm_rule_to_apply', 'sales_rule_to_apply')
    def _validate_domain_syntax(self):
        """Ensure domain syntax is valid when saving."""
        for rec in self:
            for field_name in ['crm_rule_to_apply', 'sales_rule_to_apply']:
                domain_str = rec[field_name]
                if domain_str:
                    try:
                        eval(domain_str)
                    except Exception as e:
                        raise ValidationError(
                            f"Invalid domain syntax in field '{field_name}': {e}")

    @api.onchange('type')
    def _onchange_type(self):
        """Reset the rule field based on the type selected."""
        if self.type == 'crm':
            self.sales_rule_to_apply = ""
        else:
            self.crm_rule_to_apply = ""
