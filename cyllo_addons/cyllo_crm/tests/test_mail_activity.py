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
from datetime import timedelta, date


class TestMailActivity(TransactionCase):
    """
    Test cases for MailActivity model method `get_crm_activities_summary`.

    This class ensures that activities related to CRM leads are correctly
    grouped and counted by their activity type when filtered by date ranges
    (`date_from`, `date_to`) and lead domains.

    """
    @classmethod
    def setUpClass(cls):
        """
        Set up test data for CRM leads, activity types, and activities.

        Creates:
        - Two CRM leads (lead1, lead2).
        - Two activity types (Call, Email).
        - Three activities:
            * Call (5 days in the past).
            * Email (today).
            * Call (5 days in the future).
        """
        super().setUpClass()

        cls.company = cls.env['res.company'].create({'name': 'Test Company'})
        cls.user = cls.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])]

        })
        cls.lead1 = cls.env['crm.lead'].create({
            'name': 'Lead 1',
            'user_id': cls.user.id,
            'company_id': cls.company.id,
        })
        cls.lead2 = cls.env['crm.lead'].create({
            'name': 'Lead 2',
            'user_id': cls.user.id,
            'company_id': cls.company.id,
        })
        cls.call_type = cls.env['mail.activity.type'].create({
            'name': 'Call',
        })
        cls.email_type = cls.env['mail.activity.type'].create({
            'name': 'Email',
        })
        today = date.today()
        lead_model = cls.env['ir.model']._get('crm.lead')
        cls.activity1 = cls.env['mail.activity'].create({
            'res_model': 'crm.lead',
            'res_model_id': lead_model.id,
            'res_id': cls.lead1.id,
            'activity_type_id': cls.call_type.id,
            'date_deadline': today - timedelta(days=5),
        })
        cls.activity2 = cls.env['mail.activity'].create({
            'res_model': 'crm.lead',
            'res_model_id': lead_model.id,
            'res_id': cls.lead1.id,
            'activity_type_id': cls.email_type.id,
            'date_deadline': today,
        })
        cls.activity3 = cls.env['mail.activity'].create({
            'res_model': 'crm.lead',
            'res_id': cls.lead2.id,
            'res_model_id': lead_model.id,
            'activity_type_id': cls.call_type.id,
            'date_deadline': today + timedelta(days=5),
        })

    def test_get_crm_activities_summary(self):
        """
        Verify that `get_crm_activities_summary` correctly groups and counts
         activities.

        Scenarios tested:
        1. Without date filters → Call=2, Email=1.
        2. With date_from=today → Call=1, Email=1.
        3. With date_to=today → Call=1, Email=1.
        4. With date_from=today and date_to=today → Call=0, Email=1.
        """
        summary = self.env['mail.activity'].get_crm_activities_summary(
            domain=[('id', 'in', [self.lead1.id, self.lead2.id])]
        )
        self.assertEqual(summary.get('Call', 0), 2)
        self.assertEqual(summary.get('Email', 0), 1)
        today = date.today()
        summary = self.env['mail.activity'].get_crm_activities_summary(
            date_from=today,
            domain=[('id', 'in', [self.lead1.id, self.lead2.id])]
        )
        self.assertEqual(summary.get('Call', 0), 1)
        self.assertEqual(summary.get('Email', 0), 1)
        self.assertEqual(summary.get('Call', 0), 1)
        self.assertEqual(summary.get('Email', 0), 1)
        summary = self.env['mail.activity'].get_crm_activities_summary(
            date_to=today,
            domain=[('id', 'in', [self.lead1.id, self.lead2.id])]
        )
        self.assertEqual(summary.get('Call', 0), 1)
        self.assertEqual(summary.get('Email', 0), 1)
        summary = self.env['mail.activity'].get_crm_activities_summary(
            date_from=today,
            date_to=today,
            domain=[('id', 'in', [self.lead1.id, self.lead2.id])]
        )
        self.assertEqual(summary.get('Call', 0), 0)
        self.assertEqual(summary.get('Email', 0), 1)
