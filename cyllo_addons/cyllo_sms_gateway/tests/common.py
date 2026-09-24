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

class TestCylloSmsGateway(common.TransactionCase):
    """
    Common setup class for SMS gateway tests, providing pre-configured 
    gateway settings, partners, and SMS records for test isolation.
    """

    @classmethod
    def setUpClass(cls):
        """
        Initialize class-level test data for SMS gateway operations.
        """
        super().setUpClass()
        cls.sms_gateway = cls.env['sms.gateway.config'].create({
            'name': 'TWILIO',
            'twilio_account_sid': 'TEST_SID',
            'twilio_auth_token': 'TEST_TOKEN',
            'twilio_phone_number': '+911234567890',
            'is_active': False,
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
            'mobile': '+9876543210',
        })
        cls.send_sms = cls.env['send.sms'].create({
            'sms_id': cls.sms_gateway.id,
            'sms_to': cls.partner.mobile,
            'text': 'Test Text',
            'partner_ids': cls.partner.ids,
        })
