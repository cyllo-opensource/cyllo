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


class MailActivity(models.Model):
    """Class to add new fields to res.partner"""
    _inherit = 'mail.activity'

    office_365_identifier = fields.Char(string="Contact id",
                                        help="Id to distinguish each activity imported from office 365")
    connector_ids = fields.Many2many('cyllo.office.connector',
                                     help="Connector of the activity")
    office_connectors_ids = fields.One2many('cyllo.office.connector.line',
                                            'activity_id',
                                            string="Connected Instances",
                                            help="List of synced instances")
