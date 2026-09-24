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

class TestResUsers(TransactionCase):
    """
    Test cases for 'res.users' extensions for WhatsApp integration, covering
    API account data management and token generation.
    """

    def setUp(self):
        """
        Setup test environment for WhatsApp user configuration tests.
        """
        super(TestResUsers, self).setUp()
        self.User = self.env['res.users']
        self.test_user = self.env['res.users'].create({
            'name': 'WhatsApp User',
            'login': 'wa_user',
            'email': 'wa@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })

    def test_get_user_data(self):
        """
        Test the retrieval of structured WhatsApp API configuration data for a user.
        """
        self.test_user.write({
            'token': 'test_token',
            'account_uid': 'test_acc',
            'phone_uid': 'test_phone',
            'app_uid': 'test_app',
        })
        data = self.test_user.get_user_data(self.test_user.id)
        self.assertEqual(data['token'], 'test_token')
        self.assertEqual(data['phone_uid'], 'test_phone')

    def test_action_generate_token(self):
        """
        Test the generation and verification of WhatsApp return tokens for API callbacks.
        """
        self.test_user.write({
            'token': 'test_token',
            'account_uid': 'test_acc',
            'phone_uid': 'test_phone',
            'app_uid': 'test_app',
        })
        self.test_user.action_generate_token()
        self.assertTrue(self.test_user.return_token)
        param = self.env['ir.config_parameter'].sudo().get_param('res_users.whatsapp_return_token')
        self.assertEqual(self.test_user.return_token, param)
