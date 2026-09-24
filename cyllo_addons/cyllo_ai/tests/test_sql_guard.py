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
"""Tests for core/retrieval/sql_guard.py — the WHERE-clause allowlist validator.

Pure-function tests (no env needed); subclass TransactionCase to match the
module's test convention and be picked up by the Odoo test runner.
"""
from odoo.tests.common import TransactionCase

from odoo.addons.cyllo_ai.core.retrieval.sql_guard import (
    SqlGuardError,
    validate_group_by,
    validate_order_by,
    validate_plan,
    validate_select,
    validate_where,
)

# Two declared tables with their real columns — the fixture a validated query
# would hand the guard after resolving main_table + joins.
ALLOWED = {'sale_order', 'res_partner'}
COLUMNS = {
    'sale_order': {'id', 'name', 'state', 'amount_total', 'date_order',
                   'partner_id', 'user_id'},
    'res_partner': {'id', 'name', 'country_id', 'email'},
}

# Schema for whole-plan tests: a get_columns resolver over three tables, one of
# which (res_users) is sensitive and must never be reachable unless declared.
PLAN_SCHEMA = {
    'sale_order': COLUMNS['sale_order'],
    'res_partner': COLUMNS['res_partner'],
    'res_users': {'id', 'login', 'password', 'partner_id'},
}


def _get_columns(table):
    return PLAN_SCHEMA.get(table)  # None -> unknown table -> rejected


# A valid, joined, aggregated plan reused across the plan tests.
def _good_plan():
    return {
        'main_table': {'name': 'sale_order', 'alias': 'sale_order'},
        'joins': [{'type': 'LEFT JOIN',
                   'lhs_alias': 'sale_order', 'lhs_column': 'partner_id',
                   'rhs_alias': 'res_partner', 'rhs_column': 'id',
                   'rhs_table': 'res_partner'}],
        'select': ['res_partner.name', 'SUM(sale_order.amount_total) AS total'],
        'where': {'where_clause': 'sale_order.date_order >= %s',
                  'where_params': ['2025-01-01']},
        'group_by': 'res_partner.name',
        'order_by': 'SUM(sale_order.amount_total) DESC',
        'tables': ['this_is_a_lie'],  # self-report is ignored by design
    }


class TestSqlGuardWhere(TransactionCase):

    def _ok(self, clause):
        # Should not raise; returns the referenced idents.
        return validate_where(clause, ALLOWED, COLUMNS)

    def _reject(self, clause):
        with self.assertRaises(SqlGuardError):
            validate_where(clause, ALLOWED, COLUMNS)

    # -- accepted subset ----------------------------------------------------

    def test_empty_clause_ok(self):
        self.assertEqual(validate_where("", ALLOWED, COLUMNS), [])
        self.assertEqual(validate_where("   ", ALLOWED, COLUMNS), [])
        self.assertEqual(validate_where(None, ALLOWED, COLUMNS), [])

    def test_simple_comparison(self):
        self.assertEqual(self._ok("sale_order.amount_total >= %s"),
                         [('sale_order', 'amount_total')])

    def test_and_or_grouping(self):
        self._ok("(sale_order.state = %s OR sale_order.state = %s) "
                 "AND res_partner.name ILIKE %s")

    def test_date_range(self):
        self._ok("sale_order.date_order >= %s AND sale_order.date_order < %s")

    def test_in_placeholder(self):
        self._ok("sale_order.state IN %s")

    def test_between(self):
        self._ok("sale_order.date_order BETWEEN %s AND %s")

    def test_is_null(self):
        self._ok("sale_order.state IS NULL")
        self._ok("sale_order.state IS NOT NULL")

    def test_allowed_function_wrapping_column(self):
        self._ok("LOWER(res_partner.name) LIKE %s")
        self._ok("COALESCE(sale_order.amount_total, %s) > %s")

    def test_prefix_not(self):
        self._ok("NOT (sale_order.state = %s)")

    def test_not_like(self):
        self._ok("sale_order.name NOT LIKE %s")

    def test_uppercase_identifier_normalized(self):
        # Postgres folds unquoted identifiers to lowercase; the guard mirrors
        # that instead of forcing a retry, and returns the normalized pair.
        self.assertEqual(self._ok("SALE_ORDER.AMOUNT_TOTAL >= %s"),
                         [('sale_order', 'amount_total')])

    def test_returns_all_referenced_idents(self):
        idents = self._ok("sale_order.amount_total > %s "
                          "AND res_partner.country_id = %s")
        self.assertIn(('sale_order', 'amount_total'), idents)
        self.assertIn(('res_partner', 'country_id'), idents)

    # -- rejected: injection / exfiltration ---------------------------------

    def test_reject_subquery(self):
        self._reject("sale_order.id IN (SELECT id FROM hr_payslip)")

    def test_reject_scalar_subquery(self):
        self._reject("sale_order.name = (SELECT password FROM res_users)")

    def test_reject_semicolon_second_statement(self):
        self._reject("sale_order.state = %s; DROP TABLE res_users")

    def test_reject_sql_comment(self):
        self._reject("sale_order.state = %s -- comment")

    def test_reject_string_literal(self):
        self._reject("sale_order.state = 'done'")

    def test_reject_numeric_literal(self):
        self._reject("sale_order.amount_total = 5")

    def test_reject_tautology(self):
        self._reject("sale_order.amount_total > %s OR 1=1")

    def test_reject_disallowed_function(self):
        self._reject("pg_sleep(%s)")

    def test_reject_extract(self):
        # EXTRACT dropped by design — range filters replace it.
        self._reject("EXTRACT(YEAR FROM sale_order.date_order) = %s")

    # -- rejected: access scope ---------------------------------------------

    def test_reject_unknown_alias(self):
        self._reject("hr_payslip.amount > %s")

    def test_reject_unknown_column(self):
        self._reject("sale_order.secret > %s")

    def test_reject_column_to_column(self):
        # RHS must be %s — comparing to another column is a leak vector.
        self._reject("sale_order.amount_total = res_partner.id")

    # -- rejected: malformed ------------------------------------------------

    def test_reject_bare_column(self):
        self._reject("sale_order.amount_total")

    def test_reject_trailing_operator(self):
        self._reject("sale_order.amount_total >= %s AND")

    def test_reject_bare_table(self):
        self._reject("sale_order > %s")

    def test_reject_dotted_path(self):
        # alias.column only — deeper paths are not columns.
        self._reject("sale_order.partner_id.name = %s")

    def test_arithmetic_lhs_allowed(self):
        # Arithmetic on the left of a comparison is safe (operands validated;
        # RHS is still %s-only).
        self._ok("sale_order.amount_total * %s > %s")

    def test_rhs_literal_still_rejected(self):
        # Even though numbers are now legal in arithmetic, a bare value as a
        # comparison RHS is still refused — values must be %s.
        self._reject("sale_order.amount_total = 5")

    def test_reject_aggregate_in_where(self):
        # Aggregates belong in SELECT/HAVING, never WHERE.
        self._reject("SUM(sale_order.amount_total) > %s")


class TestSqlGuardSelect(TransactionCase):

    def _ok(self, items):
        return validate_select(items, ALLOWED, COLUMNS)

    def _reject(self, items):
        with self.assertRaises(SqlGuardError):
            validate_select(items, ALLOWED, COLUMNS)

    def test_plain_columns(self):
        self.assertEqual(
            self._ok(['sale_order.id', 'sale_order.amount_total']),
            [('sale_order', 'id'), ('sale_order', 'amount_total')])

    def test_aggregate(self):
        self._ok(['SUM(sale_order.amount_total)'])

    def test_count_star(self):
        self.assertEqual(self._ok(['COUNT(*)']), [])

    def test_aggregate_with_as_label(self):
        self._ok(['sale_order.state', 'SUM(sale_order.amount_total) AS total'])

    def test_scalar_functions(self):
        self._ok(['DATE_TRUNC(%s, sale_order.date_order)'])
        self._ok(['COALESCE(sale_order.amount_total, %s)'])

    def test_empty_list_ok(self):
        self.assertEqual(self._ok([]), [])
        self.assertEqual(self._ok(None), [])

    def test_reject_injection(self):
        self._reject(['sale_order.id; DROP TABLE res_users'])

    def test_reject_subquery(self):
        self._reject(['(SELECT 1)'])

    def test_reject_unknown_column(self):
        self._reject(['sale_order.secret'])

    def test_reject_undeclared_table(self):
        self._reject(['res_users.password'])

    def test_reject_disallowed_function(self):
        self._reject(['pg_sleep(sale_order.id)'])

    def test_reject_injected_as_label(self):
        self._reject(['sale_order.id AS ; drop'])

    # -- newly-supported patterns (item 5) ----------------------------------

    def test_count_star_with_as_label(self):
        # The COUNT(*) AS n bug the shell test found.
        self._ok(['COUNT(*) AS order_count'])

    def test_count_distinct(self):
        self._ok(['COUNT(DISTINCT sale_order.partner_id) AS customers'])

    def test_date_trunc_string_literal(self):
        # Time-series bucketing needs a quoted literal as the function arg.
        self._ok(["DATE_TRUNC('month', sale_order.date_order) AS month"])

    def test_arithmetic_in_aggregate(self):
        self._ok(['SUM(sale_order.amount_total * sale_order.amount_total) AS sq'])

    def test_coalesce_with_number(self):
        self._ok(['COALESCE(SUM(sale_order.amount_total), 0) AS total'])

    def test_bare_string_constant_allowed(self):
        # Safe-charset string constant — harmless, cannot break out.
        self._ok(["'a label'"])

    def test_unsafe_string_literal_rejected(self):
        # A semicolon inside a string literal is refused by the safe charset.
        self._reject(["DATE_TRUNC('a;b', sale_order.date_order)"])

    def test_select_star_rejected(self):
        self._reject(['*'])


class TestSqlGuardGroupOrder(TransactionCase):

    def test_group_by_columns(self):
        self.assertEqual(
            validate_group_by('sale_order.state, sale_order.user_id',
                              ALLOWED, COLUMNS),
            [('sale_order', 'state'), ('sale_order', 'user_id')])

    def test_group_by_scalar_function_with_comma_arg(self):
        # Comma inside the function must not be mistaken for a term separator.
        validate_group_by('COALESCE(sale_order.state, %s), sale_order.user_id',
                          ALLOWED, COLUMNS)

    def test_group_by_empty_ok(self):
        self.assertEqual(validate_group_by('', ALLOWED, COLUMNS), [])
        self.assertEqual(validate_group_by(None, ALLOWED, COLUMNS), [])

    def test_group_by_rejects_aggregate(self):
        with self.assertRaises(SqlGuardError):
            validate_group_by('SUM(sale_order.amount_total)', ALLOWED, COLUMNS)

    def test_group_by_rejects_injection(self):
        with self.assertRaises(SqlGuardError):
            validate_group_by('sale_order.state; drop', ALLOWED, COLUMNS)

    def test_order_by_direction(self):
        validate_order_by('sale_order.state ASC, sale_order.date_order DESC',
                          ALLOWED, COLUMNS)

    def test_order_by_aggregate(self):
        validate_order_by('SUM(sale_order.amount_total) DESC', ALLOWED, COLUMNS)

    def test_order_by_rejects_bad_direction(self):
        with self.assertRaises(SqlGuardError):
            validate_order_by('sale_order.amount_total FOOBAR', ALLOWED, COLUMNS)

    def test_order_by_rejects_injection(self):
        with self.assertRaises(SqlGuardError):
            validate_order_by('sale_order.state; drop', ALLOWED, COLUMNS)

    def test_order_by_accepts_select_output_alias(self):
        # ORDER BY may reference a SELECT alias (e.g. SUM(...) AS total).
        validate_order_by('total DESC', ALLOWED, COLUMNS, {'total'})

    def test_order_by_rejects_unknown_bare_name(self):
        with self.assertRaises(SqlGuardError):
            validate_order_by('mystery DESC', ALLOWED, COLUMNS, {'total'})

    def test_group_by_accepts_select_output_alias(self):
        validate_group_by('bucket', ALLOWED, COLUMNS, {'bucket'})

    def test_group_by_rejects_unknown_bare_name(self):
        with self.assertRaises(SqlGuardError):
            validate_group_by('bucket', ALLOWED, COLUMNS, {'total'})


class TestSqlGuardPlan(TransactionCase):

    def _reject(self, plan):
        with self.assertRaises(SqlGuardError):
            validate_plan(plan, _get_columns)

    def test_valid_plan_derives_tables_ignoring_self_report(self):
        vp = validate_plan(_good_plan(), _get_columns)
        # Derived from main_table + joins, NOT from the plan's 'tables' list.
        self.assertEqual(vp.tables, {'sale_order', 'res_partner'})

    def test_reject_where_subquery_to_undeclared_table(self):
        plan = _good_plan()
        plan['where'] = {'where_clause':
                         'sale_order.id IN (SELECT id FROM res_users)'}
        self._reject(plan)

    def test_reject_select_from_undeclared_table(self):
        plan = _good_plan()
        plan['select'] = ['res_users.password']
        self._reject(plan)

    def test_reject_join_bad_column(self):
        plan = _good_plan()
        plan['joins'] = [{'type': 'JOIN',
                          'lhs_alias': 'sale_order', 'lhs_column': 'nope',
                          'rhs_alias': 'res_partner', 'rhs_column': 'id',
                          'rhs_table': 'res_partner'}]
        self._reject(plan)

    def test_reject_join_lhs_before_declared(self):
        # A join whose left side references an alias not yet introduced.
        self._reject({
            'main_table': {'name': 'sale_order', 'alias': 'sale_order'},
            'joins': [{'type': 'JOIN',
                       'lhs_alias': 'res_partner', 'lhs_column': 'id',
                       'rhs_alias': 'res_users', 'rhs_column': 'partner_id',
                       'rhs_table': 'res_users'}],
            'select': ['sale_order.id'],
        })

    def test_reject_unknown_main_table(self):
        self._reject({'main_table': {'name': 'hr_payslip', 'alias': 'hr_payslip'},
                      'select': ['hr_payslip.id']})

    def test_reject_join_alias_injection(self):
        plan = _good_plan()
        plan['joins'][0]['rhs_alias'] = 'res_partner; drop'
        self._reject(plan)

    def test_reject_bad_join_type(self):
        plan = _good_plan()
        plan['joins'][0]['type'] = 'CROSS JOIN'
        self._reject(plan)

    def test_reject_dotted_model_name_not_normalized(self):
        # validate_plan requires table names already normalized (no dots).
        self._reject({'main_table': {'name': 'sale.order', 'alias': 'sale.order'},
                      'select': ['sale_order.id']})

    def test_reject_non_dict_plan(self):
        self._reject('DROP TABLE res_users')
