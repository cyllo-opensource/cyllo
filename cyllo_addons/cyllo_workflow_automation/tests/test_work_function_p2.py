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
import base64

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestWorkFunctionP2(TransactionCase):
    """Phase-2 tests for work.function: button_click, studio_wf_ normalization,
    new trigger types (write, unlink), and _ensure_button_trigger."""

    def setUp(self):
        super().setUp()
        self.WorkFunction = self.env['work.function']
        self.model_partner = self.env['ir.model'].search(
            [('model', '=', 'res.partner')], limit=1
        )

    def _make_func(self, **kw):
        vals = {'name': 'Test Func', 'func_name': 'test_func', 'trigger_type': 'other'}
        vals.update(kw)
        return self.WorkFunction.create(vals)

    # ─────────────────────── trigger_type values added in phase-2 ───────────────

    def test_01_trigger_type_write_accepted(self):
        """trigger_type='write' is a valid selection in phase-2."""
        func = self._make_func(func_name='write', trigger_type='write')
        self.assertEqual(func.trigger_type, 'write')

    def test_02_trigger_type_unlink_accepted(self):
        """trigger_type='unlink' is valid in phase-2."""
        func = self._make_func(func_name='unlink', trigger_type='unlink')
        self.assertEqual(func.trigger_type, 'unlink')

    def test_03_trigger_type_button_click_accepted(self):
        """trigger_type='button_click' is valid in phase-2."""
        func = self._make_func(func_name='btn_action', trigger_type='button_click')
        self.assertEqual(func.trigger_type, 'button_click')

    def test_04_all_phase2_trigger_types_present(self):
        """All expected trigger_type selection keys present on work.function."""
        expected = {
            'create', 'write', 'unlink', 'time',
            'new_action', 'field_change', 'other', 'button_click',
        }
        field = self.WorkFunction._fields['trigger_type']
        keys = {k for k, _ in field.selection}
        self.assertTrue(expected.issubset(keys))

    # ────────────────────── _is_studio_workflow_func_name ───────────────────────

    def test_05_is_studio_func_name_true_for_prefix(self):
        """_is_studio_workflow_func_name returns True for 'studio_wf_' prefix."""
        self.assertTrue(
            self.WorkFunction._is_studio_workflow_func_name('studio_wf_approve')
        )

    def test_06_is_studio_func_name_false_for_regular(self):
        """_is_studio_workflow_func_name returns False for regular names."""
        self.assertFalse(
            self.WorkFunction._is_studio_workflow_func_name('write')
        )

    def test_07_is_studio_func_name_false_for_empty(self):
        """_is_studio_workflow_func_name returns False for empty/None."""
        self.assertFalse(self.WorkFunction._is_studio_workflow_func_name(''))
        self.assertFalse(self.WorkFunction._is_studio_workflow_func_name(None))

    # ────────────────────── _normalize_button_click_vals ────────────────────────

    def test_08_normalize_sets_button_click_for_studio_prefix(self):
        """_normalize_button_click_vals forces trigger_type='button_click' for studio_ prefix."""
        vals = {'func_name': 'studio_wf_approve', 'name': 'Approve'}
        normalized = self.WorkFunction._normalize_button_click_vals(vals)
        self.assertEqual(normalized['trigger_type'], 'button_click')

    def test_09_normalize_leaves_non_studio_unchanged(self):
        """_normalize_button_click_vals does not alter non-studio func names."""
        vals = {'func_name': 'write', 'trigger_type': 'write', 'name': 'Write'}
        normalized = self.WorkFunction._normalize_button_click_vals(vals)
        self.assertEqual(normalized['trigger_type'], 'write')

    def test_10_normalize_does_not_mutate_original_dict(self):
        """_normalize_button_click_vals returns a new dict, not the original."""
        vals = {'func_name': 'studio_wf_reject', 'name': 'Reject'}
        normalized = self.WorkFunction._normalize_button_click_vals(vals)
        self.assertIsNot(normalized, vals)

    # ─────────── create/write call _normalize_button_click_vals automatically ───

    def test_11_create_with_studio_prefix_auto_sets_button_click(self):
        """Creating work.function with studio_wf_ prefix auto-sets button_click trigger."""
        func = self.WorkFunction.create({
            'name': 'Studio Approve',
            'func_name': 'studio_wf_approve',
        })
        self.assertEqual(func.trigger_type, 'button_click')

    def test_12_write_with_studio_prefix_auto_sets_button_click(self):
        """Writing studio_wf_ func_name on existing record sets button_click."""
        func = self._make_func(func_name='old_func', trigger_type='other')
        func.write({'func_name': 'studio_wf_action'})
        self.assertEqual(func.trigger_type, 'button_click')

    # ────────────────────── _ensure_button_trigger ──────────────────────────────

    def test_13_ensure_button_trigger_creates_record(self):
        """_ensure_button_trigger creates a button_click work.function if absent."""
        func = self.WorkFunction._ensure_button_trigger(
            'res.partner', 'studio_wf_test_ensure'
        )
        self.assertTrue(func.id)
        self.assertEqual(func.trigger_type, 'button_click')
        self.assertEqual(func.func_name, 'studio_wf_test_ensure')

    def test_14_ensure_button_trigger_is_idempotent(self):
        """_ensure_button_trigger returns existing record on second call."""
        f1 = self.WorkFunction._ensure_button_trigger(
            'res.partner', 'studio_wf_idempotent'
        )
        f2 = self.WorkFunction._ensure_button_trigger(
            'res.partner', 'studio_wf_idempotent'
        )
        self.assertEqual(f1.id, f2.id)

    def test_15_ensure_button_trigger_returns_empty_for_missing_model(self):
        """_ensure_button_trigger returns empty recordset for unknown model."""
        result = self.WorkFunction._ensure_button_trigger(
            'nonexistent.model.xyz', 'studio_wf_x'
        )
        self.assertFalse(result)

    def test_16_ensure_button_trigger_returns_empty_for_blank_args(self):
        """_ensure_button_trigger returns empty recordset when model or func_name blank."""
        self.assertFalse(self.WorkFunction._ensure_button_trigger('', 'studio_wf_x'))
        self.assertFalse(self.WorkFunction._ensure_button_trigger('res.partner', ''))

    # ─────────────────── button_click code generation ───────────────────────────

    def test_17_button_click_make_function_returns_false(self):
        """Generated code for button_click trigger contains 'return False'."""
        func = self.WorkFunction.create({
            'name': 'Studio Action',
            'func_name': 'studio_wf_do_something',
        })
        self.assertIn('return False', func.c_make_function)

    def test_18_button_click_make_function_has_guard_key(self):
        """Generated button_click code includes the guard_key pattern."""
        func = self.WorkFunction.create({
            'name': 'Studio Action 2',
            'func_name': 'studio_wf_check_guard',
        })
        self.assertIn('guard_key', func.c_make_function)

    def test_19_regular_trigger_make_function_returns_res(self):
        """Regular ORM trigger code uses 'res' return variable (not False)."""
        func = self._make_func(func_name='create', trigger_type='create', has_return=True)
        self.assertIn('return res', func.c_make_function)

    def test_20_mode_is_auto_without_make_function(self):
        """mode is 'auto' when make_function is empty."""
        func = self._make_func()
        self.assertEqual(func.mode, 'auto')

    def test_21_mode_is_manual_with_make_function(self):
        """mode is 'manual' when make_function is provided."""
        func = self._make_func(make_function='def my_func(): pass')
        self.assertEqual(func.mode, 'manual')

    def test_22_icon_validation_rejects_non_svg(self):
        """Uploading a non-SVG binary raises ValidationError."""
        with self.assertRaises(ValidationError):
            self._make_func(icon=base64.b64encode(b'not-an-svg').decode())

    def test_23_icon_validation_accepts_valid_svg(self):
        """Uploading valid SVG binary is accepted."""
        svg = b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
        func = self._make_func(icon=base64.b64encode(svg).decode())
        self.assertTrue(func.icon)

    def test_24_compute_mode_is_separate_method(self):
        """compute_mode is a separate method from compute_c_make_function."""
        self.assertTrue(hasattr(self.WorkFunction, 'compute_mode'))
        self.assertTrue(callable(self.WorkFunction.compute_mode))

    def test_25_trigger_type_in_generated_code(self):
        """Generated c_make_function embeds the trigger_type value."""
        func = self._make_func(func_name='write', trigger_type='write')
        self.assertIn("'write'", func.c_make_function)
