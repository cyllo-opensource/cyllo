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
"""Tests for core/retrieval/schema_index.py — the columns_for resolver.

Needs the DB (reads information_schema), so this is a TransactionCase.
"""
from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core.retrieval.schema_index import SchemaIndex


class TestColumnsFor(TransactionCase):

    def setUp(self):
        super().setUp()
        # Ensure a clean build for this database's cache.
        SchemaIndex.invalidate(self.env.cr.dbname)
        self.schema = SchemaIndex(self.env)

    def test_known_table_returns_real_columns(self):
        cols = self.schema.columns_for('res_partner')
        self.assertIsNotNone(cols)
        # A few columns every res_partner table has.
        self.assertIn('name', cols)
        self.assertIn('id', cols)

    def test_unknown_table_returns_none(self):
        # None is the signal validate_plan turns into a rejection.
        self.assertIsNone(self.schema.columns_for('no_such_table_xyz'))

    def test_result_is_a_set_like_membership(self):
        cols = self.schema.columns_for('res_users')
        self.assertIn('login', cols)
        self.assertNotIn('definitely_not_a_column', cols)

    def test_cached_across_calls(self):
        # Second call must hit the cache, not rebuild — same object identity.
        first = self.schema.columns_for('res_partner')
        second = self.schema.columns_for('res_partner')
        self.assertIs(first, second)


class TestSelectionAndOrdering(TransactionCase):
    """Status values are exposed and listed first, for any model."""

    def setUp(self):
        super().setUp()
        SchemaIndex.invalidate(self.env.cr.dbname)
        self.schema = SchemaIndex(self.env)

    def test_selection_values_cached(self):
        meta = self.schema.field_meta('sale.order', 'state')
        values = [v for v, _l in meta['selection']]
        self.assertIn('sale', values)
        self.assertIn('cancel', values)

    def test_compact_lists_state_values_first(self):
        compact = self.schema.compact_fields('sale.order', max_fields=5)
        self.assertTrue(compact.startswith('state:selection('), compact)
        self.assertIn('|sale|', compact)

    def test_compact_keeps_dates_and_money_under_cap(self):
        compact = self.schema.compact_fields('sale.order', max_fields=12)
        self.assertIn('date_order:datetime', compact)
        self.assertIn('amount_total:monetary', compact)

    def test_describe_model_includes_selection(self):
        fields = {f['name']: f for f in self.schema.describe_model('sale.order')['fields']}
        self.assertIn('selection', fields['state'])

    def test_fields_for_models_shows_values(self):
        labels = self.schema.fields_for_models(['sale.order'])['sale.order']
        self.assertTrue(any(l.startswith('state (values:') for l in labels), labels)
