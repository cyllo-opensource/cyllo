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
from datetime import datetime
import re

from odoo import _, api, models
from odoo.exceptions import UserError

FIELDS = ['name', 'move_name', 'date', 'amount_currency', 'account_id',
          'date_maturity', 'currency_id', 'debit', 'credit', 'move_id', 'annotations', 'partner_id']
PARTNER_LIMIT = 50
MOVE_LINE_LIMIT = 100
UNKNOWN_PARTNER_ID = 0

# Compute the residual at the selected report date. ``amount_residual`` is the
# current residual and incorrectly applies payments reconciled after that date.
OUTSTANDING = ("(line.balance - COALESCE(partial_debit.amount, 0.0) "
               "+ COALESCE(partial_credit.amount, 0.0))")
PARTIAL_RECONCILE_JOINS = """
    LEFT JOIN LATERAL (
        SELECT SUM(partial.amount) AS amount
        FROM account_partial_reconcile partial
        WHERE partial.debit_move_id = line.id AND partial.max_date <= %(date)s
    ) partial_debit ON TRUE
    LEFT JOIN LATERAL (
        SELECT SUM(partial.amount) AS amount
        FROM account_partial_reconcile partial
        WHERE partial.credit_move_id = line.id AND partial.max_date <= %(date)s
    ) partial_credit ON TRUE
"""

# These are the six inclusive due-date periods used by Odoo 17's aged-partner
# report.  Keeping the conditions in due-date form (rather than mixing them
# with ``AGE`` intervals) avoids calendar-month edge cases and leaves no gaps
# or overlaps between adjacent buckets.
AGE_PERIOD_CONDITIONS = (
    "COALESCE(line.date_maturity, line.date) >= %(date)s",
    "COALESCE(line.date_maturity, line.date) BETWEEN %(date)s - 30 AND %(date)s - 1",
    "COALESCE(line.date_maturity, line.date) BETWEEN %(date)s - 60 AND %(date)s - 31",
    "COALESCE(line.date_maturity, line.date) BETWEEN %(date)s - 90 AND %(date)s - 61",
    "COALESCE(line.date_maturity, line.date) BETWEEN %(date)s - 120 AND %(date)s - 91",
    "COALESCE(line.date_maturity, line.date) <= %(date)s - 121",
)


class AgePayableReceivableReport(models.AbstractModel):
    """Model for generating Aged Payable Receivable Report.

    Aging is bucketed on the balance outstanding at the selected report date.
    Partial reconciliations dated after that cut-off are not applied, so a
    partially paid line shows only its historical residual and fully settled
    lines do not appear as outstanding.
    """
    _name = 'aged.payable.receivable.report'
    _description = 'Aged Payable Receivable Report'

    @api.model
    def get_report(self, account_type=None, offset=0, limit=PARTNER_LIMIT, **filter_kwargs):
        """Generate the aged payable/receivable report.

        The page's partners get their totals from a single grouped query and
        their detail lines from a single windowed query (capped per partner);
        the grand total covers ALL matching partners, not just the page.

        :param str account_type: The account type(s).
        :param int offset: Partner pagination offset.
        :param int limit: Partner pagination limit.
        :param dict filter_kwargs: date, partners, company_ids, is_report.
        :return: Dictionary containing report values.
        :rtype: dict
        """
        is_report = filter_kwargs.get('is_report', False)
        if not filter_kwargs.get('date'):
            raise UserError(_("Please select a date to generate the report."))
        currency_id = self.env.company.currency_id.symbol

        partner_data = self.get_partners(account_type, **filter_kwargs)
        partners_dict = partner_data if is_report else partner_data[offset:offset + limit]
        page_partner_ids = [partner['id'] for partner in partners_dict]

        totals_by_partner = self._get_partners_ml_totals(page_partner_ids, account_type, **filter_kwargs)
        lines_by_partner = self._get_partners_move_lines(page_partner_ids, account_type, **filter_kwargs)

        partner_totals = []
        for partner in partners_dict:
            partner_id = partner['id']
            totals = totals_by_partner.get(partner_id, {})
            partner_totals.append({
                **totals,
                'move_lines': lines_by_partner.get(partner_id, []),
                'move_lines_count': totals.get('move_lines_count', 0),
                'currency_id': currency_id,
                'partner': partner['name'],
                'partner_id': partner_id,
            })

        all_partner_ids = [partner['id'] for partner in partner_data]
        grand_total = self.get_grand_total(all_partner_ids, account_type, **filter_kwargs)
        grand_total['currency'] = currency_id

        return {
            'partner_totals': partner_totals,
            'grand_total': grand_total,
            'partners': partners_dict if is_report else all_partner_ids,
        }

    @staticmethod
    def _as_tuple(value):
        """Normalize a scalar or list/tuple into a tuple for safe use with SQL
        ``IN %(param)s`` regardless of how the caller passed it in.
        """
        if isinstance(value, (list, tuple, set)):
            return tuple(value)
        return (value,)

    def _company_tuple(self, filter_kwargs):
        """Company ids as a tuple, defaulting to the current company so the
        ``IN %s`` clause can never become ``IN ()``."""
        return tuple(filter_kwargs.get('company_ids') or self.env.companies.ids)

    def _get_currency_table(self, filter_kwargs, date):
        """Return Odoo's multi-company conversion table for this report.

        ``account_move_line.balance`` and partial reconciliation amounts are in
        the line's company currency.  The standard Odoo reporting engine
        converts each company amount to the current/report company currency at
        the report date *before* it aggregates rows.  Keeping that conversion
        in SQL also preserves Odoo's per-line report-currency rounding.
        """
        return self.env['res.currency']._get_query_currency_table(
            self._company_tuple(filter_kwargs), date,
        )

    def _round_report_amount(self, amount):
        """Serialize report totals at the report currency's precision.

        The currency table performs the conversion and per-line rounding.  A
        final report-currency round prevents Python float serialization from
        exposing a residual fraction after SQL aggregation.
        """
        return self.env.company.currency_id.round(float(amount or 0.0))

    @staticmethod
    def _partner_sort_key(partner):
        name = (partner['name'] or '').strip().casefold()
        natural = tuple((0, int(part)) if part.isdigit() else (1, part)
                        for part in re.split(r'(\d+)', name))
        return (partner['id'] == UNKNOWN_PARTNER_ID,
                0 if name and not name[0].isalpha() else 1, natural)

    @property
    def _line_columns(self):
        """Per-line SELECT columns shared by the detail queries (single-partner
        pager and the windowed page query)."""
        return f"""
                line.id,
                line.name,
                line.move_name,
                line.date_maturity,
                line.date,
                line.amount_currency,
                {OUTSTANDING},
                account.name as account_name,
                account.code as account_code,
                currency.name as amount_currency_name,
                currency.symbol as amount_currency_symbol,
                line.debit,
                line.credit,
                line.move_id,
                line.annotations,
                COALESCE(line.partner_id, 0) AS partner_id,
                line.company_id,
                CASE WHEN {AGE_PERIOD_CONDITIONS[0]}
                     THEN {OUTSTANDING} ELSE 0.0 END AS diff0,
                CASE WHEN {AGE_PERIOD_CONDITIONS[1]}
                     THEN {OUTSTANDING} ELSE 0.0 END AS diff1,
                CASE WHEN {AGE_PERIOD_CONDITIONS[2]}
                     THEN {OUTSTANDING} ELSE 0.0 END AS diff2,
                CASE WHEN {AGE_PERIOD_CONDITIONS[3]}
                     THEN {OUTSTANDING} ELSE 0.0 END AS diff3,
                CASE WHEN {AGE_PERIOD_CONDITIONS[4]}
                     THEN {OUTSTANDING} ELSE 0.0 END AS diff4,
                CASE WHEN {AGE_PERIOD_CONDITIONS[5]}
                     THEN {OUTSTANDING} ELSE 0.0 END AS diff5"""

    @property
    def _line_source(self):
        """Shared FROM + WHERE for the detail queries. Placeholders:
        ``account_type``, ``date``, ``partner_ids``, ``company_ids``."""
        return f"""
            FROM account_move_line as line
            INNER JOIN account_account as account
                ON account.id = line.account_id AND account.account_type IN %(account_type)s
            LEFT JOIN res_currency as currency ON currency.id = line.currency_id
            INNER JOIN account_move as move ON move.id = line.move_id
            {PARTIAL_RECONCILE_JOINS}
            WHERE line.parent_state = 'posted'
              AND {OUTSTANDING} != 0
              AND line.date <= %(date)s
              AND COALESCE(line.partner_id, 0) IN %(partner_ids)s
              AND line.company_id IN %(company_ids)s"""

    @api.model
    def get_partner_move_lines(self, partner_id=None, account_type=None, offset=0, limit=MOVE_LINE_LIMIT,
                               **filter_kwargs):
        """Detail move lines for a single partner (used by the per-partner line
        pager). ``partner_id`` may be a single id or, on the pager path, the
        selected partner passed via ``filter_kwargs['partners']``.
        """
        date = datetime.strptime(filter_kwargs.get('date'), "%Y-%m-%d").date()
        is_pagination = False
        if not partner_id:
            is_pagination = True
            partner_id = filter_kwargs.get('partners', None)
        query = f"""
            SELECT {self._line_columns}
            {self._line_source}
            ORDER BY line.date
        """
        if is_pagination:
            query += " OFFSET %(offset)s LIMIT %(limit)s"
        params = {'date': date, 'partner_ids': self._as_tuple(partner_id),
                  'account_type': self._as_tuple(account_type),
                  'company_ids': self._company_tuple(filter_kwargs),
                  'offset': offset, 'limit': limit}
        active_company = self.env.company
        active_currency = active_company.currency_id
        companies = {comp.id: comp for comp in self.env['res.company'].sudo().search([])}
        self.env.cr.execute(query, params)
        lines = self.env.cr.dictfetchall()
        for row in lines:
            c_id = row['company_id']
            comp = companies.get(c_id)
            if comp:
                for col in ['diff0', 'diff1', 'diff2', 'diff3', 'diff4', 'diff5']:
                    val = float(row.get(col) or 0.0)
                    if val:
                        converted_abs = comp.currency_id._convert(abs(val), active_currency, active_company, date)
                        row[col] = -converted_abs if val < 0 else converted_abs
        return lines

    def _get_partners_move_lines(self, partner_ids, account_type, **filter_kwargs):
        """Detail lines for all page partners in one windowed query, capped at
        MOVE_LINE_LIMIT lines per partner for the interactive view; exports
        (is_report) fetch every line. Returns ``{partner_id: [lines]}``.
        """
        if not partner_ids:
            return {}
        is_report = filter_kwargs.get('is_report', False)
        date = datetime.strptime(filter_kwargs.get('date'), "%Y-%m-%d").date()
        cap_clause = "" if is_report else " WHERE sub.rn <= %(cap)s"
        query = f"""
            SELECT * FROM (
                SELECT {self._line_columns},
                       ROW_NUMBER() OVER (PARTITION BY line.partner_id
                                          ORDER BY line.date, line.id) AS rn
                {self._line_source}
            ) sub
            {cap_clause}
            ORDER BY sub.partner_id, sub.rn
        """
        params = {'date': date, 'partner_ids': tuple(partner_ids),
                  'account_type': self._as_tuple(account_type),
                  'company_ids': self._company_tuple(filter_kwargs),
                  'cap': MOVE_LINE_LIMIT}
        active_company = self.env.company
        active_currency = active_company.currency_id
        companies = {comp.id: comp for comp in self.env['res.company'].sudo().search([])}
        self.env.cr.execute(query, params)
        lines_by_partner = {}
        for row in self.env.cr.dictfetchall():
            c_id = row['company_id']
            comp = companies.get(c_id)
            if comp:
                for col in ['diff0', 'diff1', 'diff2', 'diff3', 'diff4', 'diff5']:
                    val = float(row.get(col) or 0.0)
                    if val:
                        converted_abs = comp.currency_id._convert(abs(val), active_currency, active_company, date)
                        row[col] = -converted_abs if val < 0 else converted_abs
            lines_by_partner.setdefault(row['partner_id'], []).append(row)
        return lines_by_partner

    def get_partners(self, account_type, **filter_kwargs):
        """Distinct partner buckets with an open balance as of the report date.

        This intentionally uses the exact same as-of residual expression and
        partial-reconciliation joins as the detail and total queries.  Using
        ``amount_residual`` here would use today's balance, while omitting the
        joins would both exclude historical open lines and make this query
        invalid once the residual is calculated from partial reconciliations.
        """
        date = datetime.strptime(filter_kwargs.get('date'), "%Y-%m-%d").date()
        partners = filter_kwargs.get('partners', [])
        query = f"""
            SELECT DISTINCT COALESCE(line.partner_id, {UNKNOWN_PARTNER_ID}) AS id,
                   COALESCE(partner.name, %(unknown_partner)s) AS name
            FROM account_move_line as line
            LEFT JOIN res_partner as partner ON line.partner_id = partner.id
            INNER JOIN account_account as account ON account.id = line.account_id
            INNER JOIN account_move as move ON move.id = line.move_id
            {PARTIAL_RECONCILE_JOINS}
            WHERE line.parent_state = 'posted'
              AND {OUTSTANDING} != 0
              AND account.account_type IN %(account_type)s
              AND line.date <= %(date)s
              AND line.company_id IN %(company_ids)s
        """
        if partners:
            query += " AND partner.id in %(partners)s"
        params = {'date': date, 'account_type': self._as_tuple(account_type),
                  'partners': tuple(partners), 'company_ids': self._company_tuple(filter_kwargs)}
        params['unknown_partner'] = _("Unknown Partner")
        self.env.cr.execute(query, params)
        return sorted(self.env.cr.dictfetchall(), key=self._partner_sort_key)

    def _get_partners_ml_totals(self, partner_ids, account_type, **filter_kwargs):
        """Per-partner aging-bucket totals, sub_total and line count in one
        grouped query. Returns ``{partner_id: {...}}``.
        """
        if not partner_ids:
            return {}
        date = datetime.strptime(filter_kwargs.get('date'), "%Y-%m-%d").date()
        currency_table = self._get_currency_table(filter_kwargs, date)
        query = self._get_total_query.replace(
            "SELECT", f"SELECT COALESCE(line.partner_id, {UNKNOWN_PARTNER_ID}) AS partner_id,", 1)
        query += f"""
                  SUM(ROUND(({OUTSTANDING}) * currency_table.rate,
                            currency_table.precision)) AS sub_total,
                  COUNT(*) AS move_lines_count
              FROM account_move_line as line
              INNER JOIN account_account as account
                  ON account.id = line.account_id AND account.account_type IN %(account_type)s
              INNER JOIN account_move as move ON move.id = line.move_id
              JOIN {currency_table} ON currency_table.company_id = line.company_id
              {PARTIAL_RECONCILE_JOINS}
              WHERE line.parent_state = 'posted'
                AND {OUTSTANDING} != 0
                AND line.date <= %(date)s
                AND COALESCE(line.partner_id, {UNKNOWN_PARTNER_ID}) IN %(partner_ids)s
                AND line.company_id IN %(company_ids)s
              GROUP BY COALESCE(line.partner_id, {UNKNOWN_PARTNER_ID})
        """
        params = {'date': date, 'partner_ids': tuple(partner_ids),
                  'account_type': self._as_tuple(account_type),
                  'company_ids': self._company_tuple(filter_kwargs)}
        self.env.cr.execute(query, params)
        totals_by_partner = {}
        for row in self.env.cr.dictfetchall():
            p_id = row['partner_id']
            if p_id not in totals_by_partner:
                totals_by_partner[p_id] = {
                    'diff0_sum': 0.0, 'diff1_sum': 0.0, 'diff2_sum': 0.0, 'diff3_sum': 0.0,
                    'diff4_sum': 0.0, 'diff5_sum': 0.0, 'sub_total': 0.0, 'move_lines_count': 0,
                    'partner_id': p_id
                }
            for col in ['diff0_sum', 'diff1_sum', 'diff2_sum', 'diff3_sum', 'diff4_sum', 'diff5_sum', 'sub_total']:
                totals_by_partner[p_id][col] = self._round_report_amount(
                    totals_by_partner[p_id][col] + float(row[col] or 0.0)
                )
            totals_by_partner[p_id]['move_lines_count'] += row['move_lines_count']
        return totals_by_partner

    def get_grand_total(self, partner_ids, account_type, **filter_kwargs):
        """Grand total of the aging buckets across the given partners."""
        if not partner_ids:
            return {
                'diff0_sum': 0.0, 'diff1_sum': 0.0, 'diff2_sum': 0.0,
                'diff3_sum': 0.0, 'diff4_sum': 0.0, 'diff5_sum': 0.0, 'total': 0.0,
            }
        date = datetime.strptime(filter_kwargs.get('date'), "%Y-%m-%d").date()
        currency_table = self._get_currency_table(filter_kwargs, date)
        query = self._get_total_query
        query += f"""
                  SUM(ROUND(({OUTSTANDING}) * currency_table.rate,
                            currency_table.precision)) AS total
              FROM account_move_line as line
              INNER JOIN account_account as account
                  ON account.id = line.account_id AND account.account_type IN %(account_type)s
              INNER JOIN account_move as move ON move.id = line.move_id
              JOIN {currency_table} ON currency_table.company_id = line.company_id
              {PARTIAL_RECONCILE_JOINS}
              WHERE line.parent_state = 'posted'
                AND {OUTSTANDING} != 0
                AND line.date <= %(date)s
                AND COALESCE(line.partner_id, {UNKNOWN_PARTNER_ID}) IN %(partner_id)s
                AND line.company_id IN %(company_ids)s
        """
        params = {'date': date, 'partner_id': tuple(partner_ids),
                  'account_type': self._as_tuple(account_type),
                  'company_ids': self._company_tuple(filter_kwargs)}
        self.env.cr.execute(query, params)

        grand = {'diff0_sum': 0.0, 'diff1_sum': 0.0, 'diff2_sum': 0.0, 'diff3_sum': 0.0,
                 'diff4_sum': 0.0, 'diff5_sum': 0.0, 'total': 0.0}

        for row in self.env.cr.dictfetchall():
            for col in ['diff0_sum', 'diff1_sum', 'diff2_sum', 'diff3_sum', 'diff4_sum', 'diff5_sum', 'total']:
                grand[col] = self._round_report_amount(grand[col] + float(row[col] or 0.0))

        return grand

    @property
    def _get_total_query(self):
        """Base SELECT with the six aging-bucket SUM columns (shared by the
        per-partner totals and the grand total)."""
        return f"""
            SELECT
              SUM(ROUND((CASE WHEN {AGE_PERIOD_CONDITIONS[0]}
                       THEN {OUTSTANDING} ELSE 0.0 END) * currency_table.rate,
                        currency_table.precision)) AS diff0_sum,
              SUM(ROUND((CASE WHEN {AGE_PERIOD_CONDITIONS[1]}
                       THEN {OUTSTANDING} ELSE 0.0 END) * currency_table.rate,
                        currency_table.precision)) AS diff1_sum,
              SUM(ROUND((CASE WHEN {AGE_PERIOD_CONDITIONS[2]}
                       THEN {OUTSTANDING} ELSE 0.0 END) * currency_table.rate,
                        currency_table.precision)) AS diff2_sum,
              SUM(ROUND((CASE WHEN {AGE_PERIOD_CONDITIONS[3]}
                       THEN {OUTSTANDING} ELSE 0.0 END) * currency_table.rate,
                        currency_table.precision)) AS diff3_sum,
              SUM(ROUND((CASE WHEN {AGE_PERIOD_CONDITIONS[4]}
                       THEN {OUTSTANDING} ELSE 0.0 END) * currency_table.rate,
                        currency_table.precision)) AS diff4_sum,
              SUM(ROUND((CASE WHEN {AGE_PERIOD_CONDITIONS[5]}
                       THEN {OUTSTANDING} ELSE 0.0 END) * currency_table.rate,
                        currency_table.precision)) AS diff5_sum,
        """
