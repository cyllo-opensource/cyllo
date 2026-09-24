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


class TestNodeStructP2(TransactionCase):
    """Phase-2 tests for node.struct: new node types, new fields,
    save_data valid_data filtering, and create_editable_reuse_copy."""

    def setUp(self):
        super().setUp()
        self.NodeStruct = self.env['node.struct']
        self.model_partner = self.env['ir.model'].search(
            [('model', '=', 'res.partner')], limit=1
        )
        self.work_auto = self.env['work.auto'].create({
            'name': 'P2 Node Test WA',
            'model_id': self.model_partner.id,
        })

    def _make_node(self, **kw):
        vals = {'name': 'test_node', 'work_auto_id': self.work_auto.id}
        vals.update(kw)
        return self.NodeStruct.create(vals)

    # ───────────────────────── reuse fields ─────────────────────────────────────

    def test_01_reused_work_auto_id_field_exists(self):
        """node.struct has reused_work_auto_id Many2one field."""
        node = self._make_node()
        self.assertIn('reused_work_auto_id', node._fields)

    def test_02_reused_work_auto_id_stores_reference(self):
        """reused_work_auto_id stores a work.auto reference."""
        reusable = self.env['work.auto'].create({
            'name': 'Reusable WA',
            'model_id': self.model_partner.id,
            'is_reusable': True,
        })
        node = self._make_node(reused_work_auto_id=reusable.id)
        self.assertEqual(node.reused_work_auto_id, reusable)

    def test_03_reused_variable_field_exists(self):
        """node.struct has reused_variable Char field."""
        node = self._make_node()
        self.assertIn('reused_variable', node._fields)

    # ───────────────────────── new type selections ───────────────────────────────

    def test_04_type_action_accepted(self):
        """type='action' is a valid selection in phase-2."""
        node = self._make_node(type='action')
        self.assertEqual(node.type, 'action')

    def test_05_type_action_to_do_accepted(self):
        """type='action_to_do' is a valid selection in phase-2."""
        node = self._make_node(type='action_to_do')
        self.assertEqual(node.type, 'action_to_do')

    # ───────────────────────── WhatsApp fields ───────────────────────────────────

    def test_06_whatsapp_fields_exist(self):
        """WhatsApp-specific fields are present on node.struct."""
        wa_fields = [
            'wa_partner_path', 'wa_free_message', 'wa_template',
            'wa_is_template', 'wa_attachment_mode',
        ]
        node = self._make_node()
        for field_name in wa_fields:
            self.assertIn(field_name, node._fields, f"Missing field: {field_name}")

    def test_07_wa_is_template_default_false(self):
        """wa_is_template defaults to False (Free-form, not required)."""
        node = self._make_node()
        self.assertFalse(node.wa_is_template)

    # ───────────────────────── Window fields ─────────────────────────────────────

    def test_08_window_fields_exist(self):
        """Window-specific fields are present on node.struct."""
        window_fields = [
            'window_view_type', 'window_action_id', 'window_target',
        ]
        node = self._make_node()
        for field_name in window_fields:
            self.assertIn(field_name, node._fields, f"Missing field: {field_name}")

    # ───────────────────────── Webhook fields ────────────────────────────────────

    def test_09_webhook_fields_exist(self):
        """Webhook-specific fields are present on node.struct."""
        webhook_fields = [
            'webhook_url', 'webhook_method', 'webhook_headers',
            'webhook_payload', 'webhook_actions',
        ]
        node = self._make_node()
        for field_name in webhook_fields:
            self.assertIn(field_name, node._fields, f"Missing field: {field_name}")

    # ───────────────────────── Duplicate fields ──────────────────────────────────

    def test_10_duplicate_fields_exist(self):
        """Duplicate-specific fields are present on node.struct."""
        dup_fields = ['duplicate_record', 'duplicate_field_overrides', 'duplicate_result_variable']
        node = self._make_node()
        for field_name in dup_fields:
            self.assertIn(field_name, node._fields, f"Missing field: {field_name}")

    # ───────────────────────── TryCatch fields ───────────────────────────────────

    def test_11_try_catch_fields_exist(self):
        """TryCatch-specific fields are present on node.struct."""
        tc_fields = ['try_catch_error_variable', 'try_catch_error_types']
        node = self._make_node()
        for field_name in tc_fields:
            self.assertIn(field_name, node._fields, f"Missing field: {field_name}")

    # ───────────────────────── Loop fields ───────────────────────────────────────

    def test_12_loop_fields_exist(self):
        """Loop-specific fields are present on node.struct."""
        loop_fields = ['loop_source_type', 'loop_collection', 'loop_variable_name']
        node = self._make_node()
        for field_name in loop_fields:
            self.assertIn(field_name, node._fields, f"Missing field: {field_name}")

    # ───────────────────────── Approval fields ───────────────────────────────────

    def test_13_approval_fields_exist(self):
        """Approval-specific fields are present on node.struct."""
        approval_fields = [
            'approval_rule_type', 'approval_approver_user_id',
            'approval_approver_group_id', 'approval_timeout_hours',
        ]
        node = self._make_node()
        for field_name in approval_fields:
            self.assertIn(field_name, node._fields, f"Missing field: {field_name}")

    # ───────────────────────── else_setup_code / notification_sticky ─────────────

    def test_14_else_setup_code_field_exists(self):
        """else_setup_code field is present on node.struct."""
        self.assertIn('else_setup_code', self._make_node()._fields)

    def test_15_notification_sticky_field_exists(self):
        """notification_sticky field is present on node.struct."""
        self.assertIn('notification_sticky', self._make_node()._fields)

    # ───────────────────────── save_data valid_data filtering ────────────────────

    def test_16_save_data_ignores_unknown_keys(self):
        """save_data filters unknown keys without raising an error."""
        node = self._make_node()
        node.save_data({'name': 'valid_update', 'totally_fake_field': 'ignored'})
        self.assertEqual(node.name, 'valid_update')

    def test_17_save_data_creates_when_called_on_empty_set(self):
        """save_data on empty recordset creates a new node."""
        new_id = self.NodeStruct.save_data({'name': 'p2_created'})
        self.assertTrue(new_id)
        self.assertTrue(self.NodeStruct.browse(new_id).exists())

    def test_18_save_data_updates_existing_record(self):
        """save_data on existing node updates provided fields."""
        node = self._make_node(name='original')
        node.save_data({'warning_text': 'p2 warning'})
        self.assertEqual(node.warning_text, 'p2 warning')

    def test_19_save_data_accepts_wa_is_template_false(self):
        """save_data stores wa_is_template=False without error."""
        node = self._make_node()
        node.save_data({'wa_is_template': False})
        self.assertFalse(node.wa_is_template)

    # ─────────────────────── create_editable_reuse_copy ─────────────────────────

    def test_20_create_editable_reuse_copy_exists(self):
        """node.struct has create_editable_reuse_copy method."""
        self.assertTrue(hasattr(self.NodeStruct, 'create_editable_reuse_copy'))
        self.assertTrue(callable(self.NodeStruct.create_editable_reuse_copy))

    def test_21_create_editable_reuse_copy_returns_new_record(self):
        """create_editable_reuse_copy returns dict with 'id' of new work.auto."""
        reusable = self.env['work.auto'].create({
            'name': 'Reuse Source',
            'model_id': self.model_partner.id,
            'is_reusable': True,
        })
        reusable.write({'flow_data': {'drawflow': {'Home': {'data': {}}}}})
        node = self._make_node(
            name='Reuse Automation',
            reused_work_auto_id=reusable.id,
        )
        result = node.create_editable_reuse_copy()
        self.assertIsInstance(result, dict)
        self.assertIn('id', result)
        self.assertNotEqual(result['id'], reusable.id)

    def test_22_create_editable_reuse_copy_is_not_reusable(self):
        """Editable copy has is_reusable=False on the copied work.auto."""
        reusable = self.env['work.auto'].create({
            'name': 'Reuse Source 2',
            'model_id': self.model_partner.id,
            'is_reusable': True,
        })
        reusable.write({'flow_data': {'drawflow': {'Home': {'data': {}}}}})
        node = self._make_node(
            name='Reuse Automation',
            reused_work_auto_id=reusable.id,
        )
        result = node.create_editable_reuse_copy()
        copy_wa = self.env['work.auto'].browse(result['id'])
        self.assertFalse(copy_wa.is_reusable)

    # ───────────────────────── code_return_type field ────────────────────────────

    def test_23_code_return_type_field_exists(self):
        """code_return_type field is present on node.struct."""
        self.assertIn('code_return_type', self._make_node()._fields)

    # ───────────────────────── trigger_type on node ───────────────────────────────

    def test_24_trigger_type_char_field_exists(self):
        """node.struct has trigger_type Char field (phase-2 addition)."""
        node = self._make_node()
        self.assertIn('trigger_type', node._fields)

    def test_25_trigger_type_stored_on_node(self):
        """trigger_type value persists on node.struct."""
        node = self._make_node()
        node.write({'trigger_type': 'button_click'})
        self.assertEqual(node.trigger_type, 'button_click')
