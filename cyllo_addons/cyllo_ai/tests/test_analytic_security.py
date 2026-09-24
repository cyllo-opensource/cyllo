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
"""Integration tests for analytic_record's SQL hardening (Stage 1, item 3).

Drives the real ``chatbot.tools.analytic_record`` entry point with a mocked LLM
so a crafted, malicious query plan reaches the guarded pipeline. Every case
here must be refused during validation — before the sandbox cursor is ever
touched — so no data leaks and the tool returns its terminal error string.
"""
import json
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core.retrieval.schema_index import SchemaIndex


class TestAnalyticRecordSecurity(TransactionCase):

    def setUp(self):
        super().setUp()
        self.tools = self.env['chatbot.tools']

    def _run_with_plan(self, plan):
        """Make the LLM return ``plan`` for every attempt, then run the tool."""
        payload = json.dumps(plan)
        with patch.object(type(self.tools), '_call_llm', return_value=payload):
            return self.tools.analytic_record('analyse something',
                                              self.env.company.ids)

    def _assert_refused(self, plan):
        out = self._run_with_plan(plan)
        # The tool always returns a string; a refused plan yields the terminal
        # error (never a JSON result payload with leaked rows).
        self.assertIsInstance(out, str)
        self.assertIn('Error in analytic_record', out)
        # And crucially: no rows were returned.
        self.assertNotIn('"result"', out)

    def test_where_subquery_to_undeclared_table_refused(self):
        # The classic exfiltration: a subquery reading a table never declared,
        # so ir.rules would never cover it. Must be refused.
        self._assert_refused({
            'main_table': {'name': 'res_partner', 'alias': 'res_partner'},
            'select': ['res_partner.id', 'res_partner.name'],
            'where': {'where_clause':
                      'res_partner.id IN (SELECT id FROM res_users)',
                      'where_params': []},
        })

    def test_scalar_subquery_password_leak_refused(self):
        self._assert_refused({
            'main_table': {'name': 'res_partner', 'alias': 'res_partner'},
            'select': ['res_partner.id'],
            'where': {'where_clause':
                      'res_partner.name = (SELECT password FROM res_users)',
                      'where_params': []},
        })

    def test_select_from_undeclared_table_refused(self):
        # Self-report claims only res_partner, but the SELECT reaches into
        # res_users — the derived table set ignores the self-report and the
        # undeclared alias is refused.
        self._assert_refused({
            'main_table': {'name': 'res_partner', 'alias': 'res_partner'},
            'select': ['res_partner.id', 'res_users.password'],
            'where': {'where_clause': '', 'where_params': []},
            'tables': ['res_partner'],
        })

    def test_second_statement_refused(self):
        self._assert_refused({
            'main_table': {'name': 'res_partner', 'alias': 'res_partner'},
            'select': ['res_partner.id'],
            'where': {'where_clause':
                      "res_partner.active = %s; DROP TABLE res_users",
                      'where_params': [True]},
        })

    def test_string_literal_refused(self):
        self._assert_refused({
            'main_table': {'name': 'res_partner', 'alias': 'res_partner'},
            'select': ['res_partner.id'],
            'where': {'where_clause': "res_partner.name = 'Administrator'",
                      'where_params': []},
        })


class TestAnalyticRecordHappyPath(TransactionCase):
    """A VALID plan flows all the way through the real pipeline and returns a
    proper result payload.

    Everything is real except the raw SQL execution, which is mocked: in Odoo
    test mode ``registry.cursor()`` shares the test transaction, so the sandbox
    cursor's ``SET TRANSACTION READ ONLY`` can't run cleanly — a test-harness
    artefact, not a production issue. Mocking only ``_execute_analytic_sql``
    still exercises validate_plan, query building, the ACL/ir.rules loop, and
    result/entity assembly. The live execution path is verified via the Odoo
    shell (see the module docs / PR notes).
    """

    def setUp(self):
        super().setUp()
        self.tools = self.env['chatbot.tools']

    def test_valid_plan_returns_result_and_entities(self):
        plan = json.dumps({
            'main_table': {'name': 'res_partner', 'alias': 'res_partner'},
            'select': ['res_partner.id', 'res_partner.name'],
            'where': {'where_clause': '', 'where_params': []},
            'limit': 10,
        })
        # Canned rows standing in for the sandbox-cursor read.
        fake_rows = [(1, 'Alice'), (2, 'Bob')]
        fake_cols = ['id', 'name']
        with patch.object(type(self.tools), '_call_llm', return_value=plan), \
             patch.object(type(self.tools), '_execute_analytic_sql',
                          return_value=(fake_rows, fake_cols)):
            out = self.tools.analytic_record('list partners', self.env.company.ids)

        data = json.loads(out)  # a valid plan yields JSON, not an error string
        self.assertEqual(len(data['result']), 2)
        # Keys are disambiguated as table_column so joined same-name columns
        # never collide.
        self.assertEqual(data['result'][0],
                         {'res_partner_id': 1, 'res_partner_name': 'Alice'})
        # Entities are derived from the id + name columns for clickable links.
        names = {e['text'] for e in data['entities']}
        self.assertEqual(names, {'Alice', 'Bob'})
        self.assertTrue(all(e['model'] == 'res.partner' for e in data['entities']))

    def test_joined_same_name_columns_do_not_collide(self):
        # The bug the shell test caught: partner.id/name and country.id/name
        # both come back as 'id'/'name' and used to overwrite each other.
        plan = json.dumps({
            'main_table': {'name': 'res_partner', 'alias': 'res_partner'},
            'select': ['res_partner.id', 'res_partner.name',
                       'res_country.id', 'res_country.name'],
            'joins': [{'type': 'LEFT JOIN',
                       'lhs_alias': 'res_partner', 'lhs_column': 'country_id',
                       'rhs_alias': 'res_country', 'rhs_column': 'id',
                       'rhs_table': 'res_country'}],
            'where': {'where_clause': '', 'where_params': []},
        })
        rows = [(1, 'Alice', 233, {'en_US': 'United States'})]
        cols = ['id', 'name', 'id', 'name']  # duplicate names, as Postgres returns
        with patch.object(type(self.tools), '_call_llm', return_value=plan), \
             patch.object(type(self.tools), '_execute_analytic_sql',
                          return_value=(rows, cols)):
            out = self.tools.analytic_record('partners and countries',
                                             self.env.company.ids)
        row = json.loads(out)['result'][0]
        # Both the partner AND the country survive, and the translatable
        # country name is unwrapped to plain text.
        self.assertEqual(row['res_partner_id'], 1)
        self.assertEqual(row['res_partner_name'], 'Alice')
        self.assertEqual(row['res_country_id'], 233)
        self.assertEqual(row['res_country_name'], 'United States')


class TestAnalyticFieldAccess(TransactionCase):
    """Field-level (column) access on the raw-SQL read path — raw SQL bypasses
    Odoo's field security, so analytic_record re-applies it as the user."""

    def setUp(self):
        super().setUp()
        self.tools = self.env['chatbot.tools']
        self.schema = SchemaIndex(self.env)

    def test_denylist_blocks_password_even_for_admin(self):
        # Credential columns are blocked outright, regardless of model ACL.
        with self.assertRaises(AccessError):
            self.tools._check_field_access(
                [('res_users', 'password')], self.schema)

    def test_denylist_blocks_api_key(self):
        with self.assertRaises(AccessError):
            self.tools._check_field_access(
                [('res_users', 'api_key')], self.schema)

    def test_normal_fields_allowed(self):
        # No restriction -> no error.
        self.tools._check_field_access(
            [('res_partner', 'name'), ('sale_order', 'amount_total')],
            self.schema)

    def test_field_group_blocks_non_member(self):
        limited = self.env['res.users'].create({
            'name': 'Analytic Limited', 'login': 'analytic_limited_test',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        tools = self.tools.with_user(limited)
        schema = SchemaIndex(tools.env)
        # Temporarily restrict a real stored field to a group the user lacks.
        field = self.env['res.partner']._fields['email']
        original = field.groups
        field.groups = 'base.group_system'
        try:
            with self.assertRaises(AccessError):
                tools._check_field_access([('res_partner', 'email')], schema)
        finally:
            field.groups = original

    def test_field_group_allows_member(self):
        # The admin has base.group_system, so the same field is readable.
        field = self.env['res.partner']._fields['email']
        original = field.groups
        field.groups = 'base.group_system'
        try:
            self.tools._check_field_access([('res_partner', 'email')], self.schema)
        finally:
            field.groups = original

    def test_end_to_end_password_query_denied(self):
        # A full run: a plan that selects the password column is refused, and
        # no result payload is returned.
        plan = json.dumps({
            'main_table': {'name': 'res_users', 'alias': 'res_users'},
            'select': ['res_users.id', 'res_users.password'],
            'where': {'where_clause': '', 'where_params': []},
        })
        with patch.object(type(self.tools), '_call_llm', return_value=plan):
            out = self.tools.analytic_record('dump passwords',
                                             self.env.company.ids)
        self.assertIsInstance(out, str)
        self.assertIn('Error in analytic_record', out)
        self.assertNotIn('"result"', out)
