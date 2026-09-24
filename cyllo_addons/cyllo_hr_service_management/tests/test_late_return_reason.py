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
from unittest.mock import patch


class TestLateReturnReason(TransactionCase):
    """
    Test suite for the Late Return Reason wizard.
    This ensures that when a late return is logged, the service request:
    - Moves to the correct state ("quality")
    - Has its return date set
    - Sends the appropriate email
    - Logs chatter messages about the equipment being ready to return
      and the late return reason
    """
    @classmethod
    def setUpClass(cls):
        """
        Test setup:
        - Create a handler employee with an email
        - Create a service category
        - Create a service request in 'draft' state linked to the handler
        - Create a wizard record with a reason for the late return
        """
        super().setUpClass()
        cls.handler = cls.env['hr.employee'].create({
            'name': 'Test Handler',
            'work_email': 'test@test.com',
            'private_email': 'test@test.com',
        })
        cls.category = cls.env['hr.service.category'].create({
            'name': 'Test Category',
        })
        cls.service_request = cls.env['hr.service'].create({
            'name': 'Test Service Request',
            'employee_id': cls.handler.id,
            'service_handler_id': cls.handler.id,
            'service_category_id': cls.category.id,
            'state': 'draft',
        })
        cls.wizard = cls.env['late.return.reason'].create({
            'service_request_id': cls.service_request.id,
            'reason': 'Delayed due to technical issues',
        })
        
    def test_action_run(self):
        """
        Test the action_return method:
        1. It updates the service request state to 'quality'.
        2. It sets a return_date on the service request.
        3. It sends an email using the related mail template.
        4. It posts two chatter messages:
           - One confirming equipment is ready to return.
           - One containing the provided late return reason.
        """
        with patch('odoo.addons.mail.models.mail_template.MailTemplate.'
                   'send_mail',
                return_value=True) as mock_send_mail:
            self.wizard.action_return()
            self.assertEqual(self.service_request.state, 'quality')
            self.assertIsNotNone(self.service_request.return_date)
            self.assertEqual(mock_send_mail.call_count, 1)
            bodies = [m.body for m in self.service_request.message_ids]
            self.assertTrue(
                any("Equipment have been ready to return" in b for b in bodies),
                "Expected readiness message not found"
            )
            self.assertTrue(
                any("Late Return Reason" in b for b in bodies),
                "Expected late return reason message not found"
            )
