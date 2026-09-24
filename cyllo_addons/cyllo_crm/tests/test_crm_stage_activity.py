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
from odoo import fields
from datetime import timedelta, datetime
from unittest.mock import patch


class TestCrmStageActivity(TransactionCase):
    """

    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env['res.company'].create({'name': 'Test stage company'})
        cls.user = cls.env['res.users'].create({
            'name': 'Test stage user',
            'login': 'Test stage user',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
        })
        cls.stage = cls.env['crm.stage'].create({
            'name': 'Qualification',
            'sequence': 1,
        })
        cls.opportunity = cls.env['crm.lead'].create({
            'name': 'Test Opportunity',
            'type': 'opportunity',
            'user_id': cls.user.id,
            'company_id': cls.company.id,
            'stage_id': cls.stage.id,
        })
        cls.activity_type = cls.env['mail.activity.type'].create({
            'name': 'Follow-up',
            'delay_count': 3
        })
        cls.big_lead = cls.env['crm.lead'].create({
            'name': 'Big Deal Lead',
            'company_id': cls.company.id,
        })

    def test_create_exit_criteria_if_needed(self):
        """

        """
        result = (self.env['crm.stage.activity']._create_exit_criteria_if_needed
                  (999, self.stage.id))
        self.assertFalse(result)
        result = (self.env['crm.stage.activity']._create_exit_criteria_if_needed
                  (self.opportunity.id, self.stage.id))
        self.assertFalse(result)

        exit_criteria = self.env['crm.stage.activity'].create({
            'stage_id': self.stage.id,
            'activity_id': self.activity_type.id,
            'is_exit_criteria': True,
        })
        activity = self.env['mail.activity'].create({
            'activity_type_id': self.activity_type.id,
            'summary': "Existing Exit Criteria",
            'res_model_id': self.env.ref('crm.model_crm_lead').id,
            'res_id': self.opportunity.id,
            'user_id': self.user.id,
            'date_deadline': fields.Date.today(),
            'is_exit_criteria': True,
        })
        result = self.env['crm.stage.activity']._create_exit_criteria_if_needed(
            self.opportunity.id, self.stage.id)
        self.assertFalse(result)

        activity.action_done()

        result = self.env['crm.stage.activity']._create_exit_criteria_if_needed(
            self.opportunity.id, self.stage.id)
        self.assertTrue(result)

        result = self.env['crm.stage.activity']._create_exit_criteria_if_needed(
            self.opportunity.id, self.stage.id
        )
        self.assertFalse(result)

    def test_notify_user_activity(self):
        """
        Test that notify_user_activity calls send_mail correctly.
        """
        activity_summary = "Follow up call"
        stage_name = "Negotiation"
        lead_name = self.big_lead.name
        deadline = datetime.today() + timedelta(days=2)  # ✅ define it

        exit_activity = self.env['crm.stage.activity'].create({
            'stage_id': self.stage.id,
            'activity_id': self.activity_type.id,
            'is_exit_criteria': True,
            'user_id': self.user.id,
        })

        with patch(
                "odoo.addons.mail.models.mail_template.MailTemplate.send_mail") as mock_send:
            exit_activity.notify_user_activity(
                self.user.id,
                activity_summary,
                stage_name,
                lead_name,
                deadline,
            )
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            self.assertEqual(args[0], exit_activity.id)
            self.assertTrue(kwargs.get("force_send"))
