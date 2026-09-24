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


class MailComposeMessage(models.TransientModel):
    """Inherit model mail.compose.message with additional fields and methods."""
    _inherit = 'mail.compose.message'

    marketing_activity_id = fields.Many2one('marketing.activity',
                                            ondelete='cascade',
                                            help="Marketing activity")

    def _prepare_mail_values_mailing_traces(self, mail_values_all):
        """
            Override method to link mail automation activity with mail
            statistics.

            This method prepares the mail trace values and adds the link to the
            corresponding marketing activity line.

            Args:
                mail_values_all (dict): A dictionary containing mail trace
                values.

            Returns:
                dict: The updated mail trace values with the link to marketing
                activity line.
        """
        mail_trace_vals = super()._prepare_mail_values_mailing_traces(
            mail_values_all)
        if not self.marketing_activity_id:
            return mail_trace_vals
        # Retrieve marketing activity lines related to the current marketing
        # activity
        activity_line = self.env['marketing.activity.line'].search(
            [('activity_id', '=', self.marketing_activity_id.id),
             ('record_id', 'in', list(mail_trace_vals.keys()))])
        # Create a dictionary mapping record_id to marketing activity line id
        mail_trace = {record.record_id: record.id for record in activity_line}
        # Update mail trace values with the link to marketing activity line
        for record_id, vals in mail_trace_vals.items():
            vals['marketing_activity_line_id'] = mail_trace[record_id]
        return mail_trace_vals
