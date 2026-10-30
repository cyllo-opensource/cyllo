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
from lxml import etree
from odoo.tests.common import TransactionCase

from ..hooks import uninstall_hook


class TestCrmProjectFlows(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Lead = cls.env['crm.lead']
        cls.partner = cls.env['res.partner'].create({'name': 'Flow Partner'})
        cls.project = cls.env.ref('cyllo_crm_project.project_crm_leads')

    def _lead(self, **vals):
        return self.Lead.create({'name': 'Flow Lead', **vals})


class TestDefaultData(TestCrmProjectFlows):
    """Records shipped with the module."""

    def test_default_project(self):
        self.assertEqual(self.project.name, 'CRM Leads')
        self.assertEqual(self.project.user_id, self.env.ref('base.user_admin'))

    def test_default_stages(self):
        stages = self.project.type_ids.sorted('sequence')
        self.assertEqual(stages.mapped('name'), ['New', 'In Progress', 'Done'])
        self.assertEqual(stages.mapped('sequence'), [1, 2, 3])

    def test_only_done_stage_is_folded(self):
        done = self.env.ref('cyllo_crm_project.crm_leads_stage_done')
        new = self.env.ref('cyllo_crm_project.crm_leads_stage_new')
        progress = self.env.ref('cyllo_crm_project.crm_leads_stage_in_progress')
        self.assertTrue(done.fold)
        self.assertFalse(new.fold)
        self.assertFalse(progress.fold)


class TestCreateTask(TestCrmProjectFlows):

    def test_task_is_linked_to_lead(self):
        lead = self._lead(partner_id=self.partner.id)
        lead.action_create_task()
        self.assertTrue(lead.task_id.exists())
        self.assertEqual(lead.task_id.name, 'Flow Lead')
        self.assertEqual(lead.task_id.project_id, self.project)
        self.assertEqual(lead.task_id.partner_id, self.partner)

    def test_task_without_customer(self):
        lead = self._lead()
        lead.action_create_task()
        self.assertFalse(lead.task_id.partner_id)
        self.assertEqual(lead.task_id.project_id, self.project)

    def test_task_starts_in_first_stage(self):
        lead = self._lead()
        lead.action_create_task()
        self.assertEqual(lead.task_id.stage_id,
                         self.env.ref('cyllo_crm_project.crm_leads_stage_new'))

    def test_action_opens_new_task(self):
        lead = self._lead()
        action = lead.action_create_task()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'project.task')
        self.assertEqual(action['res_id'], lead.task_id.id)
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'current')

    def test_each_lead_gets_its_own_task(self):
        first, second = self._lead(name='First'), self._lead(name='Second')
        first.action_create_task()
        second.action_create_task()
        self.assertNotEqual(first.task_id, second.task_id)
        self.assertEqual(
            self.project.task_ids & (first.task_id | second.task_id),
            first.task_id | second.task_id)

    def test_task_name_is_not_synced_later(self):
        lead = self._lead()
        lead.action_create_task()
        lead.name = 'Renamed'
        self.assertEqual(lead.task_id.name, 'Flow Lead')

    def test_task_without_default_project(self):
        self.env['project.task.type'].search(
            [('project_ids', 'in', self.project.id)]).unlink()
        self.project.unlink()
        lead = self._lead()
        lead.action_create_task()
        self.assertTrue(lead.task_id)
        self.assertFalse(lead.task_id.project_id)

    def test_deleting_task_clears_link(self):
        lead = self._lead()
        lead.action_create_task()
        lead.task_id.unlink()
        self.assertFalse(lead.task_id)


class TestOpenTask(TestCrmProjectFlows):

    def test_open_action_points_to_linked_task(self):
        lead = self._lead()
        lead.action_create_task()
        action = lead.action_open_task()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'project.task')
        self.assertEqual(action['res_id'], lead.task_id.id)
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'current')

    def test_open_does_not_create_a_task(self):
        lead = self._lead()
        count = self.env['project.task'].search_count([])
        lead.action_open_task()
        self.assertEqual(self.env['project.task'].search_count([]), count)


class TestLeadFormView(TestCrmProjectFlows):

    def _button(self, name):
        arch = self.Lead.get_view(
            self.env.ref('crm.crm_lead_view_form').id)['arch']
        buttons = etree.fromstring(arch).xpath('//button[@name="%s"]' % name)
        self.assertEqual(len(buttons), 1, name)
        return buttons[0]

    def test_create_task_button_conditions(self):
        invisible = self._button('action_create_task').get('invisible')
        self.assertIn('task_id', invisible)
        self.assertIn('probability', invisible)

    def test_task_button_hidden_without_task(self):
        button = self._button('action_open_task')
        self.assertIn('not task_id', button.get('invisible'))
        self.assertEqual(button.get('class'), 'oe_stat_button')

    def test_task_field_is_in_the_view(self):
        arch = self.Lead.get_view(
            self.env.ref('crm.crm_lead_view_form').id)['arch']
        self.assertTrue(etree.fromstring(arch).xpath('//field[@name="task_id"]'))


class TestAccessGroups(TestCrmProjectFlows):

    def test_salesman_gets_project_user(self):
        group = self.env.ref('sales_team.group_sale_salesman')
        self.assertIn(self.env.ref('project.group_project_user'),
                      group.implied_ids)

    def test_sales_manager_gets_project_manager(self):
        group = self.env.ref('sales_team.group_sale_manager')
        self.assertIn(self.env.ref('project.group_project_manager'),
                      group.implied_ids)

    def test_salesman_can_create_and_open_task(self):
        user = self.env['res.users'].create({
            'name': 'Flow Salesman', 'login': 'flow_salesman',
            'groups_id': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('sales_team.group_sale_salesman').id])],
        })
        lead = self.Lead.with_user(user).create({'name': 'Mine'})
        lead.action_create_task()
        self.assertTrue(lead.task_id)
        self.assertEqual(lead.action_open_task()['res_id'], lead.task_id.id)


class TestUninstallHook(TestCrmProjectFlows):

    def test_records_survive_uninstall(self):
        uninstall_hook(self.env)
        self.assertFalse(self.env['ir.model.data'].search(
            [('module', '=', 'cyllo_crm_project')]))
        self.assertTrue(self.project.exists())
        self.assertTrue(self.project.type_ids)
