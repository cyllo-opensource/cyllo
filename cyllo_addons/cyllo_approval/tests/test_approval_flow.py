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
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestApprovalFlow(TransactionCase):

    def setUp(self):
        super().setUp()
        self.ApprovalRule = self.env['approval.rule']
        self.ApprovalRequest = self.env['approval.request']
        self.IrButtons = self.env['ir.buttons']
        self.User = self.env['res.users']
        self.groups = [
            self.env.ref('base.group_user').id,
            self.env.ref('cyllo_approval.group_approval_user').id,
            self.env.ref('base.group_partner_manager').id,
            self.env.ref('base.group_erp_manager').id,
        ]
        self.test_user = self.User.create({
            'name': 'Test Approver',
            'login': 'test_approver_flow',
            'email': 'approver_flow@example.com',
            'active': True,
            'groups_id': [(6, 0, self.groups)],
        })
        self.second_user = self.User.create({
            'name': 'Second Approver',
            'login': 'test_approver_flow_2',
            'email': 'approver_flow_2@example.com',
            'active': True,
            'groups_id': [(6, 0, self.groups)],
        })
        self.model_res_partner = self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)
        self.model_res_users = self.env['ir.model'].search([('model', '=', 'res.users')], limit=1)
        self.button_toggle_active = self.IrButtons.create({
            'name': 'toggle_active',
            'string': 'Archive',
            'model_id': self.model_res_partner.id,
        })
        self.button_reset_password = self.IrButtons.create({
            'name': 'action_reset_password',
            'string': 'Reset Password',
            'model_id': self.model_res_users.id,
        })
        self.rule_partner = self.ApprovalRule.create({
            'name': 'Toggle Active Rule',
            'model_id': self.model_res_partner.id,
            'rule_type': 'button',
            'button_id': self.button_toggle_active.id,
            'approval_line_ids': [
                (0, 0, {'sequence': 10, 'name': 'First',
                        'user_id': self.test_user.id}),
                (0, 0, {'sequence': 20, 'name': 'Second',
                        'user_id': self.second_user.id}),
            ],
        })
        self.rule_users = self.ApprovalRule.create({
            'name': 'Reset Password Rule',
            'model_id': self.model_res_users.id,
            'rule_type': 'button',
            'button_id': self.button_reset_password.id,
            'user_id': self.test_user.id,
        })
        # Rebuilding the registry drops the button patches: re-apply them the
        # same way the server does at start up.
        self.env.registry.setup_models(self.env.cr)
        self.env['approval.rule']._register_hook()
        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner Flow',
            'active': True,
        })

    def _request_approval(self, action):
        """Run the wizard the intercepted button returned."""
        context = action['context']
        wizard = self.env['approval.request.wizard'].create({
            'rule_id': context['default_rule_id'],
            'line_id': context.get('default_line_id'),
            'res_model': context['default_res_model'],
            'res_id': context['default_res_id'],
        })
        wizard.action_request_approval()
        return self.ApprovalRequest.search([
            ('rule_id', '=', context['default_rule_id']),
            ('res_model', '=', context['default_res_model']),
            ('res_id', '=', context['default_res_id']),
        ], order='id desc', limit=1)

    def test_01_legacy_rule_gets_a_single_level(self):
        """A rule created with a plain approver still has one level."""
        self.assertEqual(len(self.rule_users.approval_line_ids), 1)
        self.assertEqual(self.rule_users.approval_line_ids.user_id,
                         self.test_user)
        self.assertEqual(self.rule_users.level_count, 1)

    def test_02_multi_level_button_flow(self):
        """Each level is asked in turn and the button replays itself."""
        action = self.partner.toggle_active()
        self.assertEqual(action.get('res_model'), 'approval.request.wizard')
        self.assertEqual(action['context']['default_line_id'],
                         self.rule_partner.approval_line_ids[0].id)

        first_request = self._request_approval(action)
        self.assertEqual(first_request.approver_id, self.test_user)
        self.assertEqual(first_request.level, 1)
        self.assertEqual(first_request.level_total, 2)
        self.assertTrue(self.partner.active,
                        "the record must not change while approvals run")

        # A second click while a level is pending is refused.
        with self.assertRaises(ValidationError):
            self.partner.toggle_active()

        first_request.with_user(self.test_user).action_approve()
        second_request = self.ApprovalRequest.search([
            ('rule_id', '=', self.rule_partner.id),
            ('res_id', '=', self.partner.id),
            ('state', '=', 'pending'),
        ])
        self.assertEqual(len(second_request), 1,
                         "approving level 1 must ask level 2 automatically")
        self.assertEqual(second_request.approver_id, self.second_user)
        self.assertEqual(second_request.level, 2)
        self.assertTrue(self.partner.active)

        second_request.with_user(self.second_user).action_approve()
        self.partner.invalidate_recordset()
        self.assertFalse(self.partner.active,
                         "the last approval must replay the button itself")

    def test_03_rejection_restarts_the_chain(self):
        """A rejection closes the cycle: the first level is asked again."""
        action = self.partner.toggle_active()
        first_request = self._request_approval(action)
        first_request.with_user(self.test_user).action_reject()
        self.partner.invalidate_recordset()
        self.assertTrue(self.partner.active)

        action = self.partner.toggle_active()
        self.assertEqual(action.get('res_model'), 'approval.request.wizard')
        self.assertEqual(action['context']['default_line_id'],
                         self.rule_partner.approval_line_ids[0].id)

    def test_04_manual_flow_without_auto_execute(self):
        """Without auto execution the requester triggers the action again."""
        self.rule_partner.auto_execute = False
        action = self.partner.toggle_active()
        request = self._request_approval(action)
        request.with_user(self.test_user).action_approve()
        request = self.ApprovalRequest.search([
            ('rule_id', '=', self.rule_partner.id),
            ('res_id', '=', self.partner.id),
            ('state', '=', 'pending'),
        ])
        request.with_user(self.second_user).action_approve()
        self.partner.invalidate_recordset()
        self.assertTrue(self.partner.active)
        self.partner.toggle_active()
        self.assertFalse(self.partner.active)

    def test_05_only_the_level_approver_may_answer(self):
        """The approver of another level cannot answer the running one."""
        action = self.partner.toggle_active()
        request = self._request_approval(action)
        with self.assertRaises(ValidationError):
            request.with_user(self.second_user).action_approve()

    def test_06_single_level_button_flow(self):
        """A one level rule behaves like the legacy single approver flow."""
        action_user = self.test_user.action_reset_password()
        self.assertEqual(action_user.get('res_model'),
                         'approval.request.wizard')
        request = self._request_approval(action_user)
        self.assertEqual(request.level_total, 1)
        request.with_user(self.test_user).action_approve()
        res = self.test_user.with_user(self.test_user).action_reset_password()
        if isinstance(res, dict):
            self.assertNotEqual(res.get('res_model'),
                                'approval.request.wizard')

    def test_07_multi_level_state_flow(self):
        """A state change waits for every level, then applies itself."""
        field = self.env['ir.model.fields'].search([
            ('model', '=', 'mail.mail'), ('name', '=', 'state')], limit=1)
        value = self.env['ir.model.fields.selection'].search([
            ('field_id', '=', field.id), ('value', '=', 'cancel')], limit=1)
        rule = self.ApprovalRule.create({
            'name': 'Mail Cancel Rule',
            'model_id': self.env['ir.model']._get_id('mail.mail'),
            'rule_type': 'state',
            'state_field_id': field.id,
            'state_to_selection_id': value.id,
            'approval_line_ids': [
                (0, 0, {'sequence': 10, 'user_id': self.test_user.id}),
                (0, 0, {'sequence': 20, 'user_id': self.second_user.id}),
            ],
        })
        self.env.registry.setup_models(self.env.cr)
        self.env['approval.rule']._register_hook()

        mail = self.env['mail.mail'].create({'subject': 'Approval state test'})
        mail.write({'state': 'cancel'})
        self.assertNotEqual(mail.state, 'cancel',
                            "the state must wait for the approvals")
        self.assertTrue(mail.x_is_state_approval)

        action = mail.action_request_approval()
        self.assertEqual(action.get('res_model'), 'approval.request.wizard')
        first_request = self._request_approval(action)
        self.assertEqual(first_request.approver_id, self.test_user)
        first_request.with_user(self.test_user).action_approve()

        second_request = self.ApprovalRequest.search([
            ('rule_id', '=', rule.id),
            ('res_id', '=', mail.id),
            ('state', '=', 'pending'),
        ])
        self.assertEqual(second_request.approver_id, self.second_user)
        second_request.with_user(self.second_user).action_approve()

        mail.invalidate_recordset()
        self.assertEqual(mail.state, 'cancel',
                         "the last approval must apply the state itself")

    def test_08_level_keeps_its_own_approver(self):
        """A level never inherits the approver of level one."""
        group = self.env['res.groups'].create({
            'name': 'Level Two Approvers',
            'users': [(6, 0, [self.second_user.id])],
        })
        self.rule_partner.approval_line_ids[1].write({
            'user_id': False,
            'group_id': group.id,
        })
        action = self.partner.toggle_active()
        first_request = self._request_approval(action)
        first_request.with_user(self.test_user).action_approve()

        second_request = self.ApprovalRequest.search([
            ('rule_id', '=', self.rule_partner.id),
            ('res_id', '=', self.partner.id),
            ('state', '=', 'pending'),
        ])
        self.assertFalse(
            second_request.approver_id,
            "a group level must not fall back on the approver of level one")
        self.assertEqual(second_request.approver_group_id, group)
        self.assertFalse(second_request.with_user(self.test_user).can_approve)
        with self.assertRaises(ValidationError):
            second_request.with_user(self.test_user).action_approve()

        second_request.with_user(self.second_user).action_approve()
        self.partner.invalidate_recordset()
        self.assertFalse(self.partner.active)
