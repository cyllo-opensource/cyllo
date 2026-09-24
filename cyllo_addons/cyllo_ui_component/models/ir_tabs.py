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

class IrModelTabs(models.Model):
    _name = 'ir.tabs'
    _description = 'Ir Model Tabs'

    name = fields.Char('Name', required=True,
                       help="Technical name of the tab (e.g. name or string attribute in XML).")
    string = fields.Char('String', help="Display title string of the tab.")
    view_id = fields.Many2one('ir.ui.view', string='View',
                              help="The specific view where this tab is defined.")
    model_id = fields.Many2one('ir.model', string='Model',
                               help="The target Cyllo model associated with the tab's view.")

    @api.depends('string', 'name')
    def _compute_display_name(self):
        """Compute display name for tabs in UI listings."""
        for tab in self:
            name = tab.name
            if tab.string and tab.name:
                name = f"{tab.string}({name})"
            tab.display_name = name

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Extend search functionality for tabs in UI configuration."""
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('string', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)

    @api.model
    def load_tabs_from_views(self, model=None):
        """
        Loads all notebook pages (tabs) defined in XML views into the database.
        """
        domain = [('model', '=', model.model), ('model', '!=', 'access.manager')] if model else [
            ('model', '!=', 'access.manager')]
        views = self.env['ir.ui.view'].search(domain)
        for view in views:
            try:
                if not view.arch_db:
                    continue
                arch = etree.fromstring(view.arch_db)
                for page in arch.xpath('//page'):
                    tab_name = page.get('name') or page.get('string')
                    tab_string = page.get('string')
                    if tab_string:
                        existing = self.search([
                            ("name", "=", tab_name),
                            ("view_id", "=", view.id)
                        ], limit=1)
                        if not existing:
                            self.create({
                                'name': tab_name or tab_string,
                                'string': tab_string,
                                'view_id': view.id,
                                'model_id': view.model_id.id if view.model_id else False,
                            })
            except Exception:
                continue
