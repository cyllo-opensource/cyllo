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


class TestAccountFollowUpLine(TransactionCase):

    def setUp(self):
        super().setUp()
        self.FollowUpLine = self.env['accounting.followup.line']

    def test_create_followup_line(self):
        """Test follow-up line creation with required fields"""
        followup = self.FollowUpLine.create({
            'title': 'First Reminder',
            'due_date': 5,
            'send_mail': True,
        })

        self.assertTrue(followup)
        self.assertEqual(followup.title, 'First Reminder')

    def test_default_company(self):
        """Test company_id default value"""
        followup = self.FollowUpLine.create({
            'title': 'Company Check',
        })

        self.assertEqual(followup.company_id, self.env.company)

    def test_default_mail_template(self):
        """Test default mail template is set"""
        followup = self.FollowUpLine.create({
            'title': 'Mail Template Check',
        })

        self.assertTrue(followup.mail_template_id)
        self.assertEqual(
            followup.mail_template_id.model,
            'res.partner'
        )

    def test_required_title(self):
        """Title should be required"""
        with self.assertRaises(Exception):
            self.FollowUpLine.create({
                'due_date': 10
            })
