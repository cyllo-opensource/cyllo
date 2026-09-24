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
import logging

from odoo.tests import common

_logger = logging.getLogger(__name__)

class TestMarketingActivityLine(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        """Super setUpClass to create records to test fields in
            marketing_activity_line.

           Creates a marketing campaign, activity, participant, and
           activity line.
        """
        super().setUpClass()
        cls.campaign = cls.env['marketing.campaign'].create({
            'name': 'Campaign 1'
        })
        cls.activity = cls.env['marketing.activity'].create({
            'name': 'Activity 1',
            'type': 'mail',
            'campaign_id': cls.campaign.id,
        })
        cls.participant = cls.env['marketing.participant'].create({
            'campaign_id': cls.campaign.id,
            'record': 'res.partner,1',
            'record_id': 1,
            'is_test_participant': False,
            'is_inactive': False
        })
        cls.activity_line = cls.env['marketing.activity.line'].create({
            'activity_id': cls.activity.id,
            'participant_id': cls.participant.id,
            'mail_opened': False,
            'mail_clicked': False,
            'activity_another_trigger': False,
        })

    def test_trigger_next_activity(self):
        """
            Test the trigger_next_activity method.

            Checks if the trigger_next_activity method updates fields
            appropriately.
        """
        _logger.info('Starts test_trigger_next_activity')
        self.activity.sub_parent_activity_id = self.activity.id
        self.activity_line.trigger_next_activity('opened')
        self.assertEqual(self.activity_line.mail_opened, True)
        self.assertEqual(self.activity_line.mail_clicked, False)
        self.assertEqual(self.activity_line.activity_another_trigger, True)
        _logger.info('Ends test_trigger_next_activity')
