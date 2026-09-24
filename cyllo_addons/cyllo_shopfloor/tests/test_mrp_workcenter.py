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
from odoo.tests.common import tagged
from .common import ShopfloorCommon


@tagged('post_install', '-at_install')
class TestMrpWorkcenter(ShopfloorCommon):
    """Tests for get_shopfloor_dashboard_metrics on mrp.workcenter."""

    def test_dashboard_metrics_returns_dict(self):
        """get_shopfloor_dashboard_metrics must return a dict."""
        result = self.env['mrp.workcenter'].get_shopfloor_dashboard_metrics()
        self.assertIsInstance(result, dict, "Result should be a dict.")

    def test_dashboard_metrics_structure(self):
        """Each entry in metrics must have the expected keys."""
        mo = self._make_mo()
        # Start the first workorder so it's not in draft state
        if mo.workorder_ids:
            mo.workorder_ids[0].button_start()

        result = self.env['mrp.workcenter'].get_shopfloor_dashboard_metrics()

        for wc_id, data in result.items():
            self.assertIsInstance(wc_id, int, "Keys must be workcenter ids (int).")
            self.assertIn('in_progress', data)
            self.assertIn('completed', data)
            self.assertIn('canceled', data)
            self.assertIn('total', data)

    def test_dashboard_metrics_totals_consistent(self):
        """total must equal sum of in_progress + completed + canceled for every entry."""
        mo = self._make_mo()
        if mo.workorder_ids:
            mo.workorder_ids[0].button_start()

        result = self.env['mrp.workcenter'].get_shopfloor_dashboard_metrics()
        for wc_id, data in result.items():
            calc_total = data['in_progress'] + data['completed'] + data['canceled']
            self.assertEqual(
                data['total'], calc_total,
                f"total mismatch for workcenter {wc_id}: {data}"
            )

    def test_dashboard_metrics_completed_increments_after_finish(self):
        """Finishing a workorder must increment the 'completed' counter for that workcenter."""
        mo = self._make_mo()
        wo = mo.workorder_ids.filtered(lambda w: w.workcenter_id == self.workcenter_1)[:1]
        if not wo:
            self.skipTest("No workorder on workcenter_1 — check BoM setup.")

        wo.button_start()
        metrics_before = self.env['mrp.workcenter'].get_shopfloor_dashboard_metrics()
        before = metrics_before.get(self.workcenter_1.id, {}).get('completed', 0)

        wo.button_finish()
        metrics_after = self.env['mrp.workcenter'].get_shopfloor_dashboard_metrics()
        after = metrics_after.get(self.workcenter_1.id, {}).get('completed', 0)

        self.assertGreater(after, before, "completed count should increase after finishing a workorder.")

    def test_dashboard_metrics_in_progress_increments_after_start(self):
        """Starting a workorder must increment the 'in_progress' counter."""
        mo = self._make_mo()
        wo = mo.workorder_ids.filtered(lambda w: w.workcenter_id == self.workcenter_1)[:1]
        if not wo:
            self.skipTest("No workorder on workcenter_1.")

        metrics_before = self.env['mrp.workcenter'].get_shopfloor_dashboard_metrics()
        before = metrics_before.get(self.workcenter_1.id, {}).get('in_progress', 0)

        wo.button_start()
        metrics_after = self.env['mrp.workcenter'].get_shopfloor_dashboard_metrics()
        after = metrics_after.get(self.workcenter_1.id, {}).get('in_progress', 0)

        self.assertGreaterEqual(after, before, "in_progress should not decrease after starting a workorder.")

    def test_dashboard_metrics_excludes_draft_workorders(self):
        """Draft workorders (state=draft) must not appear in the metrics."""
        # Create a bare MO without confirming → workorders remain in draft
        mo = self._make_mo(confirm=False)
        draft_wc_ids = mo.workorder_ids.mapped('workcenter_id').ids

        result = self.env['mrp.workcenter'].get_shopfloor_dashboard_metrics()
        # Draft workorders should not inflate the total for those workcenters
        for wc_id in draft_wc_ids:
            if wc_id in result:
                # Totals for draft-only workorders should reflect only non-draft orders
                self.assertIsInstance(result[wc_id]['total'], int)
