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
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

DAYS_PER_MONTH = 30
DAYS_PER_YEAR = DAYS_PER_MONTH * 12


class AccountFiscalYear(models.Model):
    """For Account Fiscal Year """
    _name = "account.fiscal.year"
    _description = "Account Fiscal Year"

    name = fields.Char(string='Fiscal Year', required=True,help='Name for the fiscal year')
    start_date = fields.Date(required=True, help='Start date for the fiscal year')
    end_date = fields.Date(required=True, help='End date for the fiscal year')
    company_id = fields.Many2one('res.company', readonly=True, default=lambda self: self.env.company)
    state = fields.Selection(selection=[('draft', 'Draft'), ('open', 'Open'), ('close', 'Closed')], string='Status',
                             readonly=True, copy=False, default='draft',
                             help='Current state of the fiscal year')

    @api.constrains("start_date", "end_date", "company_id")
    def _check_start_date(self):
        """Check intersection with the existing fiscal years."""
        for fiscal_year in self:
            if fiscal_year.end_date < fiscal_year.start_date:
                raise UserError(_("The ending date must not be prior to the"
                                  " starting date."))
            domain = fiscal_year._get_domain()
            overlapping_fiscal_year = self.search(domain, limit=1)
            if overlapping_fiscal_year:
                raise UserError(
                    _("This fiscal year %s overlaps with %s.\n "
                      "Please correct the start and/or end dates of your "
                      "fiscal years.", fiscal_year.display_name,
                      overlapping_fiscal_year.display_name))

    def unlink(self):
        """OVERRIDE to unlink the record"""
        for rec in self:
            if rec.state == 'open':
                raise UserError(
                    _("You cannot delete a fiscal year in open state first "
                      "close the fiscal year.")
                )
        res = super().unlink()
        return res

    def action_reopen(self):
        """Button: Re-open the fiscal year"""
        self.ensure_one()
        self.write({'state': 'open'})

    def action_draft(self):
        """Button: Set to Draft"""
        self.ensure_one()
        self.write({'state': 'draft'})

    def action_open(self):
        """Button: Open the fiscal year"""
        for rec in self:
                rec.write({'state': 'open'})

    def action_close(self):
        """Button: return wizard for entire or partial fiscal close"""
        self.ensure_one()
        return {
            'name': (_('Close Fiscal Year %s') % self.name),
            'res_model': 'account.move.lock',
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('cyllo_accounting.view_account_move_lock_form').id, 'form')],
            'context': {
                'default_fiscal_year_id': self.id,
            },
            'target': 'new',
        }

    def _get_domain(self):
        """Get domain for finding fiscal years overlapping with self"""
        self.ensure_one()
        # Compare with other fiscal years defined for this company
        company_domain = [
            ("id", "!=", self.id),
            ("company_id", "=", self.company_id.id),
        ]
        start_date = self.start_date
        end_date = self.end_date
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
