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
