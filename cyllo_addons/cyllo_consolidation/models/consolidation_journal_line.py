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


class ConsolidationJournalLine(models.Model):
    """This model represents individual lines within consolidation journals,
    linking consolidated accounts with specific amounts and balances."""
    _name = 'consolidation.journal.line'
    _description = 'Consolidation Journal Line'

    journal_id = fields.Many2one(
        'consolidation.journal', string='Journal',
        help='Consolidation journal associated with this journal line')
    account_id = fields.Many2one(
        'consolidation.account', string='Consolidated Account',
        help='Consolidated account linked with this journal line')
    group_id = fields.Many2one(
        'consolidation.group', string='Group',
        help='Select the group associated with this consolidation account.')
    balance = fields.Monetary(help='Balance for this journal line')
    currency_id = fields.Many2one(
        'res.currency', related='journal_id.currency_id', string='Currency',
        help='Currency associated with the journal.')
