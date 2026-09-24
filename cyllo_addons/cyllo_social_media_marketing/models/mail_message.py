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
from odoo import fields, models


class MailMessage(models.Model):
    """ Extended Mail Message class to add custom actions."""
    _inherit = 'mail.message'

    is_possible_lead = fields.Boolean(string="Possible to Make Lead", help="Thi message can be converted to lead")

    def action_reply_message(self, reply):
        """ Method for replying to a message."""
        return True

    def action_create_lead(self):
        """ Action to create lead on the basis of message."""
        return False

    def action_reply_message_chatter(self, sender_id, reply, res_id):
        """ Method for replying to a message from chatter."""
        return True
