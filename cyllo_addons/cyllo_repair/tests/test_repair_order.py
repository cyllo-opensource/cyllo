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
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


class TestRepairOrderTimer(TransactionCase):
    """Tests for the custom fields/methods added to ``repair.order``."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Repair = cls.env['repair.order']
        cls.Policy = cls.env['repair.time.allocation.policy']
        cls.Employee = cls.env['hr.employee']
        cls.ICP = cls.env['ir.config_parameter']
        cls.category_parent = cls.env['product.category'].create({
            'name': 'Test Electronics',
        })
        cls.category_child = cls.env['product.category'].create({
            'name': 'Test Laptops',
            'parent_id': cls.category_parent.id,
        })
        cls.product_with_specific_policy = cls.env['product.product'].create({
            'name': 'Test Laptop',
            'type': 'consu',
            'categ_id': cls.category_child.id,
        })
        cls.product_category_only = cls.env['product.product'].create({
            'name': 'Test Tablet',
            'type': 'consu',
            'categ_id': cls.category_child.id,
        })
        cls.product_no_policy = cls.env['product.product'].create({
            'name': 'Test Screwdriver',
            'type': 'consu',
        })
        cls.policy_product = cls.Policy.create({
            'name': 'Laptop Specific Policy',
            'target_type': 'product',
            'product_id': cls.product_with_specific_policy.id,
            'allocated_duration': 2.0,
            'sequence': 1,
            'active': True,
        })
        cls.policy_category = cls.Policy.create({
            'name': 'Electronics Category Policy',
            'target_type': 'category',
            'product_category_id': cls.category_parent.id,
            'allocated_duration': 5.0,
            'sequence': 10,
            'active': True,
        })
        cls.operator_1 = cls.Employee.create({'name': 'Operator One'})
        cls.operator_2 = cls.Employee.create({'name': 'Operator Two'})
        cls.partner = cls.env['res.partner'].create({'name': 'Test Customer'})

    def _create_repair(self, product, operators=None):
        vals = {
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_qty': 1.0,
            'partner_id': self.partner.id,
        }
        if operators:
            vals['operator_ids'] = [(6, 0, operators.ids)]
        return self.Repair.create(vals)

    def _set_limit(self, value):
        self.ICP.sudo().set_param('repair.max_active_orders', value)

    def test_allocation_policy_prefers_product_specific(self):
        """A product with its own policy must use it over a matching
        category-level policy, even though both technically apply."""
        repair = self._create_repair(self.product_with_specific_policy)
        self.assertEqual(repair.allocation_policy_id, self.policy_product)
        self.assertEqual(repair.allocated_duration, 2.0)

    def test_allocation_policy_falls_back_to_category(self):
        """A product without a dedicated policy should inherit the
        policy defined on its (parent) category."""
        repair = self._create_repair(self.product_category_only)
        self.assertEqual(repair.allocation_policy_id, self.policy_category)
        self.assertEqual(repair.allocated_duration, 5.0)

    def test_allocation_policy_none_when_no_match(self):
        """No matching policy should leave allocation_policy_id empty
        and allocated_duration at its default of 0."""
        repair = self._create_repair(self.product_no_policy)
        self.assertFalse(repair.allocation_policy_id)
        self.assertEqual(repair.allocated_duration, 0.0)

    def test_inactive_policy_is_ignored(self):
        """Archived (active=False) policies must never be selected."""
        self.policy_product.active = False
        repair = self._create_repair(self.product_with_specific_policy)
        self.assertEqual(repair.allocation_policy_id,self.policy_category)

    def test_allocated_duration_recomputes_on_policy_change(self):
        """allocated_duration is stored & editable (readonly=False): it
        should follow the policy whenever allocation_policy_id changes,
        but otherwise keep whatever value the user set manually."""
        repair = self._create_repair(self.product_with_specific_policy)
        self.assertEqual(repair.allocated_duration, 2.0)

        # Manual override sticks as long as the dependency doesn't change.
        repair.allocated_duration = 9.0
        self.assertEqual(repair.allocated_duration, 9.0)
        repair.product_id = self.product_category_only
        self.assertEqual(repair.allocation_policy_id, self.policy_category)
        self.assertEqual(repair.allocated_duration, 5.0)

    def test_progress_on_track_below_80_percent(self):
        """Progress below 80% should be marked as on_track."""
        repair = self._create_repair(self.product_with_specific_policy)
        repair.allocated_duration = 10.0
        repair.total_accumulated_time = 5.0  # 50%
        self.assertEqual(repair.progress_percentage, 50.0)
        self.assertEqual(repair.time_status, 'on_track')

    def test_progress_warning_between_80_and_100_percent(self):
        """Progress between 80% and 100% should trigger warning status."""
        repair = self._create_repair(self.product_with_specific_policy)
        repair.allocated_duration = 10.0
        repair.total_accumulated_time = 9.0  # 90%
        self.assertEqual(repair.progress_percentage, 90.0)
        self.assertEqual(repair.time_status, 'warning')

    def test_progress_overdue_above_100_percent_caps_at_100(self):
        """Progress above allocation should be capped at 100% and marked overdue."""
        repair = self._create_repair(self.product_with_specific_policy)
        repair.allocated_duration = 10.0
        repair.total_accumulated_time = 15.0  # 150%
        self.assertEqual(repair.progress_percentage, 100.0)
        self.assertEqual(repair.time_status, 'overdue')

    def test_progress_zero_allocation_gives_no_status(self):
        """No allocation duration should result in zero progress and no status."""
        repair = self._create_repair(self.product_no_policy)
        repair.total_accumulated_time = 3.0
        self.assertEqual(repair.allocated_duration, 0.0)
        self.assertEqual(repair.progress_percentage, 0.0)
        self.assertFalse(repair.time_status)

    def test_actual_duration_when_timer_stopped(self):
        """Actual duration should equal accumulated time when timer is stopped."""
        repair = self._create_repair(self.product_no_policy)
        repair.total_accumulated_time = 4.5
        repair.is_timer_running = False
        self.assertEqual(repair.actual_duration, 4.5)

    def test_actual_duration_when_timer_running(self):
        """Actual duration should include accumulated and currently running time."""
        repair = self._create_repair(self.product_no_policy)
        repair.total_accumulated_time = 1.0
        repair.current_start_time = fields.Datetime.now() - timedelta(hours=2)
        repair.is_timer_running = True
        # ~1h already accumulated + ~2h elapsed in the current session.
        self.assertAlmostEqual(repair.actual_duration, 3.0, delta=0.02)

    def test_action_repair_start_blocks_when_operator_at_limit(self):
        """Starting a repair should fail when an operator reaches the active-order limit."""
        self._set_limit('1')
        repair_a = self._create_repair(self.product_no_policy, self.operator_1)
        repair_b = self._create_repair(self.product_no_policy, self.operator_1)
        repair_a.action_validate()
        repair_a.action_repair_start()
        self.assertTrue(repair_a.is_timer_running)
        repair_b.action_validate()
        with self.assertRaises(UserError):
            repair_b.action_repair_start()

    def test_action_repair_start_allows_different_operators(self):
        """Different operators should be able to start repairs independently."""
        self._set_limit('1')
        repair_a = self._create_repair(self.product_no_policy, self.operator_1)
        repair_b = self._create_repair(self.product_no_policy, self.operator_2)
        repair_a.action_validate()
        repair_a.action_repair_start()
        repair_b.action_validate()
        repair_b.action_repair_start()
        self.assertTrue(repair_b.is_timer_running)

    def test_action_repair_start_unlimited_when_param_is_zero(self):
        """A limit value of zero should disable workload restrictions."""
        self._set_limit('0')
        repair_a = self._create_repair(self.product_no_policy, self.operator_1)
        repair_b = self._create_repair(self.product_no_policy, self.operator_1)
        repair_a.action_validate()
        repair_a.action_repair_start()
        repair_b.action_validate()
        repair_b.action_repair_start()
        self.assertTrue(repair_b.is_timer_running)

    def test_action_repair_start_sets_timer_fields(self):
        """Starting a repair should initialize timer tracking fields."""
        repair = self._create_repair(self.product_no_policy, self.operator_1)
        repair.action_validate()
        before = fields.Datetime.now()
        repair.action_repair_start()
        self.assertTrue(repair.is_timer_running)
        self.assertTrue(repair.current_start_time)
        self.assertGreaterEqual(
            repair.current_start_time, before - timedelta(seconds=5)
        )

    def test_action_repair_pause_accumulates_time_and_stops_timer(self):
        """Pausing a repair should accumulate elapsed time and stop the timer."""
        repair = self._create_repair(self.product_no_policy, self.operator_1)
        repair.write({
            'current_start_time': fields.Datetime.now() - timedelta(hours=1),
            'is_timer_running': True,
            'total_accumulated_time': 2.0,
        })
        repair.action_repair_pause()
        self.assertFalse(repair.is_timer_running)
        self.assertFalse(repair.current_start_time)
        self.assertAlmostEqual(repair.total_accumulated_time, 3.0, delta=0.02)

    def test_action_repair_pause_noop_when_timer_not_running(self):
        """Pausing an inactive timer should leave repair timing unchanged."""
        repair = self._create_repair(self.product_no_policy, self.operator_1)
        repair.total_accumulated_time = 1.5
        repair.action_repair_pause()
        self.assertEqual(repair.total_accumulated_time, 1.5)
        self.assertFalse(repair.is_timer_running)

    def test_action_repair_end_finalizes_running_timer(self):
        """Ending a repair should finalize elapsed time and clear timer state."""
        repair = self._create_repair(self.product_no_policy, self.operator_1)
        repair.action_validate()
        repair.action_repair_start()
        repair.current_start_time = fields.Datetime.now() - timedelta(hours=1)
        repair.action_repair_end()
        self.assertFalse(repair.is_timer_running)
        self.assertFalse(repair.current_start_time)
        self.assertAlmostEqual(repair.total_accumulated_time, 1.0, delta=0.02)
        self.assertNotEqual(repair.state, 'under_repair')