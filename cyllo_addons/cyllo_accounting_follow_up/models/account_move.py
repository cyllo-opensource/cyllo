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


class AccountMove(models.Model):
    """
       This model extends the `account.move` model to add fields for managing
       follow-up actions related to accounting, including the next and last follow-up lines.
       """
    _inherit = "account.move"

    next_follow_up_id = fields.Many2one('accounting.followup.line',
                                        'Next Follow Up',
                                        help='References the next follow-up action for this account move.')
    last_follow_up_id = fields.Many2one('accounting.followup.line',
                                        'Last Follow-Up Taken',
                                        help='References the last follow-up action taken for this account move.'
                                        )

    def many2one_action(self):
        """
                Triggers the follow-up action change for the partner associated with this account move.

                This method calls the `change_followup_action` method on the `partner_id`
                of the current account move, passing the move as a parameter.
                """
        self.partner_id.change_followup_action(self)
