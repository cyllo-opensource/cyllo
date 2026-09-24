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

from odoo.tests import tagged, TransactionCase
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestPosKitchenScreen(TransactionCase):
    """Test suite for POS Kitchen Screen module (stages, screen, and POS order integration)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create customer
        cls.customer = cls.env['res.partner'].create({
            'name': 'Kitchen Customer',
            'email': 'kitchen@test.com',
        })

        # Create products
        cls.product_food = cls.env['product.product'].create({
            'name': 'Pizza',
            'type': 'consu',
            'available_in_pos': True,
        })
        cls.product_drink = cls.env['product.product'].create({
            'name': 'Soda',
            'type': 'consu',
            'available_in_pos': True,
        })

        # Find or create a pricelist
        cls.pricelist = cls.env['product.pricelist'].search([], limit=1)
        if not cls.pricelist:
            cls.pricelist = cls.env['product.pricelist'].create({
                'name': 'POS Default Pricelist',
            })

        # Find or create POS Configuration
        cls.pos_config = cls.env['pos.config'].search([('module_pos_restaurant', '=', True)], limit=1)
        if not cls.pos_config:
            journal = cls.env['account.journal'].search([('type', '=', 'sale')], limit=1)
            cls.pos_config = cls.env['pos.config'].create({
                'name': 'Kitchen Test POS Restaurant',
                'module_pos_restaurant': True,
                'journal_id': journal.id if journal else False,
                'pricelist_id': cls.pricelist.id,
            })

        # Find or create POS Session
        cls.pos_session = cls.env['pos.session'].search([
            ('config_id', '=', cls.pos_config.id),
            ('state', '!=', 'closed'),
        ], limit=1)
        if not cls.pos_session:
            cls.pos_session = cls.env['pos.session'].create({
                'config_id': cls.pos_config.id,
                'user_id': cls.env.user.id,
            })

    def setUp(self):
        super().setUp()
        # Create a kitchen screen for the config
        self.kitchen_screen = self.env['kitchen.screen'].create({
            'pos_config_id': self.pos_config.id,
        })

    def _create_pos_order(self, pos_reference, qty=1, product=None, is_cooking=False):
        product = product or self.product_food
        total = qty * 10.0
        return self.env['pos.order'].create({
            'session_id': self.pos_session.id,
            'partner_id': self.customer.id,
            'pos_reference': pos_reference,
            'pricelist_id': self.pricelist.id,
            'amount_tax': 0.0,
            'amount_total': total,
            'amount_paid': total,
            'amount_return': 0.0,
            'is_cooking': is_cooking,
            'lines': [(0, 0, {
                'product_id': product.id,
                'qty': qty,
                'price_unit': 10.0,
                'price_subtotal': total,
                'price_subtotal_incl': total,
                'is_cooking': is_cooking,
            })]
        })

    def test_kitchen_screen_creation_and_defaults(self):
        """Test default stages and sequence generation during kitchen screen creation."""
        self.assertNotEqual(self.kitchen_screen.sequence, 'New')
        stages = self.kitchen_screen.stage_ids
        # Should have Draft (not done, not cancelled), Completed (is_done), and Cancelled (is_cancelled)
        self.assertEqual(len(stages), 3)

        completed_stages = stages.filtered(lambda s: s.is_done)
        cancelled_stages = stages.filtered(lambda s: s.is_cancelled)
        self.assertEqual(len(completed_stages), 1)
        self.assertEqual(len(cancelled_stages), 1)

    def test_kitchen_screen_stage_constraints(self):
        """Test constraints validating that stages are correctly configured."""
        draft_stage = self.kitchen_screen.stage_ids.filtered(lambda s: not s.is_done and not s.is_cancelled)[0]

        # 1. A stage cannot be both completed and cancelled
        with self.assertRaises(ValidationError):
            draft_stage.write({
                'is_done': True,
                'is_cancelled': True,
            })

        # 2. Only one Completed stage is allowed per screen
        with self.assertRaises(ValidationError):
            self.env['kitchen.screen.stage'].create({
                'name': 'Another Completed Stage',
                'is_done': True,
                'is_cancelled': False,
                'kitchen_screen_id': self.kitchen_screen.id,
            })

        # 3. Only one Cancelled stage is allowed per screen
        with self.assertRaises(ValidationError):
            self.env['kitchen.screen.stage'].create({
                'name': 'Another Cancelled Stage',
                'is_done': False,
                'is_cancelled': True,
                'kitchen_screen_id': self.kitchen_screen.id,
            })

    def test_kitchen_screen_action_redirect(self):
        """Test the action redirect URL format."""
        action = self.kitchen_screen.kitchen_screen()
        self.assertEqual(action.get('type'), 'ir.actions.act_url')
        self.assertEqual(action.get('target'), 'new')
        self.assertIn(f'pos_config_id= {self.pos_config.id}', action.get('url'))

    def test_pos_order_payment_and_kitchen_propagation(self):
        """Test that paying a POS order puts it into the kitchen workflow."""
        pos_order = self._create_pos_order('Chomp/0002', qty=2)

        self.assertFalse(pos_order.is_cooking)

        # Trigger order payment/finalization
        pos_order.action_pos_order_paid()

        self.assertTrue(pos_order.is_cooking)
        self.assertEqual(pos_order.order_ref, pos_order.name)

        # Should be placed into the first active stage (Draft)
        draft_stage = self.kitchen_screen.stage_ids.filtered(lambda s: s.name == 'Draft')
        self.assertEqual(pos_order.kitchen_stage_id, draft_stage)
        self.assertEqual(pos_order.order_status, 'waiting')

    def test_refund_does_not_merge_into_original_order(self):
        pos_order = self._create_pos_order('Chomp/0012', qty=1)
        original_amount_total = pos_order.amount_total
        original_line_count = len(pos_order.lines)

        refund_vals = {
            'session_id': self.pos_session.id,
            'partner_id': self.customer.id,
            'pos_reference': 'Chomp/0012',  # same as original, like a real refund
            'pricelist_id': self.pricelist.id,
            'amount_tax': 0.0,
            'amount_total': -original_amount_total,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'lines': False,
        }

        refund_order = self.env['pos.order'].with_context(
            skip_pos_reference_dedup=True).create(refund_vals)

        self.assertNotEqual(refund_order.id, pos_order.id)
        self.assertEqual(refund_order.amount_total, -original_amount_total)

        # The original order must be completely untouched.
        pos_order.invalidate_recordset()
        self.assertEqual(pos_order.amount_total, original_amount_total)
        self.assertEqual(len(pos_order.lines), original_line_count)

        # Both orders legitimately share the same pos_reference now, and
        # both must still exist as separate records.
        matching_orders = self.env['pos.order'].search(
            [('pos_reference', '=', 'Chomp/0012')])
        self.assertEqual(len(matching_orders), 2)

    def test_kitchen_time_and_floor_never_false(self):
        """Regression test: hour/minutes/floor must be derived server-side from
        date_order/table_id, so they are always populated (never the raw
        boolean False that used to render as the literal text 'false' on the
        Kitchen Screen) regardless of which flow put the order there."""
        pos_order = self._create_pos_order('Chomp/0011', qty=1)

        # Even without going through the "Send to Kitchen" JS flow (which used
        # to be the only place hour/minutes/floor got populated), the computed
        # fields must already report real values derived from date_order.
        self.assertTrue(pos_order.date_order)
        self.assertEqual(pos_order.hour, "%02d" % pos_order.date_order.hour)
        self.assertEqual(pos_order.minutes, "%02d" % pos_order.date_order.minute)
        # No table assigned -> floor should be an empty string, never False.
        self.assertEqual(pos_order.floor, "")
        self.assertNotEqual(pos_order.floor, False)

        # Simulate payment-triggered entry into the kitchen workflow.
        pos_order.action_pos_order_paid()
        self.assertEqual(pos_order.hour, "%02d" % pos_order.date_order.hour)
        self.assertEqual(pos_order.minutes, "%02d" % pos_order.date_order.minute)

    def test_payment_does_not_resend_completed_kitchen_order(self):
        """Regression test for the reported bug: sending an order to the kitchen,
        moving it to 'Completed', and then validating payment must NOT recreate
        or resend the kitchen order (i.e. must not reset it back to the first
        active stage)."""
        pos_order = self._create_pos_order('Chomp/0010', qty=1)

        # 1. Simulate "Send to Kitchen": order enters the kitchen workflow.
        draft_stage = self.kitchen_screen.stage_ids.filtered(
            lambda s: s.name == 'Draft')
        pos_order.set_kitchen_stage(draft_stage.id)
        self.assertEqual(pos_order.kitchen_stage_id, draft_stage)

        # 2. Kitchen staff moves the order to "Completed".
        completed_stage = self.kitchen_screen.stage_ids.filtered(
            lambda s: s.is_done)
        pos_order.set_kitchen_stage(completed_stage.id)
        self.assertEqual(pos_order.kitchen_stage_id, completed_stage)
        self.assertEqual(pos_order.order_status, 'ready')

        # 3. Cashier validates payment.
        pos_order.action_pos_order_paid()

        # The order must still be in the Completed stage - payment validation
        # must not resend/reset it back to the first active (Draft) stage,
        # which is what caused the order to reappear as a "duplicate" on the
        # Kitchen Screen.
        self.assertEqual(pos_order.kitchen_stage_id, completed_stage)
        self.assertEqual(pos_order.order_status, 'ready')

        # Only one pos.order record should exist for this reference - no
        # duplicate order was created by any step of the workflow.
        matching_orders = self.env['pos.order'].search(
            [('pos_reference', '=', 'Chomp/0010')])
        self.assertEqual(len(matching_orders), 1)

    def test_kitchen_order_status_changing_methods(self):
        """Test methods to change kitchen order progress and status (draft, cancel, ready)."""
        pos_order = self._create_pos_order('Chomp/0003', qty=1)

        # 1. Test cancel progress
        pos_order.order_progress_cancel()
        self.assertEqual(pos_order.order_status, 'cancel')
        self.assertTrue(all(line.order_status == 'cancel' for line in pos_order.lines))

        # 2. Test draft/cooking progress
        pos_order.order_progress_draft()
        self.assertEqual(pos_order.order_status, 'waiting')
        self.assertTrue(all(line.order_status == 'waiting' for line in pos_order.lines))

        # 3. Test progress change to ready
        pos_order.order_progress_change()
        self.assertEqual(pos_order.order_status, 'ready')

        # 4. Test force set kitchen status helper
        pos_order.set_kitchen_order_status('waiting')
        self.assertEqual(pos_order.order_status, 'waiting')

    def test_set_kitchen_stage_dynamic_transitions(self):
        """Test transitions using set_kitchen_stage and check mapping to status fields."""
        pos_order = self._create_pos_order('Chomp/0004', qty=1)

        completed_stage = self.kitchen_screen.stage_ids.filtered(lambda s: s.is_done)
        cancelled_stage = self.kitchen_screen.stage_ids.filtered(lambda s: s.is_cancelled)

        # Transition to completed stage
        pos_order.set_kitchen_stage(completed_stage.id)
        self.assertEqual(pos_order.kitchen_stage_id, completed_stage)
        self.assertEqual(pos_order.order_status, 'ready')

        # Transition to cancelled stage
        pos_order.set_kitchen_stage(cancelled_stage.id)
        self.assertEqual(pos_order.kitchen_stage_id, cancelled_stage)
        self.assertEqual(pos_order.order_status, 'cancel')

    def test_check_order_helpers_and_removal(self):
        """Test helper functions checking order status and removing order from kitchen."""
        pos_order = self._create_pos_order('Chomp/0005', qty=1)

        # Default state check
        status_valid = pos_order.check_order('Chomp/0005')
        self.assertTrue(status_valid)

        status_str = pos_order.check_order_status('Chomp/0005')
        self.assertTrue(status_str)

        # Test remove from kitchen
        pos_order.action_pos_order_paid()
        self.assertTrue(pos_order.is_cooking)

        pos_order.remove_from_kitchen()
        self.assertFalse(pos_order.is_cooking)
        self.assertFalse(pos_order.kitchen_stage_id)
        self.assertTrue(all(not line.is_cooking for line in pos_order.lines))

    def test_get_details_payload_and_legacy_backfill(self):
        """Test get_details fetches accurate details and backfills legacy orders without stages."""
        pos_order = self._create_pos_order('Chomp/0006', qty=1, is_cooking=True)

        details = self.env['pos.order'].get_details(self.pos_config.id)
        self.assertIn('orders', details)
        self.assertIn('order_lines', details)
        self.assertIn('stages', details)

        # Verify that 'All' stage got auto-created and added to the list of stages
        stage_names = [stage['name'] for stage in details['stages']]
        self.assertIn('All', stage_names)

        # Verify that legacy orders (with is_cooking=True but no kitchen_stage_id) got backfilled
        self.assertTrue(pos_order.kitchen_stage_id)
        self.assertEqual(pos_order.order_status, 'waiting')

    def test_pos_session_ui_load(self):
        """Test that session loading parameters list required models."""
        session = self.pos_session
        models_to_load = session._pos_ui_models_to_load()
        self.assertIn('pos.order', models_to_load)
        self.assertIn('pos.order.line', models_to_load)

        # Test param loading methods execute successfully
        params_order = session._loader_params_pos_order()
        self.assertIn('fields', params_order.get('search_params', {}))

        params_line = session._loader_params_pos_order_line()
        self.assertIn('fields', params_line.get('search_params', {}))
