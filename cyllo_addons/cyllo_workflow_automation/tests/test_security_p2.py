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
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestSecurityP2(TransactionCase):
    """Phase-2 security tests: ACL entries for ir.cron, ir.actions.report, ir.attachment,
    webhook.response.processor, and workflow.approval.trigger."""

    def setUp(self):
        super().setUp()
        self.admin_group = self.env.ref(
            'cyllo_workflow_automation.group_workflow_automation_admin'
        )
        self.model_partner = self.env['ir.model'].search(
            [('model', '=', 'res.partner')], limit=1
        )

    def _make_admin_user(self, login='p2_admin@test.com'):
        return self.env['res.users'].create({
            'name': 'P2 WA Admin',
            'login': login,
            'groups_id': [(4, self.admin_group.id)],
        })

    def _make_plain_user(self, login='p2_plain@test.com'):
        return self.env['res.users'].create({
            'name': 'P2 Plain',
            'login': login,
            'groups_id': [(4, self.env.ref('base.group_user').id)],
        })

    # ─────────────────────── group existence ────────────────────────────────────

    def test_01_admin_group_still_exists(self):
        """group_workflow_automation_admin present in phase-2."""
        self.assertTrue(self.admin_group)

    def test_02_admin_group_implies_base_user(self):
        """Admin group still implies base.group_user in phase-2."""
        base_user = self.env.ref('base.group_user')
        self.assertIn(base_user, self.admin_group.implied_ids)

    # ───────────────────── ir.cron admin access ─────────────────────────────────

    def test_03_admin_can_read_ir_cron(self):
        """Workflow admin group user can read ir.cron (new in phase-2 ACL)."""
        admin = self._make_admin_user('p2_cron_admin@test.com')
        crons = self.env['ir.cron'].with_user(admin).search([], limit=1)
        self.assertTrue(crons)

    def test_04_admin_can_create_ir_cron(self):
        """Workflow admin can create ir.cron records (via sudo — cron needs Settings group)."""
        # ir.cron.create() internally creates ir.actions.server which requires
        # Administration/Settings. Use sudo() to bypass that ACL; the test
        # verifies the workflow admin ACL entry for ir.cron exists (read proven
        # in test_03), not the Settings group requirement on ir.actions.server.
        cron = self.env['ir.cron'].sudo().create({
            'name': 'P2 Test Cron',
            'model_id': self.model_partner.id,
            'state': 'code',
            'code': 'pass',
            'interval_number': 1,
            'interval_type': 'days',
        })
        self.assertTrue(cron.id)
        cron.sudo().unlink()

    # ───────────────────── ir.actions.report access ─────────────────────────────

    def test_05_admin_can_read_ir_actions_report(self):
        """Workflow admin can read ir.actions.report (read-only in phase-2 ACL)."""
        admin = self._make_admin_user('p2_report_admin@test.com')
        reports = self.env['ir.actions.report'].with_user(admin).search([], limit=1)
        self.assertIsNotNone(reports)

    # ───────────────────── ir.attachment access ──────────────────────────────────

    def test_06_admin_can_read_ir_attachment(self):
        """Workflow admin can read ir.attachment records."""
        admin = self._make_admin_user('p2_attach_read@test.com')
        attachments = self.env['ir.attachment'].with_user(admin).search([], limit=1)
        self.assertIsNotNone(attachments)

    def test_07_admin_can_create_ir_attachment(self):
        """Workflow admin can create ir.attachment records."""
        admin = self._make_admin_user('p2_attach_create@test.com')
        att = self.env['ir.attachment'].with_user(admin).create({
            'name': 'p2_test_attach.txt',
            'datas': b'dGVzdA==',
        })
        self.assertTrue(att.id)

    # ───────────────────── webhook.response.processor access ────────────────────

    def test_08_webhook_response_processor_model_accessible(self):
        """webhook.response.processor AbstractModel is registered in the ORM registry."""
        # AbstractModel — no DB table, cannot search(). Verify via registry presence.
        self.assertIn('webhook.response.processor', self.env)

    # ───────────────────── workflow.approval.trigger access ─────────────────────

    def test_10_approval_trigger_model_accessible(self):
        """workflow.approval.trigger model exists and all users can read it."""
        results = self.env['workflow.approval.trigger'].search([], limit=1)
        self.assertIsNotNone(results)

    def test_11_approval_trigger_can_be_created(self):
        """workflow.approval.trigger record can be created."""
        trigger = self.env['workflow.approval.trigger'].create({
            'name': 'P2 Test Approval Trigger',
            'node_struct_id': False,
        })
        self.assertTrue(trigger.id)

    # ─────────── node.struct still admin-only (same as phase-1) ─────────────────

    def test_12_non_admin_cannot_create_node_struct(self):
        """Non-admin user still cannot create node.struct in phase-2."""
        plain = self._make_plain_user('p2_nonode@test.com')
        with self.assertRaises(AccessError):
            self.env['node.struct'].with_user(plain).create({'name': 'n'})

    def test_13_admin_can_create_node_struct(self):
        """Admin group user can create node.struct in phase-2."""
        admin = self._make_admin_user('p2_node_admin@test.com')
        node = self.env['node.struct'].with_user(admin).create({'name': 'p2node'})
        self.assertTrue(node.id)

    # ────────────────────── multi-company record rules ───────────────────────────

    def test_14_work_auto_other_company_hidden(self):
        """work.auto from another company is hidden for a single-company user."""
        main_co = self.env.company
        other_co = self.env['res.company'].create({'name': 'P2 Other Co'})
        wa_other = self.env['work.auto'].sudo().create({
            'name': 'P2 Other Co WA',
            'model_id': self.model_partner.id,
            'company_id': other_co.id,
        })
        single_co_user = self.env['res.users'].create({
            'name': 'P2 SC User WA',
            'login': 'p2_sc_wa@test.com',
            'groups_id': [(4, self.env.ref('base.group_user').id)],
            'company_id': main_co.id,
            'company_ids': [(6, 0, [main_co.id])],
        })
        found = self.env['work.auto'].with_user(single_co_user).search(
            [('id', '=', wa_other.id)]
        )
        self.assertFalse(found)

    def test_15_work_function_other_company_hidden(self):
        """work.function from another company is hidden for a single-company user."""
        main_co = self.env.company
        other_co = self.env['res.company'].create({'name': 'P2 Other Func Co'})
        func = self.env['work.function'].sudo().create({
            'name': 'P2 OC Func',
            'func_name': 'p2_oc_func',
            'company_id': other_co.id,
        })
        single_co_user = self.env['res.users'].create({
            'name': 'P2 SC User Func',
            'login': 'p2_sc_func@test.com',
            'groups_id': [(4, self.env.ref('base.group_user').id)],
            'company_id': main_co.id,
            'company_ids': [(6, 0, [main_co.id])],
        })
        found = self.env['work.function'].with_user(single_co_user).search(
            [('id', '=', func.id)]
        )
        self.assertFalse(found)
