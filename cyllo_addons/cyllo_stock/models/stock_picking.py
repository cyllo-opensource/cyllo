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

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _attach_sign(self):
        """
        Override _attach_sign to run as sudo if the current user has no email address configured.
        This prevents an 'Unable to send message' UserError when the signed delivery slip
        is posted to the chatter.
        """
        if not self.env.user.email:
            return super(StockPicking, self.sudo())._attach_sign()
        return super()._attach_sign()

    def _send_confirmation_email(self):
        """
        Override _send_confirmation_email to run as sudo if the current user has no email address.
        This prevents a crash when the delivery confirmation email is sent automatically.
        """
        if not self.env.user.email:
            return super(StockPicking, self.sudo())._send_confirmation_email()
        return super()._send_confirmation_email()

