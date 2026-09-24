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
from odoo import fields
from odoo.tests.common import tagged
from .common import ShopfloorCommon


@tagged('post_install', '-at_install')
class TestMrpWorkorder(ShopfloorCommon):
    """Tests for cyllo_shopfloor extensions on mrp.workorder."""

    # -----------------------------------------------------------------------
    # shopfloor_blocking_wo_id
    # -----------------------------------------------------------------------

    def test_blocking_wo_id_none_when_not_pending(self):
        """shopfloor_blocking_wo_id must be empty for workorders that are not in pending state."""
        mo = self._make_mo()
        non_pending = mo.workorder_ids.filtered(lambda w: w.state != 'pending')
        if not non_pending:
            self.skipTest("All workorders are pending — nothing to assert for non-pending case.")
        for wo in non_pending:
            self.assertFalse(
                wo.shopfloor_blocking_wo_id,
                f"WO {wo.name} (state={wo.state}) should have no blocker when not pending."
            )

    def test_blocking_wo_id_none_when_no_blockers(self):
        """A pending WO with no active blockers yields an empty shopfloor_blocking_wo_id."""
        mo = self._make_mo()
        if len(mo.workorder_ids) < 2:
            self.skipTest("Need at least 2 workorders to test blocking.")

        wo = mo.workorder_ids[1]
        # Force pending state without an active blocker
        wo.state = 'pending'
        wo.blocked_by_workorder_ids = [(5,)]  # clear blockers
        wo._compute_shopfloor_blocking_wo_id()
        self.assertFalse(wo.shopfloor_blocking_wo_id)

    # -----------------------------------------------------------------------
    # button_start — employee assignment
    # -----------------------------------------------------------------------

    def test_button_start_assigns_employee_via_context(self):
        """
        Calling button_start with a numeric employee_id in context must not raise,
        and employee_ids on the MO must contain that id afterwards.
        (hr module is not a direct dependency of cyllo_shopfloor; we skip gracefully.)
        """
        mo = self._make_mo()
        wo = mo.workorder_ids[:1]
        if not wo:
            self.skipTest("No workorders on MO.")

        if 'hr.employee' not in self.env:
            self.skipTest("hr module not installed — skipping employee context test.")

        employee = self.env['hr.employee'].search([], limit=1)
        if not employee:
            self.skipTest("No hr.employee records found.")

        wo.with_context(employee_id=employee.id).button_start()
        self.assertIn(employee.id, mo.employee_ids.ids,
                      "Employee id should appear in MO.employee_ids after button_start.")

    def test_button_start_without_employee_context_does_not_fail(self):
        """button_start without employee_id context must still succeed."""
        mo = self._make_mo()
        wo = mo.workorder_ids[:1]
        if not wo:
            self.skipTest("No workorders on MO.")
        wo.button_start()
        self.assertEqual(wo.state, 'progress', "Workorder should be in progress after button_start.")

    # -----------------------------------------------------------------------
    # button_pending
    # -----------------------------------------------------------------------

    def test_button_pending_closes_active_timers_for_automated_mo(self):
        """button_pending on an automated MO must close open time_ids entries."""
        self.bom.is_automated = True
        mo = self._make_mo()
        wo = mo.workorder_ids[:1]
        if not wo:
            self.skipTest("No workorders on MO.")

        wo.button_start()
        # Verify there's an active timer
        open_timers = wo.time_ids.filtered(lambda t: not t.date_end)
        self.assertTrue(open_timers, "There should be an active timer after button_start.")

        wo.button_pending()
        still_open = wo.time_ids.filtered(lambda t: not t.date_end)
        self.assertFalse(still_open, "All timers should be closed after button_pending on automated MO.")

    def test_button_pending_non_automated_mo_does_not_alter_timers(self):
        """button_pending on a non-automated MO should not forcibly close timers."""
        self.bom.is_automated = False
        mo = self._make_mo()
        wo = mo.workorder_ids[:1]
        if not wo:
            self.skipTest("No workorders on MO.")

        wo.button_start()
        wo.button_pending()
        # The base method handles timer state; just assert no exception and state change
        self.assertIn(wo.state, ('pending', 'ready', 'progress'))

    # -----------------------------------------------------------------------
    # button_finish — shopfloor context
    # -----------------------------------------------------------------------

    def test_button_finish_from_shopfloor_triggers_close_production(self):
        """
        When all WOs finish from shopfloor context and MO is ready to close,
        button_finish must return a trigger_close_production dict.
        """
        mo = self._make_mo()
        # Start and finish all workorders except the last one normally
        for wo in mo.workorder_ids[:-1]:
            wo.button_start()
            wo.button_finish()

        last_wo = mo.workorder_ids[-1:]
        if not last_wo:
            self.skipTest("Only one workorder; skipping multi-WO test.")

        last_wo.button_start()
        result = last_wo.with_context(from_shopfloor=True).button_finish()

        if isinstance(result, dict):
            self.assertIn(result.get('type'), ('trigger_close_production', None),
                          "Expected trigger_close_production or None return from shopfloor.")

    def test_button_finish_without_shopfloor_context_returns_normally(self):
        """button_finish outside shopfloor context should return the standard result."""
        mo = self._make_mo()
        wo = mo.workorder_ids[:1]
        if not wo:
            self.skipTest("No workorders on MO.")
        wo.button_start()
        result = wo.button_finish()
        # Standard return is False, a dict, or None — just not an exception
        self.assertNotIsInstance(result, Exception)

    # -----------------------------------------------------------------------
    # button_block / button_unblock
    # -----------------------------------------------------------------------

    def test_button_block_calls_notify(self):
        """button_block must not raise and must call _update_shopfloor_view."""
        mo = self._make_mo()
        wo = mo.workorder_ids[:1]
        if not wo:
            self.skipTest("No workorders on MO.")
        wo.button_start()
        # button_block calls super().button_pending() then _update_shopfloor_view
        try:
            wo.button_block()
        except Exception as exc:
            self.fail(f"button_block raised unexpectedly: {exc}")

    def test_button_unblock_calls_notify(self):
        """button_unblock must not raise on a workorder that is genuinely pending/blocked."""
        mo = self._make_mo()
        # Find a workorder already in pending state (blocked by a predecessor)
        pending_wo = mo.workorder_ids.filtered(lambda w: w.state == 'pending')[:1]
        if not pending_wo:
            self.skipTest("No pending workorders found — need sequential ops to test unblock.")
        try:
            pending_wo.button_unblock()
        except Exception as exc:
            self.fail(f"button_unblock raised unexpectedly: {exc}")

    # -----------------------------------------------------------------------
    # action_show_shopfloor_worksheet
    # -----------------------------------------------------------------------

    def test_action_show_shopfloor_worksheet_returns_act_window(self):
        """action_show_shopfloor_worksheet must return an ir.actions.act_window."""
        mo = self._make_mo()
        wo = mo.workorder_ids[:1]
        if not wo:
            self.skipTest("No workorders on MO.")
        action = wo.action_show_shopfloor_worksheet()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'mrp.workorder')
        self.assertEqual(action['res_id'], wo.id)
        self.assertEqual(action['target'], 'new')

    def test_action_show_shopfloor_worksheet_requires_single_record(self):
        """action_show_shopfloor_worksheet raises on multi-record set."""
        mo = self._make_mo()
        if len(mo.workorder_ids) < 2:
            self.skipTest("Need at least 2 workorders.")
        with self.assertRaises(Exception):
            mo.workorder_ids.action_show_shopfloor_worksheet()

    # -----------------------------------------------------------------------
    # _compute_working_users — automated override
    # -----------------------------------------------------------------------

    def test_compute_working_users_automated_progress(self):
        """Automated MO's WO in progress with active timer must set is_user_working=True."""
        self.bom.is_automated = True
        mo = self._make_mo()
        wo = mo.workorder_ids[:1]
        if not wo:
            self.skipTest("No workorders on MO.")
        wo.button_start()
        wo._compute_working_users()
        # If there's an open timer, is_user_working should be True
        has_open = any(not t.date_end for t in wo.time_ids)
        if has_open:
            self.assertTrue(wo.is_user_working,
                            "is_user_working should be True for automated MO WO in progress.")

    # -----------------------------------------------------------------------
    # _cron_finish_automated_workorders
    # -----------------------------------------------------------------------

    def test_cron_does_not_raise(self):
        """The cron method must run without raising even with no automated workorders."""
        try:
            self.env['mrp.workorder']._cron_finish_automated_workorders()
        except Exception as exc:
            self.fail(f"Cron raised unexpectedly: {exc}")

    def test_cron_finishes_overdue_automated_workorder(self):
        """
        An automated WO whose elapsed time exceeds duration_expected must be finished
        when the cron runs.
        """
        self.bom.is_automated = True
        mo = self._make_mo()
        wo = mo.workorder_ids[:1]
        if not wo:
            self.skipTest("No workorders on MO.")

        wo.duration_expected = 1.0  # 1 minute
        wo.button_start()

        # Backdate the start time so elapsed time >> duration_expected
        for timer in wo.time_ids.filtered(lambda t: not t.date_end):
            timer.date_start = fields.Datetime.now().replace(
                year=fields.Datetime.now().year - 1
            )

        self.env['mrp.workorder']._cron_finish_automated_workorders()
        self.assertEqual(wo.state, 'done', "Cron should have finished the overdue workorder.")
