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
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

class TestCalculationPreset(TransactionCase):

    def setUp(self):
        super(TestCalculationPreset, self).setUp()
        self.Preset = self.env['calculation.preset']

    def test_translate_to_sql_basic(self):
        """Test basic arithmetic translation."""
        formula = "({rev} - {cost}) / {cost} * 100"
        bindings = {
            'rev': '"sale_order"."amount_total"',
            'cost': '1000'
        }
        sql = self.Preset.translate_to_sql(formula, bindings)
        self.assertIn('"sale_order"."amount_total"', sql)
        self.assertIn(' - 1000', sql)
        self.assertIn('NULLIF((1000), 0)', sql)
        self.assertIn(' * 100', sql)

    def test_translate_to_sql_conditional(self):
        """Test conditional expression (IF/THEN/ELSE) translation."""
        formula = "if({rev} > 1000, {rev} * 0.1, 0)"
        bindings = {
            'rev': '"sale_order"."amount_total"'
        }
        sql = self.Preset.translate_to_sql(formula, bindings)
        self.assertIn('CASE WHEN', sql)
        self.assertIn('THEN', sql)
        self.assertIn('ELSE', sql)
        self.assertIn('"sale_order"."amount_total" > 1000', sql)

    def test_translate_to_sql_safety(self):
        """Test that unauthorized functions are blocked."""
        formula = "__import__('os').system('ls')"
        bindings = {}
        with self.assertRaises(UserError):
            self.Preset.translate_to_sql(formula, bindings)

    def test_translate_to_sql_safety_complex(self):
        """Test that unauthorized method calling is blocked."""
        formula = "{rev}.pop()"
        bindings = {'rev': 'some_table.col'}
        with self.assertRaises(UserError):
            self.Preset.translate_to_sql(formula, bindings)
    def test_translate_to_sql_aggregates(self):
        """Test aggregation functions in formulas."""
        formula = "sum({rev}) - sum({tax})"
        bindings = {
            'rev': '"sale_order"."amount_total"',
            'tax': '"sale_order"."amount_tax"'
        }
        sql = self.Preset.translate_to_sql(formula, bindings)
        self.assertIn('SUM("sale_order"."amount_total")', sql)
        self.assertIn('SUM("sale_order"."amount_tax")', sql)

    def test_translate_to_sql_min_max(self):
        """Test min/max aggregate vs scalar mapping."""
        # Aggregate min
        sql_agg = self.Preset.translate_to_sql("min({a})", {'a': 'col'})
        self.assertIn('MIN(col)', sql_agg)
        
        # Scalar least (min with >1 arg)
        sql_scalar = self.Preset.translate_to_sql("min({a}, 0)", {'a': 'col'})
        self.assertIn('LEAST(col, 0)', sql_scalar)

        # Aggregate max
        sql_agg_max = self.Preset.translate_to_sql("max({a})", {'a': 'col'})
        self.assertIn('MAX(col)', sql_agg_max)
        
        # Scalar greatest (max with >1 arg)
        sql_scalar_max = self.Preset.translate_to_sql("max({a}, 100)", {'a': 'col'})
        self.assertIn('GREATEST(col, 100)', sql_scalar_max)

    def test_translate_to_sql_extra_funcs(self):
        """Test extra functions COALESCE, NULLIF."""
        sql = self.Preset.translate_to_sql("coalesce({a}, 0)", {'a': 'col'})
        self.assertIn('COALESCE(col, 0)', sql)
        
        sql_nullif = self.Preset.translate_to_sql("nullif({a}, '')", {'a': 'col'})
        self.assertIn("NULLIF(col, '')", sql_nullif)

    def test_translate_to_sql_division(self):
        """Test division with float casting and NULLIF."""
        sql = self.Preset.translate_to_sql("{a} / {b}", {'a': '1', 'b': '2'})
        self.assertIn('::float', sql)
        self.assertIn('NULLIF', sql)
        # Expected roughly: ((1)::float / NULLIF((2), 0))



    def test_translate_to_sql_advanced_no_unsound_merge(self):
        """Aggregates added together must stay separate terms.

        SUM(x) FILTER (f1) + SUM(x) FILTER (f2) is only equal to
        SUM(x) FILTER (f1 OR f2) when f1 and f2 are disjoint, and with no
        filters at all the merge collapsed SUM(x) + SUM(x) to SUM(x),
        silently dropping an operand.
        """
        configs = [
            {'name': 'this_month', 'column': 'amount', 'aggregate': 'SUM', 'filter_domain': 'date >= "2024-01-01"'},
            {'name': 'last_month', 'column': 'amount', 'aggregate': 'SUM', 'filter_domain': 'date >= "2023-12-01" AND date < "2024-01-01"'},
            {'name': 'other_col', 'column': 'qty', 'aggregate': 'SUM', 'filter_domain': '1=1'},
            {'name': 'plain_a', 'column': 'amount', 'aggregate': 'SUM', 'filter_domain': ''},
            {'name': 'plain_b', 'column': 'amount', 'aggregate': 'SUM', 'filter_domain': ''},
        ]

        # 1. Same column, same aggregate, no filters: must NOT collapse to one term.
        sql_plain = self.Preset.translate_to_sql_advanced("{plain_a} + {plain_b}", configs)
        self.assertEqual(sql_plain.count('SUM(amount)'), 2)
        self.assertIn(' + ', sql_plain)

        # 2. Same column, different filters: two FILTER terms, not one OR'd filter.
        sql = self.Preset.translate_to_sql_advanced("{this_month} + {last_month}", configs)
        self.assertEqual(sql.count('SUM(amount)'), 2)
        self.assertIn('SUM(amount) FILTER (WHERE (date >= "2024-01-01"))', sql)
        self.assertIn('SUM(amount) FILTER (WHERE (date >= "2023-12-01" AND date < "2024-01-01"))', sql)
        self.assertNotIn(') OR (', sql)

        # 3. Subtraction — unchanged, still two terms.
        sql_sub = self.Preset.translate_to_sql_advanced("{this_month} - {last_month}", configs)
        self.assertEqual(sql_sub.count('SUM(amount)'), 2)
        self.assertIn(' - ', sql_sub)

        # 4. Different columns — unchanged.
        sql_diff = self.Preset.translate_to_sql_advanced("{this_month} + {other_col}", configs)
        self.assertIn('SUM(amount)', sql_diff)
        self.assertIn('SUM(qty)', sql_diff)
        self.assertIn(' + ', sql_diff)

        # 5. Repeating the same variable must count it twice, not once.
        sql_triple = self.Preset.translate_to_sql_advanced(
            "{this_month} + {last_month} + {this_month}", configs)
        self.assertEqual(sql_triple.count('SUM(amount)'), 3)

    def test_round_two_args_casts_to_numeric(self):
        """round(x, n) must work when x came out of a division.

        Division casts to ::float and PostgreSQL has no
        round(double precision, integer), so the value is cast back to numeric.
        """
        sql = self.Preset.translate_to_sql("round({a} / {b} * 100, 2)", {'a': 'col_a', 'b': 'col_b'})
        self.assertIn('::numeric', sql)
        self.assertTrue(sql.startswith('ROUND('))

        # Single-argument round is left alone.
        sql_one = self.Preset.translate_to_sql("round({a})", {'a': 'col_a'})
        self.assertEqual(sql_one, 'ROUND(col_a)')

    def test_row_level_never_aggregates(self):
        """Row-level presets must emit bare columns, not SUM()."""
        configs = [
            {'name': 'a', 'column': 'amount', 'aggregate': 'SUM', 'filter_domain': ''},
            {'name': 'b', 'column': 'amount', 'aggregate': 'SUM', 'filter_domain': ''},
        ]
        sql = self.Preset.translate_to_sql_advanced("{a} + {b}", configs, None, 'row')
        self.assertNotIn('SUM(', sql)
        self.assertEqual(sql, '(amount + amount)')

    def test_row_level_filter_becomes_case_when(self):
        """A row-level filter is a CASE WHEN, not a FILTER clause."""
        configs = [{'name': 'a', 'column': 'amount', 'aggregate': 'SUM',
                    'filter_domain': "state = 'draft'"}]
        sql = self.Preset.translate_to_sql_advanced("{a}", configs, None, 'row')
        self.assertIn('CASE WHEN', sql)
        self.assertNotIn('FILTER', sql)
