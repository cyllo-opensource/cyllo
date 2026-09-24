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


class MailingMailing(models.Model):
    """
        This model inherits from the base 'mailing.mailing' model and extends
        or overrides its functionality as needed.
    """
    _inherit = "mailing.mailing"

    cy_automation_template = fields.Boolean(string='Automation Template',
                                            help='Is marketing automation template')

    @api.model
    def default_get(self, fields):
        """
               Customize default values for fields when creating a new record.

               If the context contains 'default_cy_automation_template' set to True,
               this method updates the context to set:
                 - 'default_subject' with the value of 'default_name' from the context, if any.
                 - 'default_email_from' with the formatted email of the user who created the record,
                   or the current user's email if unavailable.

               Then, it calls the super method to fetch default values using the updated context.

               Args:
                   fields (list): List of field names for which default values are requested.

               Returns:
                   dict: A dictionary containing the default values for the requested fields.
               """
        if self.env.context.get("default_cy_automation_template", False):
            context = dict(self.env.context)
            context['default_subject'] = context.get('default_name', False)
            context['default_email_from'] = (self.create_uid.email_formatted or
                                             self.env.user.email_formatted)
            self = self.with_context(context)
        res = super().default_get(fields)
        return res
