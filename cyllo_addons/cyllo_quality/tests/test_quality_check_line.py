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
from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import QualityCommon


@tagged('post_install', '-at_install', 'cyllo_quality')
class TestQualityCheckLine(QualityCommon):
    """Unit tests for quality.check.line.validate_quality_actions()."""

    # ── Helpers ───────────────────────────────────────────────────────────

    def _make_check_with_line(self, inspection_type, extra_insp_vals=None):
        """Return a (quality.check, quality.check.line) pair."""
        insp_vals = {
            'inspection_action_id': self.inspection_action.id,
            'inspection_type_id': inspection_type.id,
        }
        if extra_insp_vals:
            insp_vals.update(extra_insp_vals)
        qcp = self._make_qcp(extra_inspections=[insp_vals])
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        line = qc.quality_check_line_ids[0]
        return qc, line

    # ── Pass/Fail ──────────────────────────────────────────────────────────

    def test_pass_fail_pass_value(self):
        """Pass/Fail line: value='pass' → status 'pass', is_checked=True."""
        _, line = self._make_check_with_line(self.inspection_type_pass_fail)
        result = line.validate_quality_actions('pass', 'ok')
        self.assertEqual(result, 'pass')
        self.assertTrue(line.is_checked)
        self.assertEqual(line.status, 'pass')
        self.assertEqual(line.note, 'ok')

    def test_pass_fail_fail_value(self):
        """Pass/Fail line: value='fail' → status 'fail', is_checked=True."""
        _, line = self._make_check_with_line(self.inspection_type_pass_fail)
        result = line.validate_quality_actions('fail', '')
        self.assertEqual(result, 'fail')
        self.assertTrue(line.is_checked)
        self.assertEqual(line.status, 'fail')

    # ── Measure ───────────────────────────────────────────────────────────

    def test_measure_within_range_passes(self):
        """Measure line: numeric value within [start, end] → 'pass'."""
        _, line = self._make_check_with_line(
            self.inspection_type_measure,
            extra_insp_vals={'measure_start': 1.0, 'measure_end': 10.0, 'unit_id': self.uom_unit.id},
        )
        result = line.validate_quality_actions('5.0', 'in range')
        self.assertEqual(result, 'pass')
        self.assertEqual(line.value, '5.0')

    def test_measure_below_range_fails(self):
        """Measure line: value below start → 'fail'."""
        _, line = self._make_check_with_line(
            self.inspection_type_measure,
            extra_insp_vals={'measure_start': 5.0, 'measure_end': 10.0, 'unit_id': self.uom_unit.id},
        )
        result = line.validate_quality_actions('1.0', '')
        self.assertEqual(result, 'fail')

    def test_measure_above_range_fails(self):
        """Measure line: value above end → 'fail'."""
        _, line = self._make_check_with_line(
            self.inspection_type_measure,
            extra_insp_vals={'measure_start': 1.0, 'measure_end': 5.0, 'unit_id': self.uom_unit.id},
        )
        result = line.validate_quality_actions('99.9', '')
        self.assertEqual(result, 'fail')

    def test_measure_exact_boundary_passes(self):
        """Measure line: value exactly equal to start or end → 'pass'."""
        _, line = self._make_check_with_line(
            self.inspection_type_measure,
            extra_insp_vals={'measure_start': 3.0, 'measure_end': 7.0, 'unit_id': self.uom_unit.id},
        )
        result = line.validate_quality_actions('3.0', '')
        self.assertEqual(result, 'pass')

    def test_measure_non_numeric_value_fails(self):
        """Measure line: non-numeric value → 'fail' (handled gracefully)."""
        _, line = self._make_check_with_line(
            self.inspection_type_measure,
            extra_insp_vals={'measure_start': 1.0, 'measure_end': 5.0, 'unit_id': self.uom_unit.id},
        )
        result = line.validate_quality_actions('not_a_number', '')
        self.assertEqual(result, 'fail')

    def test_measure_stores_unit_value_json(self):
        """Measure line: unit_value JSON must record the unit and value."""
        _, line = self._make_check_with_line(
            self.inspection_type_measure,
            extra_insp_vals={'measure_start': 0.0, 'measure_end': 100.0, 'unit_id': self.uom_unit.id},
        )
        line.validate_quality_actions('42.5', '')
        self.assertIsInstance(line.unit_value, dict)
        self.assertEqual(line.unit_value.get('value'), '42.5')

    # ── Instructions ──────────────────────────────────────────────────────

    def test_instructions_pass_value(self):
        """Instructions line: value='pass' → status 'pass'."""
        _, line = self._make_check_with_line(self.inspection_type_instructions)
        result = line.validate_quality_actions('pass', 'acknowledged')
        self.assertEqual(result, 'pass')

    def test_instructions_fail_value(self):
        """Instructions line: any value other than 'pass' → 'fail'."""
        _, line = self._make_check_with_line(self.inspection_type_instructions)
        result = line.validate_quality_actions('skip', '')
        self.assertEqual(result, 'fail')

    # ── Take a picture ────────────────────────────────────────────────────

    def test_picture_with_pipe_separator(self):
        """Take-a-picture: 'pass|<imagedata>' should split correctly."""
        _, line = self._make_check_with_line(self.inspection_type_picture)
        result = line.validate_quality_actions('pass|base64imagedata', '')
        self.assertEqual(result, 'pass')
        self.assertEqual(line.value, 'base64imagedata')

    def test_picture_fail_with_pipe_separator(self):
        """Take-a-picture: 'fail|<imagedata>' should be marked failed."""
        _, line = self._make_check_with_line(self.inspection_type_picture)
        result = line.validate_quality_actions('fail|imgdata', '')
        self.assertEqual(result, 'fail')

    def test_picture_without_pipe(self):
        """Take-a-picture: value without pipe sets both status and value."""
        _, line = self._make_check_with_line(self.inspection_type_picture)
        line.validate_quality_actions('pass', '')
        self.assertEqual(line.value, 'pass')

    # ── Blocking logic ────────────────────────────────────────────────────

    def test_blocked_line_raises_when_predecessor_not_done(self):
        """A line with blocked_by_id must raise UserError if predecessor incomplete."""
        action2 = self.env['inspection.action'].create({'name': 'Step B'})
        qcp = self._make_qcp(extra_inspections=[
            {
                'inspection_action_id': self.inspection_action.id,
                'inspection_type_id': self.inspection_type_pass_fail.id,
                'priority': 1,
            },
            {
                'inspection_action_id': action2.id,
                'inspection_type_id': self.inspection_type_pass_fail.id,
                'priority': 2,
            },
        ])
        # Manually set the blocked_by relationship after creation
        step_a = qcp.quality_inspection_ids.filtered(lambda l: l.priority == 1)
        step_b = qcp.quality_inspection_ids.filtered(lambda l: l.priority == 2)
        step_b.write({'blocked_by_id': step_a.id})

        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        line_b = qc.quality_check_line_ids.filtered(
            lambda l: l.inspection_action_id == action2
        )
        with self.assertRaises(UserError):
            line_b.validate_quality_actions('pass', '')

    def test_blocked_line_succeeds_when_predecessor_done(self):
        """A blocked line can proceed once its predecessor is completed."""
        action2 = self.env['inspection.action'].create({'name': 'Gated Step'})
        qcp = self._make_qcp(extra_inspections=[
            {
                'inspection_action_id': self.inspection_action.id,
                'inspection_type_id': self.inspection_type_pass_fail.id,
                'priority': 1,
            },
            {
                'inspection_action_id': action2.id,
                'inspection_type_id': self.inspection_type_pass_fail.id,
                'priority': 2,
            },
        ])
        step_a = qcp.quality_inspection_ids.filtered(lambda l: l.priority == 1)
        step_b = qcp.quality_inspection_ids.filtered(lambda l: l.priority == 2)
        step_b.write({'blocked_by_id': step_a.id})

        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        line_a = qc.quality_check_line_ids.filtered(
            lambda l: l.inspection_action_id == self.inspection_action
        )
        line_b = qc.quality_check_line_ids.filtered(
            lambda l: l.inspection_action_id == action2
        )
        # Complete the predecessor first
        line_a.validate_quality_actions('pass', '')
        # Now line_b should be allowed
        result = line_b.validate_quality_actions('pass', '')
        self.assertEqual(result, 'pass')

    # ── action_check_qc ───────────────────────────────────────────────────

    def test_action_check_qc_returns_client_action(self):
        """action_check_qc should return a client action tag."""
        _, line = self._make_check_with_line(self.inspection_type_pass_fail)
        action = line.action_check_qc()
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'validate_quality_action')

    # ── action_create_alert ───────────────────────────────────────────────

    def test_action_create_alert_returns_act_window(self):
        """action_create_alert should open the alert.warning wizard form."""
        _, line = self._make_check_with_line(self.inspection_type_pass_fail)
        action = line.action_create_alert()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'alert.warning')
        self.assertEqual(action['target'], 'new')
