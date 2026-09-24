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


class ConsolidationCompanyPeriod(models.Model):
    """This model represents periods for consolidation within a company."""
    _name = 'consolidation.company.period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Consolidation Company Period'

    company_id = fields.Many2one(
        'res.company', readonly=True,
        help='The company associated with this consolidation period.')
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        help='The currency used by the company for consolidation.')
    period_id = fields.Many2one(
        'consolidation.period', string="Periods",
        help='The specific period associated with this consolidation entry.')
    consolidation_rate = fields.Float(
        string='Consolidation rate (%)', default='100',
        help='The percentage rate of consolidation for this period.')
    start_date = fields.Date(
        readonly=True, help='Start date of the consolidation period')
    end_date = fields.Date(
        readonly=True, help='End date of the consolidation period')

    def unlink(self):
        """
        Overrides the unlink method to ensure journals associated with the same
        company are unlinked when a ConsolidationCompanyPeriod record is deleted.
        Returns:
            bool: Result of the unlink operation from the super class.
        """
        for record in self:
            company = record.company_id
            journals = record.period_id.journal_ids.filtered(
                lambda journal: journal.company_id == company)
            # Unlink the filtered journals
            journals.unlink()
        return super(ConsolidationCompanyPeriod, self).unlink()
