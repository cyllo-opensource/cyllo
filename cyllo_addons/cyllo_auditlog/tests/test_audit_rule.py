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

from odoo.tests import tagged

from .common import AuditLogCommon


@tagged('post_install', '-at_install')
class TestAuditRule(AuditLogCommon):
    """Tests for audit rule configuration helpers."""

    def test_01_default_sequence_increments_from_existing_rule(self):
        first_rule = self._create_rule(name='Sequence Rule 1')
        second_rule = self._create_rule(name='Sequence Rule 2')

        self.assertGreater(second_rule.sequence, first_rule.sequence)
        self.assertEqual(second_rule.sequence, first_rule.sequence + 10)

    def test_02_onchange_tracking_scope_clears_incompatible_fields(self):
        rule = self._create_rule(
            tracking_scope='tracked',
            tracked_field_ids=[(6, 0, [self.partner_name_field.id])],
        )

        rule.tracking_scope = 'excluded'
        rule._onchange_tracking_scope()

        self.assertFalse(rule.tracked_field_ids)

        rule.excluded_field_ids = [(6, 0, [self.partner_email_field.id])]
        rule.tracking_scope = 'all'
        rule._onchange_tracking_scope()

        self.assertFalse(rule.tracked_field_ids)
        self.assertFalse(rule.excluded_field_ids)

    def test_03_should_track_user_respects_specific_and_excluded_users(self):
        tracked_user = self.env['res.users'].create({
            'name': 'Audit Tracked User',
            'login': 'audit_tracked_user',
            'email': 'audit_tracked_user@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        other_user = self.env['res.users'].create({
            'name': 'Audit Other User',
            'login': 'audit_other_user',
            'email': 'audit_other_user@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        specific_rule = self._create_rule(
            name='Specific User Rule',
            user_selection_type='specific',
            user_ids=[(6, 0, [tracked_user.id])],
        )
        excluded_rule = self._create_rule(
            name='Excluded User Rule',
            user_selection_type='exclude',
            user_ids=[(6, 0, [tracked_user.id])],
        )

        self.assertTrue(specific_rule._should_track_user(tracked_user))
        self.assertFalse(specific_rule._should_track_user(other_user))
        self.assertFalse(excluded_rule._should_track_user(tracked_user))
        self.assertTrue(excluded_rule._should_track_user(other_user))

    def test_04_group_user_selection_and_user_count(self):
        group = self.env['res.groups'].create({'name': 'Audit Test Group'})
        group_user = self.env['res.users'].create({
            'name': 'Audit Group User',
            'login': 'audit_group_user',
            'email': 'audit_group_user@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id, group.id])],
        })
        rule = self._create_rule(
            name='Group Rule',
            user_selection_type='group',
            group_ids=[(6, 0, [group.id])],
        )

        self.assertIn(group_user, rule._get_tracked_users())
        self.assertEqual(rule.user_count, 1)
        self.assertTrue(rule._should_track_user(group_user))

    def test_05_action_cleanup_logs_removes_only_rule_logs(self):
        rule = self._create_rule(name='Cleanup Rule')
        other_rule = self._create_rule(name='Other Cleanup Rule')
        log = self._create_log(rule, res_id=10)
        other_log = self._create_log(other_rule, res_id=11)

        action = rule.action_cleanup_logs()

        self.assertFalse(log.exists())
        self.assertTrue(other_log.exists())
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'display_notification')

    def test_06_retention_cron_removes_expired_logs(self):
        rule = self._create_rule(
            name='Retention Rule',
            has_retention=True,
            retention_days=1,
        )
        expired_log = self._create_log(rule, res_id=12)
        self.env.cr.execute(
            "UPDATE audit_log SET create_date = NOW() - INTERVAL '3 days' WHERE id = %s",
            [expired_log.id],
        )
        self.AuditRule._cron_audit_log_retention()

        self.assertFalse(expired_log.exists())


@tagged('post_install', '-at_install')
class TestAuditRuleData(AuditLogCommon):
    """Tests for XML data loaded by the audit log module."""

    def test_01_security_groups_and_cron_are_loaded(self):
        user_group = self.env.ref('cyllo_auditlog.group_cyllo_audit_log_users')
        admin_group = self.env.ref('cyllo_auditlog.group_cyllo_audit_log_admin')
        cron = self.env.ref('cyllo_auditlog.ir_cron_audit_log_retention')

        self.assertIn(user_group, admin_group.implied_ids)
        self.assertTrue(cron.active)
        self.assertEqual(cron.model_id.model, 'audit.rule')
        self.assertEqual(cron.state, 'code')
