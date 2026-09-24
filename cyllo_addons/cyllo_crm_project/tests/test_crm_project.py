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
from odoo.tests.common import TransactionCase

class TestCrmProject(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.lead = cls.env['crm.lead'].create({
            'name': 'Test Lead Task',
            'partner_id': cls.partner.id,
        })
        project = cls.env.ref('cyllo_crm_project.project_crm_leads', raise_if_not_found=False)
        if not project:
            cls.project = cls.env['project.project'].create({'name': 'CRM Leads Project'})
            cls.env['ir.model.data'].create({
                'name': 'project_crm_leads',
                'module': 'cyllo_crm_project',
                'model': 'project.project',
                'res_id': cls.project.id,
            })
        else:
            cls.project = project

    def test_action_create_task(self):
        """Test action_create_task creates a project.task and sets task_id"""
        self.assertFalse(self.lead.task_id)
        action = self.lead.action_create_task()
        self.assertTrue(self.lead.task_id)
        self.assertEqual(self.lead.task_id.name, 'Test Lead Task')
        self.assertEqual(self.lead.task_id.partner_id, self.partner)
        self.assertEqual(self.lead.task_id.project_id, self.project)
        self.assertEqual(action.get('res_model'), 'project.task')
        self.assertEqual(action.get('res_id'), self.lead.task_id.id)
        self.assertEqual(action.get('view_mode'), 'form')

    def test_action_open_task(self):
        """Test action_open_task returns correct action dict"""
        self.lead.action_create_task()
        action = self.lead.action_open_task()
        self.assertEqual(action.get('res_model'), 'project.task')
        self.assertEqual(action.get('res_id'), self.lead.task_id.id)
        self.assertEqual(action.get('view_mode'), 'form')
