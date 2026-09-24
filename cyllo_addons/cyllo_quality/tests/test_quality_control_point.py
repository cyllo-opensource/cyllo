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
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from .common import QualityCommon


@tagged('post_install', '-at_install', 'cyllo_quality')
class TestQualityControlPoint(QualityCommon):
    """Unit tests for quality.control.point."""

    # ── Sequence / creation ───────────────────────────────────────────────

    def test_create_assigns_sequence_name(self):
        """A new QCP should receive an auto-generated sequence reference."""
        qcp = self._make_qcp()
        self.assertTrue(qcp.name, "QCP name must not be empty after creation.")
        self.assertTrue(
            qcp.name.startswith('QCP'),
            "QCP name should start with the 'QCP' prefix.",
        )

    def test_create_two_qcps_have_different_names(self):
        """Each QCP must receive a unique sequence name."""
        qcp1 = self._make_qcp()
        qcp2 = self._make_qcp()
        self.assertNotEqual(qcp1.name, qcp2.name)

    # ── Constraint: at least one inspection line ──────────────────────────

    def test_create_without_inspection_raises(self):
        """Creating a QCP with no inspection lines must raise ValidationError."""
        with self.assertRaises(ValidationError):
            self.env['quality.control.point'].create({
                'operation_type_ids': [self.picking_type_in.id],
                'control_type': 'operation',
                'control_by': 'all',
                # deliberately omitting quality_inspection_ids
            })

    def test_remove_all_inspection_lines_raises(self):
        """Removing the last inspection line from an existing QCP must raise."""
        qcp = self._make_qcp()
        with self.assertRaises(ValidationError):
            qcp.write({'quality_inspection_ids': [(5, 0, 0)]})

    # ── Compute: responsible user from team leader ────────────────────────

    def test_user_id_computed_from_team_leader(self):
        """user_id should mirror the team leader's linked res.user."""
        # Create an employee with a linked user
        user = self.env['res.users'].create({
            'name': 'Team Lead User',
            'login': 'teamlead_qcp_test@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        employee = self.env['hr.employee'].create({
            'name': 'Team Lead Employee',
            'user_id': user.id,
        })
        team = self.env['quality.team'].create({
            'name': 'Lead Team',
            'leader_id': employee.id,
            'is_mail': False,
        })
        qcp = self._make_qcp(quality_team_id=team.id)
        self.assertEqual(
            qcp.user_id, user,
            "user_id should be set from the quality team's leader user.",
        )

    # ── Compute: qc_check_count ───────────────────────────────────────────

    def test_qc_check_count_initial_zero(self):
        """A brand-new QCP should have zero linked quality checks."""
        qcp = self._make_qcp()
        self.assertEqual(qcp.qc_check_count, 0)

    def test_qc_check_count_increments(self):
        """qc_check_count must increase when a quality.check is created."""
        qcp = self._make_qcp()
        self.env['quality.check'].create({
            'quality_control_id': qcp.id,
            'control_type': 'operation',
        })
        self.assertEqual(qcp.qc_check_count, 1)

    # ── action_view_quality_checks ────────────────────────────────────────

    def test_action_view_quality_checks_returns_act_window(self):
        """action_view_quality_checks must return an ir.actions.act_window."""
        qcp = self._make_qcp()
        action = qcp.action_view_quality_checks()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'quality.check')

    # ── Fields: product / category scoping ───────────────────────────────

    def test_create_qcp_for_product(self):
        """QCP scoped to specific products should store them correctly."""
        qcp = self._make_qcp(
            qc_check_for='product',
            product_ids=[(6, 0, [self.product.id])],
        )
        self.assertIn(self.product, qcp.product_ids)

    def test_create_qcp_for_category(self):
        """QCP scoped to a product category should store it correctly."""
        qcp = self._make_qcp(
            qc_check_for='category',
            product_category_ids=[(6, 0, [self.product_category.id])],
        )
        self.assertIn(self.product_category, qcp.product_category_ids)

    # ── control_by: periodically ──────────────────────────────────────────

    def test_create_qcp_periodically(self):
        """A QCP with control_by='periodically' should save frequency/period."""
        qcp = self._make_qcp(
            control_by='periodically',
            control_frequency=7,
            control_period='day',
        )
        self.assertEqual(qcp.control_by, 'periodically')
        self.assertEqual(qcp.control_frequency, 7)
        self.assertEqual(qcp.control_period, 'day')

    # ── Archiving ─────────────────────────────────────────────────────────

    def test_archive_qcp(self):
        """Toggling active=False should archive the QCP."""
        qcp = self._make_qcp()
        qcp.write({'active': False})
        self.assertFalse(qcp.active)
        # Archived QCPs must not appear in a default search
        result = self.env['quality.control.point'].search(
            [('id', '=', qcp.id)]
        )
        self.assertFalse(result, "Archived QCP should not appear in default search.")

    # ── Failure location ──────────────────────────────────────────────────

    def test_failure_location_stored(self):
        """failure_location_id should be persisted."""
        qcp = self._make_qcp(failure_location_id=self.failure_location.id)
        self.assertEqual(qcp.failure_location_id, self.failure_location)

    # ── Multi-inspection QCP ──────────────────────────────────────────────

    def test_multiple_inspection_lines_stored(self):
        """A QCP with two inspection steps should keep both."""
        action2 = self.env['inspection.action'].create({'name': 'Dimension Check'})
        qcp = self._make_qcp(extra_inspections=[
            {
                'inspection_action_id': self.inspection_action.id,
                'inspection_type_id': self.inspection_type_pass_fail.id,
            },
            {
                'inspection_action_id': action2.id,
                'inspection_type_id': self.inspection_type_measure.id,
                'measure_start': 1.0,
                'measure_end': 5.0,
            },
        ])
        self.assertEqual(len(qcp.quality_inspection_ids), 2)
