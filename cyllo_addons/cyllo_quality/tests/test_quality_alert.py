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
class TestQualityAlert(QualityCommon):
    """Unit tests for quality.alert."""

    def _make_alert(self, **kwargs):
        vals = {'date': '2025-06-01'}
        vals.update(kwargs)
        return self.env['quality.alert'].create(vals)

    # ── Sequence ──────────────────────────────────────────────────────────

    def test_create_assigns_qa_reference(self):
        """A new quality.alert must receive a QA-prefixed sequence name."""
        alert = self._make_alert()
        self.assertTrue(alert.name)
        self.assertTrue(
            alert.name.startswith('QA'),
            "Alert name must start with 'QA'.",
        )

    def test_two_alerts_have_different_names(self):
        alert1 = self._make_alert()
        alert2 = self._make_alert()
        self.assertNotEqual(alert1.name, alert2.name)

    # ── Default stage ─────────────────────────────────────────────────────

    def test_default_stage_is_quarantine(self):
        """A new alert should start in the Quarantine stage."""
        alert = self._make_alert()
        self.assertEqual(alert.stage_id, self.alert_stage_quarantine)

    def test_stage_can_be_changed(self):
        """An alert's stage should be updatable."""
        new_stage = self.env['quality.alert.stage'].create({'name': 'In Review'})
        alert = self._make_alert()
        alert.write({'stage_id': new_stage.id})
        self.assertEqual(alert.stage_id, new_stage)

    # ── Priority ─────────────────────────────────────────────────────────

    def test_priority_field_stores_value(self):
        """Priority '3' (High) should persist on the alert."""
        alert = self._make_alert(priority='3')
        self.assertEqual(alert.priority, '3')

    # ── Linked check and check line ────────────────────────────────────────

    def test_alert_linked_to_quality_check(self):
        """An alert created from a check should back-reference the check."""
        qcp = self._make_qcp()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        alert = self._make_alert(quality_check_id=qc.id)
        self.assertEqual(alert.quality_check_id, qc)

    def test_alert_company_defaults_to_current(self):
        """company_id should default to the current company."""
        alert = self._make_alert()
        self.assertEqual(alert.company_id, self.env.company)

    # ── alert.warning wizard ───────────────────────────────────────────────

    def test_alert_warning_wizard_creates_alert(self):
        """action_create_alert on alert.warning must create a quality.alert."""
        qcp = self._make_qcp()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        line = qc.quality_check_line_ids[0]

        wizard = self.env['alert.warning'].create({
            'quality_check_id': qc.id,
            'quality_check_line_id': line.id,
        })
        before = self.env['quality.alert'].search_count([('quality_check_id', '=', qc.id)])
        wizard.action_create_alert()
        after = self.env['quality.alert'].search_count([('quality_check_id', '=', qc.id)])
        self.assertEqual(after, before + 1, "One new alert should be created.")

    def test_alert_warning_sets_line_is_alert(self):
        """action_create_alert must flip is_alert=True on the check line."""
        qcp = self._make_qcp()
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        line = qc.quality_check_line_ids[0]
        self.assertFalse(line.is_alert)

        wizard = self.env['alert.warning'].create({
            'quality_check_id': qc.id,
            'quality_check_line_id': line.id,
        })
        wizard.action_create_alert()
        self.assertTrue(line.is_alert)

    def test_alert_warning_inherits_failure_location(self):
        """alert.warning.failure_location_id should reflect the QCP setting."""
        qcp = self._make_qcp(failure_location_id=self.failure_location.id)
        qc = self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        line = qc.quality_check_line_ids[0]
        wizard = self.env['alert.warning'].create({
            'quality_check_id': qc.id,
            'quality_check_line_id': line.id,
        })
        self.assertEqual(wizard.failure_location_id, self.failure_location)


@tagged('post_install', '-at_install', 'cyllo_quality')
class TestQualityTeam(QualityCommon):
    """Unit tests for quality.team."""

    # ── Basic creation ────────────────────────────────────────────────────

    def test_create_quality_team(self):
        """A quality.team should be creatable with a name."""
        team = self.env['quality.team'].create({'name': 'Alpha Team'})
        self.assertTrue(team.id)
        self.assertEqual(team.name, 'Alpha Team')

    # ── member_ids auto-computed from leader ──────────────────────────────

    def test_leader_auto_added_to_members(self):
        """Setting a leader should automatically include them in member_ids."""
        team = self.env['quality.team'].create({
            'name': 'Beta Team',
            'leader_id': self.employee.id,
        })
        self.assertIn(self.employee, team.member_ids)

    def test_clearing_leader_clears_members(self):
        """Removing the leader should clear the computed member list."""
        team = self.env['quality.team'].create({
            'name': 'Gamma Team',
            'leader_id': self.employee.id,
        })
        team.write({'leader_id': False})
        self.assertFalse(team.member_ids)

    # ── is_mail flag ──────────────────────────────────────────────────────

    def test_is_mail_default_true(self):
        """is_mail defaults to True on a new quality.team."""
        team = self.env['quality.team'].create({'name': 'Delta Team'})
        self.assertTrue(team.is_mail)

    def test_is_mail_can_be_set_false(self):
        """is_mail can be explicitly set to False."""
        team = self.env['quality.team'].create({
            'name': 'Epsilon Team',
            'is_mail': False,
        })
        self.assertFalse(team.is_mail)

    # ── company_id ────────────────────────────────────────────────────────

    def test_company_defaults_to_current(self):
        """company_id should default to the current company."""
        team = self.env['quality.team'].create({'name': 'Zeta Team'})
        self.assertEqual(team.company_id, self.env.company)
