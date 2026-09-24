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
from odoo.tests import common


class TestMailingTrace(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        """
        Set up test data for mailing trace model.

        Creates a marketing activity line and a mailing trace record with predefined values
        to test the functionality of the get_display_value method.
        """
        super().setUpClass()
        # Create a marketing activity line record
        cls.activity_line = cls.env['marketing.activity.line'].create({
            'mail_clicked': False,
            'mail_opened': False,
            'mail_replied': False,
            'mail_bounced': False,
        })

        # Create a partner record (res_id will reference this record)
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'testpartner@example.com',
        })

        # Create a mailing trace record
        cls.mailing_trace = cls.env['mailing.trace'].create({
            'failure_type': 'mail_dup',
            'model': 'res.partner',  # Model name
            'res_id': cls.partner.id,  # ID of the related partner record
            'marketing_activity_line_id': cls.activity_line.id,
        })

    def test_get_display_value(self):
        """
        Test the get_display_value method.

        Verifies that the method returns the correct display value for a given failure type.
        """
        # Get the key of the failure type
        failure_key = self.mailing_trace.failure_type

        # Call the get_display_value method
        display_value = self.mailing_trace.get_display_value(failure_key)

        # Expected display value for 'mail_dup'
        expected_display_value = 'Duplicated Email'

        # Assert that the display value matches the expected value
        self.assertEqual(
            display_value,
            expected_display_value,
            f"The display value for failure type '{failure_key}' should be '{expected_display_value}', but got '{display_value}'."
        )
    def test_set_clicked(self):
        """
            Test the set_clicked method.

            Checks if the mail_clicked field is set to True.
        """
        self.mailing_trace.set_clicked()
        self.assertEqual(self.activity_line.mail_clicked, True)
        self.assertNotEqual(self.activity_line.mail_opened, False)

    def test_set_opened(self):
        """
            Test the set_opened method.

            Checks if the mail_opened field is set to True.
        """
        self.mailing_trace.set_opened()
        self.assertEqual(self.activity_line.mail_opened, True)

    def test_set_replied(self):
        """
            Test the set_replied method.

            Checks if the mail_opened field is set to True and mail_replied is
            not False.
        """
        self.mailing_trace.set_replied()
        self.assertEqual(self.activity_line.mail_opened, True)
        self.assertNotEqual(self.activity_line.mail_replied, False)

    def test_set_bounced(self):
        """
            Test the set_bounced method.

            Checks if the mail_bounced field is set to True.
        """
        self.mailing_trace.set_bounced()
        self.assertEqual(self.activity_line.mail_bounced, True)
