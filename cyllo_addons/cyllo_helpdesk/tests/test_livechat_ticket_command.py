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
from odoo.tests import common


class TestLivechatTicketCommand(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create(
            {
                "name": "Visitor Partner",
                "email": "visitor@example.com",
                "phone": "1234567890",
            }
        )
        self.livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Website Support",
                "user_ids": [(6, 0, self.env.user.ids)],
            }
        )
        self.channel = self.env["discuss.channel"].create(
            {
                "name": "Livechat Session",
                "channel_type": "livechat",
                "livechat_operator_id": self.env.user.partner_id.id,
                "livechat_channel_id": self.livechat_channel.id,
                "channel_member_ids": [
                    (0, 0, {"partner_id": self.env.user.partner_id.id}),
                    (0, 0, {"partner_id": self.partner.id}),
                ],
            }
        )

    def test_execute_command_ticket_creates_helpdesk_ticket(self):
        ticket_id = self.channel.execute_command_ticket(body="/ticket Printer issue")
        ticket = self.env["helpdesk.ticket"].browse(ticket_id)

        self.assertTrue(ticket.exists())
        self.assertEqual(ticket.name, "Printer issue")
        self.assertEqual(ticket.customer_id, self.partner)
        self.assertEqual(ticket.email, self.partner.email)
        self.assertEqual(ticket.phone, self.partner.phone)
