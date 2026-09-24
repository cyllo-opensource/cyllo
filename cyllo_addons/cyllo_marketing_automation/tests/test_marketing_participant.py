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

from odoo import fields
from odoo.tests import common

_logger = logging.getLogger(__name__)

class TestMarketingFilter(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        """Super setUpClass to create records to test fields in
            marketing_participant.
        """
        super().setUpClass()
        cls.campaign = cls.env['marketing.campaign'].create({
            'name': 'Campaign'
        })
        cls.participant = cls.env['marketing.participant'].create({
            'campaign_id': cls.campaign.id,
            'record': 'res.partner,1'
        })
        cls.activity1 = cls.env['marketing.activity'].create({
            'name': 'Activity 1',
            'campaign_id': cls.campaign.id,
            'type': 'mail'
        })
        cls.activity2 = cls.env['marketing.activity'].create({
            'name': 'Activity 2',
            'campaign_id': cls.campaign.id
        })
        cls.test_activity1 = cls.env['marketing.activity.line'].create({
            'participant_id': cls.participant.id,
            'activity_id': cls.activity1.id
        })
        cls.test_activity2 = cls.env['marketing.activity.line'].create({
            'participant_id': cls.participant.id,
            'activity_id': cls.activity2.id
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner 2',
            'email': 'testpartner2@example.com',
        })

    def test_compute_activity_ids(self):
        """
            Test the _compute_activity_ids method.

            Checks if the activity_ids field is correctly computed.
        """
        _logger.info('Starts test_compute_activity_ids')
        self.participant._compute_activity_ids()
        self.assertEqual(self.participant.activity_ids.ids,
                         [self.test_activity1.activity_id.id,
                          self.test_activity2.activity_id.id])
        _logger.info('Ends test_compute_activity_ids')

    def test_inverse_record(self):
        """
            Test the _inverse_record method.

            Checks if the record_id field is correctly set.
        """
        _logger.info('Starts test_inverse_record')
        self.participant._inverse_record()
        self.assertEqual(self.participant.record_id, 1)
        _logger.info('Ends test_inverse_record')

    def test_unlink_method(self):
        """
            Test the unlink method.

            Checks if the participant and related records are successfully
            deleted.
        """
        _logger.info('Starts test_unlink_method')
        activity_line = self.env['marketing.activity.line'].create({
            'activity_id': self.activity1.id,
            'participant_id': self.participant.id,
            'mail_opened': False,
            'mail_clicked': False,
            'activity_another_trigger': False,
            'mail_trace_ids': [(0, 0, {
                'trace_type': 'mail',
                'model': 'res.partner',
                'res_id': self.partner.id,
            })],
        })
        self.participant.write({
            'test_activity_ids': [(4, activity_line.id)]
        })
        self.participant.unlink()
        self.assertFalse(self.participant.exists())
        self.assertFalse(
            self.participant.test_activity_ids.mail_trace_ids.exists())
        _logger.info('Ends test_unlink_method')

    def test_selection_models(self):
        """
            Test the _selection_models method.

            Checks if the method returns a valid selection of models that are
            mail threads.
        """
        _logger.info('Starts test_selection_models')
        result = self.participant._selection_models()
        self.assertTrue(result)
        for item in result:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)
        _logger.info('Ends test_selection_models')

    def test_update_record(self):
        """
            Test the update_record method.

            Checks if the method correctly updates the is_inactive field of the
            participant.
        """
        _logger.info('Starts test_update_record')
        activity = self.env['marketing.activity'].create({
            'name': 'Activity 1',
            'type': 'mail',
            'campaign_id': self.campaign.id,
            'test_date_started': fields.datetime.now(),
        })
        participant = self.env['marketing.participant'].create({
            'campaign_id': self.campaign.id,
            'record': 'res.partner,1',
            'is_inactive': False
        })
        activity_line = self.env['marketing.activity.line'].create({
            'activity_id': activity.id,
            'participant_id': participant.id
        })
        data = {'activity_line': activity_line.id,
                'participant_id': participant.id}
        participant.update_record(data)
        self.assertEqual(participant.is_inactive, True)
        _logger.info('Ends test_update_record')

    def test_create_test_participant(self):
        """
            Test the create_test_participant method.

            Checks if the method correctly creates a test participant with the
            provided data.
        """
        _logger.info('Starts test_create_test_participant')
        self.campaign.activity_ids = [
            (0, 0, {'name': 'Activity 1',
                    'type': 'mail',
                    'campaign_id': self.campaign.id}),
            (0, 0, {'name': 'Activity 2',
                    'type': 'mail',
                    'campaign_id': self.campaign.id})]
        data = {
            'record': 'res.partner,1',
            'campaign_id': self.campaign.id,
            'record_id': 1,
            'state': 'running',
            'record_count': 2,
            'is_test_participant': True
        }
        participant_id = self.env[
            'marketing.participant'].create_test_participant(data)
        participant = self.env['marketing.participant'].browse(participant_id)
        self.assertEqual(participant.campaign_id.id, self.campaign.id)
        self.assertEqual(participant.record_id, 1)
        self.assertEqual(participant.state, 'running')
        self.assertEqual(participant.record_count, 2)
        self.assertEqual(participant.is_test_participant, True)
        self.assertEqual(len(participant.test_activity_ids),
                         len(self.campaign.activity_ids))
        _logger.info('Ends test_create_test_participant')
