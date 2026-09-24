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


class TestProjectTask(TransactionCase):
    """
    Test case for the project.task extension that computes the `service_id`
    field based on the linked `field.service.request`.

    This test ensures that:
    - Tasks linked to a service request have their `service_id` correctly
      computed.
    - Tasks with no linked service request have `service_id` set to False.
    """
    @classmethod
    def setUpClass(cls):
        """
        Setup required data for testing compute_service_id:
        - Create a partner.
        - Create a skill category.
        - Create two tasks: one linked to a service request, one unlinked.
        - Create a service request linked to the first task.
        """
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.skill_category = cls.env['field.service.skill.category'].create({
            'name': 'Test Skill Category',
        })
        cls.task_linked = cls.env['project.task'].create(
            {'name': 'Linked Task'})
        cls.task_unlinked = cls.env['project.task'].create(
            {'name': 'Unlinked Task'})
        cls.service_request = cls.env['field.service.request'].create({
            'name': 'Linked Service Request',
            'partner_id': cls.partner.id,
            'task_id': cls.task_linked.id,
            'skill_category_id': cls.skill_category.id,
        })
    def test_compute_service_id(self):
        """
        Test the compute_service_id method of project.task.

        Steps:
        1. Call `compute_service_id` on the linked task.
           - Verify that `service_id` is set to the linked service request.
        2. Call `compute_service_id` on the unlinked task.
           - Verify that `service_id` is False for tasks without a linked
             service request.
        """
        self.task_linked.compute_service_id()
        self.assertEqual(self.task_linked.service_id, self.service_request)
        self.task_unlinked.compute_service_id()
        self.assertFalse(self.task_unlinked.service_id)
