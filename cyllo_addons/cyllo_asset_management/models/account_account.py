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


class AccountAccount(models.Model):
    """Inheriting account.account for adding new functionalities"""
    _inherit = 'account.account'

    asset_creation = fields.Selection(
        [
            ('no', 'No'),
            ('draft', 'Draft'),
            ('validate', 'Validate')
        ],
        string='Asset Automation',
        default='no',
        help='For updating the bills',
    )
    multiple_asset = fields.Boolean(
        help='Multiple asset item will be generated depending on the bill line quantity'
    )
    asset_model_id = fields.Many2one(
        'asset.item',
        help='If the field is selected expense/revenue will created automatically when '
              'the journal item posted'
    )
