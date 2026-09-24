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


class CarbonEmissionFactor(models.Model):
    _name = 'carbon.factor'
    _description = 'Emission Factor'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'name'

    name = fields.Char(required=True, help="Name of the emission factor.")
    source_id = fields.Many2one('carbon.source', required=True, ondelete='restrict',help="Emission source associated with this factor.")
    gas_id = fields.Many2one('carbon.gas', ondelete='restrict', help="Greenhouse gas associated with this emission factor.")
    factor_value = fields.Float(required=True, help="Emission factor value used for emission calculations.")
    unit_name = fields.Many2one('carbon.unit', string='Unit', help="Unit of measurement for the emission factor.")
    valid_from = fields.Date(help="Date from which this emission factor is valid.")
    valid_to = fields.Date(help="Date until which this emission factor is valid.")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    note = fields.Text(help="Additional notes or remarks about this emission factor.")
    type = fields.Selection([('air', 'Air'),('sound', 'Sound'),('water', 'Water')], required=True, help="Type of emission this factor is used to calculate.")
    ipcc_efdb_id = fields.Char(string='IPCC EFDB ID', help='The official ID from the IPCC Emission Factor Database')
    ipcc_code = fields.Char(string='IPCC Category Code', help='IPCC category code (e.g. 1.A.1, 1.A.3)')
    gwp_reference = fields.Char(string='GWP Reference', help='Global Warming Potential reference report (e.g. AR5, AR6)', default='AR5')

    @api.constrains('valid_from', 'valid_to')
    def _check_valid_dates(self):
        """Validate and check valid dates."""
        for rec in self:
            if rec.valid_from and rec.valid_to and rec.valid_to < rec.valid_from:
                raise ValidationError('Valid To must be after Valid From.')

    def _is_valid_on(self, date):
        """Return whether this factor may be used for an activity on ``date``.

        A factor without ``valid_from``/``valid_to`` is always usable.
        """
        self.ensure_one()
        if not date:
            return True
        date = fields.Date.to_date(date)
        if self.valid_from and date < self.valid_from:
            return False
        if self.valid_to and date > self.valid_to:
            return False
        return True

    def _filter_valid_on(self, date):
        """Return the subset of these factors usable on ``date``."""
        return self.filtered(lambda factor: factor._is_valid_on(date))

    def _validity_label(self):
        """Return a readable validity window, used in error messages."""
        self.ensure_one()
        if self.valid_from and self.valid_to:
            return f"{self.valid_from} to {self.valid_to}"
        if self.valid_from:
            return f"from {self.valid_from}"
        if self.valid_to:
            return f"until {self.valid_to}"
        return "always valid"

    @api.model
    def create(self, vals):
        """Set the emission type from the context if it is not provided."""
        if not vals.get('type'):
            if self.env.context.get('default_type'):
                vals['type'] = self.env.context.get('default_type')
        return super().create(vals)