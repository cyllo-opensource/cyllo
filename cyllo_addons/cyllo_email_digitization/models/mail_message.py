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
import email
from odoo import models


class MailMessage(models.Model):
    """ Override MailMessage class in order to add a new type: SMS messages.
    Those messages come with their own notification method, using SMS
    gateway. """
    _inherit = 'mail.message'

    def create(self, vals_list):
        """supering the function to create digitize the record automatically in email.digitization.data model"""
        res = super(MailMessage, self).create(vals_list)
        for record in res:
            if record.model == 'email.digitization.data':
                if not record.parent_id:
                    email_digi_data = self.env[
                        'email.digitization.data'].search(
                        [('id', '=', record.res_id)])
                    from_name, from_address = email.utils.parseaddr(
                        record.email_from)
                    if from_address:
                        email_digitization_config = self.env[
                            'email.digitization.config'].search([
                            ('email', '=', from_address),
                            ('active_configuration', '=', True)
                        ])
                        if email_digitization_config:
                            email_digi_data.write({
                                'email_digitization_config_id': email_digitization_config.id,
                            })
                            email_digi_data.model_id = email_digitization_config.model_id
                            email_digi_data.action_digitize()
                        else:
                            email_digi_data.write(
                                {'email_digitization_config_id': None})
        return res
