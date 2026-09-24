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


class ConsolidationJournal(models.Model):
    """This model represents journals used for consolidation purposes,
    containing journal lines for specific periods and companies."""
    _name = 'consolidation.journal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Consolidation Journal'

    name = fields.Char(required=True, help='Name of the consolidation journal')
    chart_id = fields.Many2one(
        'consolidation.chart', string='Consolidation',
        help='Associated consolidation chart')
    period_id = fields.Many2one(
        'consolidation.period', string="Periods",
        help='Period associated with this consolidation journal')
    company_id = fields.Many2one(
        'res.company', string="Company",
        help='Company associated with this consolidation journal')
    journal_line_ids = fields.One2many(
        'consolidation.journal.line', 'journal_id',
        help='Journal lines associated with this consolidation journal')
    total = fields.Monetary(
        compute='_compute_total', string='Total',
        help='Computed total balance based on journal lines.')
    currency_id = fields.Many2one(
        'res.currency', compute='_compute_currency_id',
        help='Currency ID computed based on the chart.')

    @api.depends('period_id')
    def _compute_currency_id(self):
        """Computes the currency ID for each record based on its chart."""
        for rec in self:
            rec.currency_id = rec.chart_id.currency_id.id

    @api.depends('journal_line_ids')
    def _compute_total(self):
        """Computes the total balance for each record based on its journal
        lines."""
        for rec in self:
            rec.total = sum(rec.journal_line_ids.mapped('balance'))
