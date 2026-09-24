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
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaltedgeConnection(models.Model):
    """To store the values related to saltedge connections"""
    _name = "saltedge.connection"
    _description = "SaltEdge Connection"

    name = fields.Char('Provider Name', readonly=True, help='Name of the bank connection')
    bank_provider_id = fields.Many2one('online.bank.provider', string='Bank Provider', readonly=True,
                                       help='Corresponding online bank provider')
    connection_id = fields.Char('Connection Id', readonly=True, help='Connection id of the created connection')
    customer_id = fields.Char(related='bank_provider_id.saltedge_customer_id', string='Customer Id',
                              help='Customer id of the created connection')
    country_code = fields.Char('Country Code', readonly=True)
    status = fields.Char('Status', readonly=True)
