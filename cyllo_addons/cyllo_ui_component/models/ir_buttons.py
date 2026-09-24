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
from lxml import etree
from odoo import api, fields, models


class IrModelButtons(models.Model):
    _name = 'ir.buttons'
    _description = 'Ir Model Buttons'

    name = fields.Char('Name', required=True,
                       help="Technical name of the button (e.g. name attribute in XML).")
    string = fields.Char('String', help="Display label or string text of the button.")
    type = fields.Selection(
        selection=[('object', 'Object'), ('action', 'Action')],
        string='Type',
        help="Type of the button: Object (calls python method) or Action (triggers action window)."
    )
    view_id = fields.Many2one('ir.ui.view', string='View',
                              help="The specific view where this button is defined.")
    model_id = fields.Many2one('ir.model', string='Model',
                               help="The target Cyllo model associated with the button's view.")

    @api.depends('string', 'name')
    def _compute_display_name(self):
        """It combines the button's technical name and its display string (if available)
            to improve clarity in UI listings."""
        for button in self:
            name = button.name
            if button.string and button.name:
                name = f"{button.string}({name})"
            button.display_name = name

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """Extend search functionality for UI elements."""
        domain = domain or []
        if name:
            domain = ['|', ('name', operator, name), ('string', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)

    @api.model
    def load_buttons_from_views(self, model=None):
        """
        Loads all action/object buttons defined in XML views into the database.
        """
        domain = [('model', '=', model.model), ('model', '!=', 'access.manager')] if model else [
            ('model', '!=', 'access.manager')]
        views = self.env['ir.ui.view'].search(domain)
        for view in views:
            try:
                if not view.arch_db:
                    continue
                arch = etree.fromstring(view.arch_db)
                for btn in arch.xpath('//button'):
                    btn_type = btn.get('type')
                    btn_name = btn.get('name')
                    btn_string = btn.get('string')

                    if btn_type in ('object', 'action') and btn_name and btn_string:
                        existing = self.search([
                            ("name", "=", btn_name),
                            ("view_id", "=", view.id)
                        ], limit=1)
                        if not existing:
                            self.create({
                                'name': btn_name,
                                'string': btn_string,
                                'type': btn_type,
                                'view_id': view.id,
                                'model_id': view.model_id.id if view.model_id else False,
                            })
            except Exception:
                continue
