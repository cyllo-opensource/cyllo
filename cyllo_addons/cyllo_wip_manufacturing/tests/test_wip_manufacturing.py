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
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestWipManufacturing(AccountTestInvoicingCommon):
    """Tests for the work in progress accounting of manufacturing orders."""

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company = cls.env.company
        cls.journal = cls.company_data['default_journal_misc']
        cls.wip_account = cls.company_data['default_account_assets']
        cls.overhead_account = cls.company_data['default_account_expense']
        cls.product = cls.env['product.product'].create({
            'name': 'WIP Finished Good',
            'type': 'product',
        })
        cls.component = cls.env['product.product'].create({
            'name': 'WIP Component',
            'type': 'product',
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {
                'product_id': cls.component.id,
                'product_qty': 2.0,
            })],
        })

    def _create_production(self):
        return self.env['mrp.production'].create({
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'product_qty': 1.0,
            'bom_id': self.bom.id,
        })

    # -------------------------------------------------------------------------
    # Company configuration
    # -------------------------------------------------------------------------
    def test_company_wip_fields(self):
        """The company carries the WIP accounting configuration."""
        fields = self.env['res.company']._fields
        for fname in ('wip_active', 'wip_journal_id', 'wip_account_id',
                      'wip_overhead_account_id'):
            self.assertIn(fname, fields)

    def test_wip_is_disabled_by_default(self):
        """WIP accounting is opt-in."""
        company = self.env['res.company'].create({'name': 'Fresh WIP Company'})
        self.assertFalse(company.wip_active)

    def test_settings_expose_the_company_configuration(self):
        """The settings screen writes through to the company."""
        settings = self.env['res.config.settings'].create({
            'wip_active': True,
            'wip_journal_id': self.journal.id,
            'wip_account_id': self.wip_account.id,
            'wip_overhead_account_id': self.overhead_account.id,
        })
        settings.execute()
        self.assertTrue(self.company.wip_active)
        self.assertEqual(self.company.wip_journal_id, self.journal)
        self.assertEqual(self.company.wip_account_id, self.wip_account)
        self.assertEqual(self.company.wip_overhead_account_id,
                         self.overhead_account)

    # -------------------------------------------------------------------------
    # Manufacturing order
    # -------------------------------------------------------------------------
    def test_production_has_no_wip_entry_initially(self):
        """A new manufacturing order has no WIP journal entry."""
        production = self._create_production()
        self.assertEqual(production.wip_entry_count, 0)

    def test_posting_requires_wip_to_be_enabled(self):
        """Posting a WIP entry is refused while WIP accounting is off."""
        self.company.wip_active = False
        production = self._create_production()
        with self.assertRaises(UserError):
            production.action_post_wip_entries()

    def test_posting_opens_the_wizard_when_enabled(self):
        """With WIP enabled the action opens the posting wizard."""
        self.company.write({
            'wip_active': True,
            'wip_journal_id': self.journal.id,
            'wip_account_id': self.wip_account.id,
        })
        production = self._create_production()
        action = production.action_post_wip_entries()
        self.assertEqual(action['res_model'], 'mrp.wip.accounting.wizard')
        self.assertEqual(action['context']['default_production_id'],
                         production.id)

    def test_view_wip_entries_is_scoped_to_the_order(self):
        """The smart button lists only the entries of this order."""
        production = self._create_production()
        action = production.action_view_wip_entries()
        self.assertEqual(action['res_model'], 'account.move')
        self.assertIn(('production_id', '=', production.id), action['domain'])
        self.assertEqual(action['context']['default_move_type'], 'entry')

    def test_wip_entry_count_follows_the_journal_entries(self):
        """Entries linked to the order are counted on the smart button."""
        production = self._create_production()
        self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.journal.id,
            'production_id': production.id,
        })
        production.invalidate_recordset(['wip_entry_count'])
        self.assertEqual(production.wip_entry_count, 1)

    def test_account_move_links_back_to_the_production(self):
        """account.move is extended with the manufacturing order link."""
        field = self.env['account.move']._fields.get('production_id')
        self.assertTrue(field)
        self.assertEqual(field.comodel_name, 'mrp.production')
