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
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class CarbonAssignationRule(models.Model):
    _name = 'carbon.assign.rule'
    _description = 'Emission Assignation Rule'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'priority, name'

    name = fields.Char(required=True, help="Enter a descriptive name for the assignment rule.")
    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade', readonly=True,
                default=lambda self: self.env['ir.model'].search([('model', '=', 'carbon.activity')], limit=1))
    domain = fields.Char(help='Domain string applied to target records.')
    source_id = fields.Many2one('carbon.source', required=True, ondelete='restrict',
                                help="Select the emission source to assign when this rule matches.")
    factor_id = fields.Many2one('carbon.factor', ondelete='restrict', domain="[('source_id', '=', source_id)]",
                                help="Select the emission factor to apply when the method is 'Factor'.")
    gas_id = fields.Many2one('carbon.gas', ondelete='restrict',
                             help="Greenhouse gas assigned to matching activities. Leave empty to "
                                  "use the gas of the selected factor; set it to attribute a gas on "
                                  "rules that carry no factor.")
    method = fields.Selection([
        ('factor', 'Factor'),
        ('direct', 'Direct'),
    ], default='factor', required=True, help="Choose how emissions are calculated")
    priority = fields.Integer(default=10, help="Set the priority of this rule. Rules with lower priority values are evaluated first.")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    note = fields.Text(help="Add any additional information or remarks about this assignment rule.")

    @api.onchange('factor_id')
    def _onchange_factor_id(self):
        """Suggest the factor's gas so the rule shows what it will assign."""
        if self.factor_id.gas_id:
            self.gas_id = self.factor_id.gas_id

    @api.constrains('method', 'factor_id')
    def _check_factor_required(self):
        """Ensure an emission factor is selected when the Factor method is used."""
        for rec in self:
            if rec.method == 'factor' and not rec.factor_id:
                raise ValidationError('Factor is required for Factor method.')

    def _get_domain(self):
        """Evaluate and return the assignment rule domain."""
        self.ensure_one()
        if not self.domain:
            return []
        try:
            return safe_eval(self.domain)
        except Exception:
            return []

    def _match(self, record):
        """Check whether the given record matches the assignment rule domain."""
        self.ensure_one()
        domain = self._get_domain()
        return record.filtered_domain(domain)
