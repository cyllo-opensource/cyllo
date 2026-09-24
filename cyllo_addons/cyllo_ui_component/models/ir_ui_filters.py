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
from lxml import etree


class IrModelFilters(models.Model):
    _name = 'ir.ui.filters'
    _description = 'Ir Model Filters'

    name = fields.Char('Name', required=True,
                       help="Technical name of the search filter (name attribute in XML).")
    string = fields.Char('String', help="Display label or string text of the filter.")
    is_group_by = fields.Boolean('Is Group By',
                            help="Check this if the filter is a group by filter rather than a simple domain filter.")
    view_id = fields.Many2one('ir.ui.view', string='View',
                              help="The specific search view where this filter is defined.")
    model_id = fields.Many2one('ir.model', string='Model',
                               help="The target Cyllo model associated with the search view.")

    @api.depends('string', 'name')
    def _compute_display_name(self):
        """Compute display name for filters in UI configuration."""
        for filter in self:
            name = filter.name
            if filter.string and filter.name:
                name = f"{filter.string}({name})"
            filter.display_name = name

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Enable search functionality for filters in UI configuration."""
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('string', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)

    @api.model
    def load_filters_from_views(self, model=None):
        """
        Loads all filters defined in search XML views into the database.
        """
        domain = [('model', '=', model.model), ('model', '!=', 'access.manager')] if model else [
            ('model', '!=', 'access.manager')]
        views = self.env['ir.ui.view'].search(domain)
        for view in views:
            try:
                if not view.arch_db:
                    continue
                arch = etree.fromstring(view.arch_db)
                for flt in arch.xpath('//filter'):
                    flt_name = flt.get('name')
                    flt_string = flt.get('string')
                    if flt_name:
                        existing = self.search([
                            ("name", "=", flt_name),
                            ("view_id", "=", view.id)
                        ], limit=1)
                        if not existing:
                            self.create({
                                'name': flt_name,
                                'string': flt_string,
                                'is_group_by': True if flt.get('context') and 'group_by' in flt.get(
                                    'context') else False,
                                'view_id': view.id,
                                'model_id': view.model_id.id if view.model_id else False,
                            })
            except Exception:
                continue
