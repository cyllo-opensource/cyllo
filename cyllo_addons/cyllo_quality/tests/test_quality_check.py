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
from odoo.tests.common import tagged

from .common import QualityCommon


@tagged('post_install', '-at_install', 'cyllo_quality')
class TestQualityCheck(QualityCommon):
    """Unit tests for quality.check."""

    # ── Sequence / creation ───────────────────────────────────────────────

    def test_create_assigns_reference(self):
        """quality.check should be assigned a QC-prefixed sequence reference."""
        qcp = self._make_qcp()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        self.assertTrue(qc.reference)
        self.assertTrue(
            qc.reference.startswith('QC'),
            "Reference should start with 'QC'.",
        )

    def test_two_checks_different_references(self):
        """Two quality checks must have distinct references."""
        qcp = self._make_qcp()
        qc1 = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        qc2 = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        self.assertNotEqual(qc1.reference, qc2.reference)

    # ── State computation ─────────────────────────────────────────────────

    def test_initial_state_todo(self):
        """A freshly created check with no checked lines must be 'todo'."""
        qcp = self._make_qcp()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        self.assertEqual(qc.state, 'todo')

    def test_state_ongoing_when_partially_checked(self):
        """State becomes 'ongoing' when some but not all lines are checked."""
        action2 = self.env['inspection.action'].create({'name': 'Step 2'})
        qcp = self._make_qcp(extra_inspections=[
            {
                'inspection_action_id': self.inspection_action.id,
                'inspection_type_id': self.inspection_type_pass_fail.id,
            },
            {
                'inspection_action_id': action2.id,
                'inspection_type_id': self.inspection_type_pass_fail.id,
            },
        ])
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        # Mark only the first line as checked/passed
        first_line = qc.quality_check_line_ids[0]
        first_line.write({'is_checked': True, 'status': 'pass'})
        self.assertEqual(qc.state, 'ongoing')

    def test_state_pass_when_all_lines_pass(self):
        """State becomes 'pass' when every line is checked and passed."""
        qcp = self._make_qcp()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        for line in qc.quality_check_line_ids:
            line.write({'is_checked': True, 'status': 'pass'})
        self.assertEqual(qc.state, 'pass')

    def test_state_fail_when_any_line_fails(self):
        """State becomes 'fail' if at least one checked line failed."""
        qcp = self._make_qcp()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        for line in qc.quality_check_line_ids:
            line.write({'is_checked': True, 'status': 'fail'})
        self.assertEqual(qc.state, 'fail')

    # ── Lines computed from QCP inspections ───────────────────────────────

    def test_lines_created_from_qcp_inspections(self):
        """quality_check_line_ids must mirror the QCP's inspection templates."""
        action2 = self.env['inspection.action'].create({'name': 'Second Step'})
        qcp = self._make_qcp(extra_inspections=[
            {
                'inspection_action_id': self.inspection_action.id,
                'inspection_type_id': self.inspection_type_pass_fail.id,
            },
            {
                'inspection_action_id': action2.id,
                'inspection_type_id': self.inspection_type_instructions.id,
            },
        ])
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        self.assertEqual(
            len(qc.quality_check_line_ids),
            len(qcp.quality_inspection_ids),
            "Number of check lines must equal number of inspection templates.",
        )

    def test_lines_reference_correct_inspection_types(self):
        """Each check line must copy its inspection_type from the template."""
        qcp = self._make_qcp(extra_inspections=[{
            'inspection_action_id': self.inspection_action.id,
            'inspection_type_id': self.inspection_type_measure.id,
            'measure_start': 0.5,
            'measure_end': 2.5,
        }])
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        line = qc.quality_check_line_ids[0]
        self.assertEqual(line.inspection_type_id, self.inspection_type_measure)

    # ── qc_alert_count ────────────────────────────────────────────────────

    def test_qc_alert_count_initial_zero(self):
        """A new quality.check should have no alerts."""
        qcp = self._make_qcp()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        self.assertEqual(qc.qc_alert_count, 0)

    def test_qc_alert_count_increments_on_alert_creation(self):
        """qc_alert_count must increase when a quality.alert is linked."""
        qcp = self._make_qcp()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        self.env['quality.alert'].create({
            'quality_check_id': qc.id,
            'date': '2025-01-01',
        })
        self.assertEqual(qc.qc_alert_count, 1)

    # ── action_view_quality_alert ─────────────────────────────────────────

    def test_action_view_quality_alert_returns_act_window(self):
        """action_view_quality_alert must return an act_window for quality.alert."""
        qcp = self._make_qcp()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        action = qc.action_view_quality_alert()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'quality.alert')

    # ── get_quality_check_actions ─────────────────────────────────────────

    def test_get_quality_check_actions_returns_list(self):
        """get_quality_check_actions() must return a non-empty list."""
        qcp = self._make_qcp()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        result = qc.get_quality_check_actions()
        self.assertIsInstance(result, list)
        self.assertTrue(result)

    def test_get_quality_check_actions_includes_lines(self):
        """Each entry in get_quality_check_actions must include check lines."""
        qcp = self._make_qcp()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        result = qc.get_quality_check_actions()
        entry = next(r for r in result if r['id'] == qc.id)
        self.assertIn('quality_check_line_ids', entry)

    # ── Archiving ─────────────────────────────────────────────────────────

    def test_archive_quality_check(self):
        """Archiving a quality.check should hide it from default searches."""
        qcp = self._make_qcp()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        qc.write({'active': False})
        found = self.env['quality.check'].search([('id', '=', qc.id)])
        self.assertFalse(found)
