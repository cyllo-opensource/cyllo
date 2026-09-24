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


class TestUiComponent(common.TransactionCase):
    """Tests for the ir.buttons / ir.tabs / ir.ui.filters registries."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env['ir.model']._get('res.partner')
        cls.form_view = cls.env['ir.ui.view'].create({
            'name': 'cyllo.ui.component.test.form',
            'model': 'res.partner',
            'type': 'form',
            'arch': """
                <form>
                    <sheet>
                        <button name="action_archive" type="object"
                                string="Cyllo Test Button"/>
                        <notebook>
                            <page name="cyllo_test_page" string="Cyllo Test Page">
                                <field name="comment"/>
                            </page>
                        </notebook>
                    </sheet>
                </form>
            """,
        })
        cls.search_view = cls.env['ir.ui.view'].create({
            'name': 'cyllo.ui.component.test.search',
            'model': 'res.partner',
            'type': 'search',
            'arch': """
                <search>
                    <field name="name"/>
                    <filter name="cyllo_test_filter" string="Cyllo Test Filter"
                            domain="[('is_company', '=', True)]"/>
                    <filter name="cyllo_test_group" string="Cyllo Test Group"
                            context="{'group_by': 'country_id'}"/>
                </search>
            """,
        })

    # -------------------------------------------------------------------------
    # ir.buttons
    # -------------------------------------------------------------------------
    def test_button_display_name(self):
        """display_name combines the string and the technical name."""
        button = self.env['ir.buttons'].create({
            'name': 'action_confirm',
            'string': 'Confirm',
            'type': 'object',
        })
        self.assertEqual(button.display_name, 'Confirm(action_confirm)')

    def test_button_display_name_without_string(self):
        """Without a string, display_name falls back to the technical name."""
        button = self.env['ir.buttons'].create({'name': 'action_confirm'})
        self.assertEqual(button.display_name, 'action_confirm')

    def test_button_name_search_on_string(self):
        """_name_search matches on the string as well as the technical name."""
        button = self.env['ir.buttons'].create({
            'name': 'action_cyllo_unique',
            'string': 'Cyllo Unique Label',
            'type': 'object',
        })
        by_string = self.env['ir.buttons'].name_search('Cyllo Unique Label')
        self.assertIn(button.id, [res[0] for res in by_string])
        by_name = self.env['ir.buttons'].name_search('action_cyllo_unique')
        self.assertIn(button.id, [res[0] for res in by_name])

    def test_load_buttons_from_views(self):
        """Buttons declared in a view are registered against that view."""
        self.env['ir.buttons'].load_buttons_from_views(self.partner_model)
        button = self.env['ir.buttons'].search([
            ('view_id', '=', self.form_view.id),
            ('name', '=', 'action_archive'),
        ])
        self.assertEqual(len(button), 1)
        self.assertEqual(button.string, 'Cyllo Test Button')
        self.assertEqual(button.type, 'object')
        self.assertEqual(button.model_id, self.partner_model)

    def test_load_buttons_is_idempotent(self):
        """Loading twice does not duplicate the registered buttons."""
        self.env['ir.buttons'].load_buttons_from_views(self.partner_model)
        self.env['ir.buttons'].load_buttons_from_views(self.partner_model)
        buttons = self.env['ir.buttons'].search([
            ('view_id', '=', self.form_view.id),
            ('name', '=', 'action_archive'),
        ])
        self.assertEqual(len(buttons), 1)

    # -------------------------------------------------------------------------
    # ir.tabs
    # -------------------------------------------------------------------------
    def test_load_tabs_from_views(self):
        """Notebook pages declared in a view are registered as tabs."""
        self.env['ir.tabs'].load_tabs_from_views(self.partner_model)
        tab = self.env['ir.tabs'].search([
            ('view_id', '=', self.form_view.id),
            ('name', '=', 'cyllo_test_page'),
        ])
        self.assertEqual(len(tab), 1)
        self.assertEqual(tab.string, 'Cyllo Test Page')
        self.assertEqual(tab.display_name, 'Cyllo Test Page(cyllo_test_page)')

    def test_load_tabs_is_idempotent(self):
        """Loading twice does not duplicate the registered tabs."""
        self.env['ir.tabs'].load_tabs_from_views(self.partner_model)
        self.env['ir.tabs'].load_tabs_from_views(self.partner_model)
        tabs = self.env['ir.tabs'].search([
            ('view_id', '=', self.form_view.id),
            ('name', '=', 'cyllo_test_page'),
        ])
        self.assertEqual(len(tabs), 1)

    # -------------------------------------------------------------------------
    # ir.ui.filters
    # -------------------------------------------------------------------------
    def test_load_filters_from_views(self):
        """Search filters are registered, group-by filters are flagged."""
        self.env['ir.ui.filters'].load_filters_from_views(self.partner_model)
        plain = self.env['ir.ui.filters'].search([
            ('view_id', '=', self.search_view.id),
            ('name', '=', 'cyllo_test_filter'),
        ])
        self.assertEqual(len(plain), 1)
        self.assertEqual(plain.string, 'Cyllo Test Filter')
        self.assertFalse(plain.is_group_by)

        group_by = self.env['ir.ui.filters'].search([
            ('view_id', '=', self.search_view.id),
            ('name', '=', 'cyllo_test_group'),
        ])
        self.assertEqual(len(group_by), 1)
        self.assertTrue(group_by.is_group_by)

    def test_load_filters_is_idempotent(self):
        """Loading twice does not duplicate the registered filters."""
        self.env['ir.ui.filters'].load_filters_from_views(self.partner_model)
        self.env['ir.ui.filters'].load_filters_from_views(self.partner_model)
        filters = self.env['ir.ui.filters'].search([
            ('view_id', '=', self.search_view.id),
            ('name', '=', 'cyllo_test_filter'),
        ])
        self.assertEqual(len(filters), 1)

    def test_access_manager_model_is_skipped(self):
        """The access.manager model is explicitly excluded from the scan."""
        self.env['ir.buttons'].load_buttons_from_views()
        self.assertFalse(self.env['ir.buttons'].search([
            ('view_id.model', '=', 'access.manager'),
        ]))
