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
from odoo.tests import common


class TestCommissionSetting(common.TransactionCase):
    """Tests for the Commissions module installer setting."""

    def test_module_field_is_declared(self):
        """The setting exposes the module installer boolean."""
        field = self.env['res.config.settings']._fields.get('module_cyllo_commission')
        self.assertTrue(field, "module_cyllo_commission should be declared")
        self.assertEqual(field.type, 'boolean')
        self.assertEqual(field.string, 'Commissions')

    def test_module_field_targets_existing_module(self):
        """The module installer field points at a real module."""
        module = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'cyllo_commission')], limit=1)
        self.assertTrue(module, "cyllo_commission module should be available")

    def test_setting_defaults_to_module_state(self):
        """The boolean mirrors the current installation state of the module."""
        module = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'cyllo_commission')], limit=1)
        settings = self.env['res.config.settings'].create({})
        self.assertEqual(
            settings.module_cyllo_commission,
            module.state in ('installed', 'to install', 'to upgrade'),
        )

    def test_settings_view_contains_the_field(self):
        """The settings form renders the commission option."""
        view = self.env.ref(
            'cyllo_commission_setting.'
            'view_res_config_settings_form_inherit_sale_commission')
        self.assertEqual(view.model, 'res.config.settings')
        self.assertIn('module_cyllo_commission', view.arch)
