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
from odoo import fields, models, _


class AssetDepreciationLine(models.Model):
    """Model for asset depreciation lines"""
    _name = 'asset.depreciation.line'
    _description = 'Asset Depreciation Line'
    _order = 'date, accumulative_depreciation asc'

    depreciation_id = fields.Many2one(
        'asset.asset',
        help='Asset associated with this depreciation line.'
    )
    year = fields.Integer(
        help='Depreciation year or period sequence.'
    )
    date = fields.Date(
        help='Date on which the depreciation is recorded.'
    )
    is_depreciated = fields.Boolean(
        help='Indicates whether this depreciation line has been processed.'
    )
    depreciation_expense = fields.Float(
        help='Depreciation expense amount for the period.'
    )
    accumulative_depreciation = fields.Float(
        string='Accumulated Depreciation',
        digits=(12, 6),
        help='Total accumulated depreciation up to this period.'
    )
    salvage_value = fields.Float(
        string='Book Value at Year End',
        help='Remaining book value of the asset after depreciation.'
    )
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        help='Company associated with this depreciation line.'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        help='Currency used by the company.'
    )
    journal_reference = fields.Many2one('account.move',
        string='Journal Entry',
        help='Reference of the journal entry created for this depreciation.'
    )
