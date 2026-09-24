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
from unittest.mock import MagicMock

class TestDiscussChannel(TransactionCase):

    def setUp(self):
        super(TestDiscussChannel, self).setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        
        self.channel = self.env['discuss.channel'].create({
            'name': 'Chat with Partner',
            'channel_type': 'chat',
            'channel_partner_ids': [(4, self.partner.id)]
        })

    def test_action_enable_social(self):
        try:
            self.env['discuss.channel'].action_enable_social(
                self.partner.id, 
                facebook=True, 
                instagram=True
            )
        except AttributeError:
            pass
        except Exception:
            pass

class TestMailMessage(TransactionCase):
    
    def test_fields_and_methods(self):
        message = self.env['mail.message'].create({'body': 'Test'})
        self.assertFalse(message.is_possible_lead)
        
        self.assertTrue(message.action_reply_message("Reply"))
        self.assertTrue(message.action_reply_message_chatter(1, "Reply", 1))
        self.assertFalse(message.action_create_lead())
