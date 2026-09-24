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


class TestIrExtensionsP2(TransactionCase):
    """Phase-2 tests for IR extensions and additional data functions:
    schedule, onchange, loop, and approval_cron seeded records."""

    # ───────────────────── workflowCard still works ─────────────────────────────

    def test_01_workflowcard_type_still_accepted(self):
        """ir.ui.view still accepts 'workflowCard' type in phase-2."""
        view = self.env['ir.ui.view'].create({
            'name': 'P2 WF View',
            'model': 'work.auto',
            'type': 'workflowCard',
            'arch': '<workflowCard></workflowCard>',
        })
        self.assertEqual(view.type, 'workflowCard')

    # ──────────────── phase-1 data functions still present ──────────────────────

    def test_02_on_create_function_present(self):
        """On Create work.function from create.xml still installed in phase-2."""
        func = self.env['work.function'].search(
            [('func_name', '=', 'create')], limit=1
        )
        self.assertTrue(func, "On Create work.function not found")

    def test_03_on_write_function_present(self):
        """On Write work.function from write.xml still installed in phase-2."""
        func = self.env['work.function'].search(
            [('func_name', '=', 'write')], limit=1
        )
        self.assertTrue(func, "On Write work.function not found")

    def test_04_on_unlink_function_present(self):
        """On Unlink work.function from unlink.xml still installed in phase-2."""
        func = self.env['work.function'].search(
            [('func_name', '=', 'unlink')], limit=1
        )
        self.assertTrue(func, "On Unlink work.function not found")

    # ─────────────────── schedule.xml seeded record ─────────────────────────────

    def test_05_on_time_function_present(self):
        """On Time work.function from schedule.xml is installed in phase-2."""
        func = self.env['work.function'].search(
            [('trigger_type', '=', 'time')], limit=1
        )
        self.assertTrue(func, "On Time (schedule) work.function not found")

    def test_06_schedule_function_has_make_function(self):
        """Time-trigger work.function has non-empty c_make_function."""
        func = self.env['work.function'].search(
            [('trigger_type', '=', 'time')], limit=1
        )
        if not func:
            self.skipTest("No time-trigger work.function installed")
        self.assertTrue(func.c_make_function)

    # ─────────────────── onchange.xml seeded record ─────────────────────────────

    def test_07_on_field_change_function_present(self):
        """On Field Change work.function from onchange.xml is installed."""
        func = self.env['work.function'].search(
            [('trigger_type', '=', 'field_change')], limit=1
        )
        self.assertTrue(func, "On Field Change work.function not found")

    def test_08_field_change_function_has_make_function(self):
        """On Field Change work.function has non-empty c_make_function."""
        func = self.env['work.function'].search(
            [('trigger_type', '=', 'field_change')], limit=1
        )
        if not func:
            self.skipTest("No field_change work.function installed")
        self.assertTrue(func.c_make_function, "On Field Change work.function missing c_make_function")

    # ───────────────────── loop.xml seeded record ────────────────────────────────

    def test_09_loop_node_function_present(self):
        """Loop work.function from loop.xml is installed in phase-2."""
        func = self.env['work.function'].search(
            [('func_name', 'like', 'loop')], limit=1
        )
        self.assertTrue(func, "Loop work.function not found")

    # ─────────────────── approval_cron.xml seeded record ────────────────────────

    def test_10_approval_cron_record_installed(self):
        """approval_cron.xml installs at least one ir.cron for approval timeouts."""
        # approval_cron.xml typically seeds an ir.cron; look for it by name pattern
        cron = self.env['ir.cron'].sudo().search(
            [('name', 'ilike', 'approval')], limit=1
        )
        self.assertTrue(
            cron,
            "No ir.cron with 'approval' in name found — approval_cron.xml may not be loaded"
        )

    # ─────────────── default image still SVG ────────────────────────────────────

    def test_11_default_image_is_svg_in_phase2(self):
        """work.auto default image is still valid SVG in phase-2."""
        import base64
        model_partner = self.env['ir.model'].search(
            [('model', '=', 'res.partner')], limit=1
        )
        wa = self.env['work.auto'].create({
            'name': 'P2 Img Test',
            'model_id': model_partner.id,
        })
        self.assertTrue(wa.image_1920)
        decoded = base64.b64decode(wa.image_1920)
        self.assertTrue(
            decoded.startswith(b'<svg') or decoded.startswith(b'<?xml'),
            "Default image is not SVG in phase-2"
        )

    # ─────────────── phase-2 data functions have make_function ──────────────────

    def test_12_phase2_data_functions_have_icons(self):
        """All seeded work.function records with icons have valid binary."""
        import base64
        funcs_with_icons = self.env['work.function'].search([('icon', '!=', False)])
        for func in funcs_with_icons:
            try:
                decoded = base64.b64decode(func.icon)
                self.assertTrue(
                    decoded.startswith(b'<svg') or decoded.startswith(b'<?xml'),
                    f"work.function '{func.func_name}' icon is not SVG"
                )
            except Exception:
                self.fail(f"work.function '{func.func_name}' icon cannot be base64-decoded")

    def test_13_workflowcard_view_mode_still_works(self):
        """ir.actions.act_window.view still accepts workflowCard view_mode in phase-2."""
        action = self.env['ir.actions.act_window'].create({
            'name': 'P2 WF Action',
            'res_model': 'work.auto',
            'view_mode': 'workflowCard',
        })
        entry = self.env['ir.actions.act_window.view'].create({
            'act_window_id': action.id,
            'view_mode': 'workflowCard',
        })
        self.assertEqual(entry.view_mode, 'workflowCard')

    def test_14_approval_trigger_model_installed(self):
        """workflow.approval.trigger model is registered in phase-2."""
        model = self.env['ir.model'].search(
            [('model', '=', 'workflow.approval.trigger')], limit=1
        )
        self.assertTrue(model, "workflow.approval.trigger model not registered")

    def test_15_webhook_response_processor_model_installed(self):
        """webhook.response.processor AbstractModel is registered in the ORM registry."""
        # AbstractModel has no DB table and is not listed in ir.model.
        # Check ORM registry directly.
        self.assertIn('webhook.response.processor', self.env)
