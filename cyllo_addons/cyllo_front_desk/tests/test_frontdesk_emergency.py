# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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

class TestFrontdeskEmergency(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 1. Create a Station
        cls.station = cls.env['frontdesk.frontdesk'].create({
            'name': 'HQ Reception'
        })
        
        # 2. Create an Emergency Alert configuration
        cls.alert = cls.env['frontdesk.emergency.alert'].create({
            'name': 'Intruder Alert',
            'station_ids': [(4, cls.station.id)],
            'default_message': 'Intruder detected. Seek shelter.',
        })

    def test_emergency_alert_flow(self):
        # 1. Create the Wizard
        wizard = self.env['frontdesk.emergency.wizard'].create({
            'station_id': self.station.id,
            'alert_id': self.alert.id,
            'message': self.alert.default_message,
        })
        
        # 2. Verify onchange populates message
        wizard._onchange_alert_id()
        self.assertEqual(wizard.message, 'Intruder detected. Seek shelter.')

        # 3. Trigger action_send_alert
        action = wizard.action_send_alert()
        self.assertEqual(action.get('type'), 'ir.actions.client')
        
        # 4. Verify log creation
        log_id = action['params']['next']['res_id']
        log = self.env['frontdesk.emergency.log'].browse(log_id)
        self.assertTrue(log.exists())
        self.assertEqual(log.station_id, self.station)
        self.assertEqual(log.alert_id, self.alert)
        self.assertEqual(log.message, 'Intruder detected. Seek shelter.')
