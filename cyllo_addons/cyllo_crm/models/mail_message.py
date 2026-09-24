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

from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    is_pinned = fields.Boolean(
        string='Pinned',
        default=False,
        index=True,
        help="Pin this message to the top of the chatter",
    )

    @api.model
    def toggle_pin(self, ids):
        """Toggle pinned status for messages by IDs"""
        messages = self.browse(ids).filtered('id')
        for message in messages:
            message.is_pinned = not message.is_pinned
        return True

    def _get_message_format_fields(self):
        """Add is_pinned to the list of fields fetched for message formatting"""
        fields = super()._get_message_format_fields()
        if 'is_pinned' not in fields:
            fields.append('is_pinned')
        return fields