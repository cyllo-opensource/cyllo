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
from datetime import date

from odoo import _, fields, models
from odoo.osv import expression
from odoo.exceptions import UserError


class FinancialYearOpeningWizard(models.TransientModel):
    """ Create fiscal year from the onboarding panel"""
    _inherit = 'account.financial.year.op'

    opening_date = fields.Date(string='Opening Date', required=True,
                               related='company_id.account_opening_date',
                               help="Date from which the accounting is managed in Cyllo. It is the date of the opening entry.",
                               readonly=False)


    def action_save_onboarding_fiscal_year(self):
        """Create fiscal year from onboarding panel of the dashboard"""
        res = super().action_save_onboarding_fiscal_year()
        if res != 'NOT_FOUND':
            start_date = self.opening_date
            end_month = int(self.fiscalyear_last_month)
            current_year = self.opening_date.year
            # Create the date object
            end_date = date(current_year+1, end_month, self.fiscalyear_last_day)
            overlapping_fiscal_year = self.env['account.fiscal.year'].search(self._get_domain(start_date, end_date), limit=1)
            if overlapping_fiscal_year:
                raise UserError(
                    _("This fiscal year will overlaps with %s.\n "
                      "Please correct the start and/or end dates of your "
                      "fiscal years.", overlapping_fiscal_year.display_name))
            else:
                new_fiscal_year = self.env['account.fiscal.year'].create({
                    'name': current_year,
                    'start_date': start_date,
                    'end_date': end_date,
                    'company_id': self.company_id.id
                })
        return res

    def _get_domain(self, start_date, end_date):
        """Get domain for finding fiscal years overlapping with the new"""
        self.ensure_one()
        # Compare with other fiscal years defined for this company
        company_domain = [
            ("company_id", "=", self.company_id.id),
        ]
        intersection_domain_from = [
            "&",
            ("start_date", "<=", start_date),
            ("end_date", ">=", start_date),
        ]
        intersection_domain_to = [
            "&",
            ("start_date", "<=", end_date),
            ("end_date", ">=", end_date),
        ]
        intersection_domain_contain = [
            "&",
            ("start_date", ">=", start_date),
            ("start_date", "<=", end_date),
        ]
        intersection_domain = expression.OR(
            [
                intersection_domain_from,
                intersection_domain_to,
                intersection_domain_contain,
            ]
        )
        return expression.AND(
            [
                company_domain,
                intersection_domain,
            ]
        )
