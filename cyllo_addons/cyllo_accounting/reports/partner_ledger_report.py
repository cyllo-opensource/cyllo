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
from odoo import _, api, models
from odoo.exceptions import UserError

PARTNER_LIMIT = 50
MOVE_LINE_LIMIT = 100


class PartnerLedgerReport(models.AbstractModel):
    """
        This model for generating the Partner Ledger Report.
    """
    _name = 'partner.ledger.report'
    _description = 'Partner Ledger Report'

    def _format_currency(self, amount, currency):
        if currency.position == 'before':
            return f"{currency.symbol} {amount:,.2f}"
        return f"{amount:,.2f} {currency.symbol}"

    @api.model
    def get_partner(self, start_date=None, end_date=None, company_id=None):
        """Return the ids of partners that have posted receivable/payable entries
        within the selected period.

        Aggregated in SQL (read_group) instead of loading every matching move
        line into memory, and bounded by date/company so the partner picker
        follows the selected range.
        """
        domain = [('account_type', 'in', ['liability_payable', 'asset_receivable']),
                  ('parent_state', '=', 'posted'), ('partner_id', '!=', False)]
        if start_date:
            domain.append(('date', '>=', start_date))
        if end_date:
            domain.append(('date', '<=', end_date))
        if company_id:
            domain.append(('company_id', 'in', company_id))
        groups = self.env['account.move.line'].read_group(
            domain, ['partner_id'], ['partner_id'])
        return [group['partner_id'][0] for group in groups]

    @api.model
    def get_report(self, offset=0, limit=PARTNER_LIMIT, **kwargs):
        """
        Retrieve partner-related data for the report.

        The interactive page uses a handful of queries: the partner ids for the
        page, one grouped totals query, and one windowed detail query (capped at
        ``MOVE_LINE_LIMIT`` lines per partner). ``pager=True`` returns a single
        partner's detail lines for line-level pagination. Every user-supplied
        value is passed as a query parameter.

        Returns:
            tuple(dict, list): (partner data keyed by id + totals, all partner ids).
        """
        partner_id = kwargs.get('partner_id') or []
        is_report = kwargs.get('is_report', False)
        pager = kwargs.get('pager', False)
        company_ids = kwargs.get('company_id', []) or self.env.company.ids
        domain = self.get_domain(**kwargs)
        if not domain['startDate'] or not domain['endDate']:
            raise UserError(_(
                "Please select both a start date and an end date to "
                "generate the report."))

        filter_clause = (" AND move_line.parent_state IN %s"
                         " AND move_line.date >= %s AND move_line.date <= %s"
                         " AND account.account_type IN %s"
                         " AND move_line.company_id IN %s")
        filter_params = [domain['parent_state_domain'], domain['startDate'],
                         domain['endDate'], domain['account_type'], tuple(company_ids)]
        currency_id = self.env.company.currency_id.symbol

        detail_from = """
            FROM account_move_line move_line
                INNER JOIN res_partner partner ON move_line.partner_id = partner.id
                INNER JOIN account_account account ON move_line.account_id = account.id
                INNER JOIN account_journal journal ON move_line.journal_id = journal.id"""
        detail_columns = """
            move_line.id AS id, move_line.date AS date, move_line.move_name AS move_name,
            account.account_type AS account_type, move_line.debit AS debit,
            move_line.credit AS credit, move_line.date_maturity AS date_maturity,
            move_line.account_id AS account_id, move_line.journal_id AS journal_id,
            move_line.partner_id AS partner_id, move_line.move_id AS move_id,
            move_line.company_id AS company_id,
            move_line.matching_number AS matching_number,
            move_line.amount_currency AS amount_currency,
            move_line.currency_id AS currency_id, move_line.annotations AS annotations,
            move_line.name AS name, journal.code AS jrnl, account.code AS code,
            partner.name AS partner_name"""

        active_company = self.env.company
        active_currency = active_company.currency_id
        companies = {comp.id: comp for comp in self.env['res.company'].sudo().search([])}
        currencies = {curr.id: curr for curr in self.env['res.currency'].sudo().search([])}

        if pager:
            single_partner = partner_id[0] if isinstance(partner_id, (list, tuple)) else partner_id
            opening = self._get_partner_openings(
                [single_partner], domain, company_ids).get(single_partner) or {}
            opening_net = (opening.get('opening_debit') or 0.0) - (opening.get('opening_credit') or 0.0)
            
            self.env.cr.execute(f"""
                SELECT move_line.debit, move_line.credit, move_line.company_id, move_line.date,
                       move_line.amount_currency, move_line.currency_id
                {detail_from}
                WHERE move_line.partner_id = %s {filter_clause}
                ORDER BY move_line.date, move_line.id
                LIMIT %s
            """, [single_partner] + filter_params + [offset])
            
            running_val = 0.0
            for row in self.env.cr.dictfetchall():
                comp = companies.get(row['company_id'])
                if not comp: continue
                
                debit = row['debit'] or 0.0
                credit = row['credit'] or 0.0
                
                if comp.currency_id != active_currency:
                    debit = comp.currency_id._convert(debit, active_currency, active_company, row['date'])
                    credit = comp.currency_id._convert(credit, active_currency, active_company, row['date'])
                    
                running_val += (debit - credit)
                
            running = opening_net + running_val
            
            self.env.cr.execute(f"""
                SELECT {detail_columns} {detail_from}
                WHERE move_line.partner_id = %s {filter_clause}
                ORDER BY move_line.date, move_line.id
                LIMIT %s OFFSET %s
            """, [single_partner] + filter_params + [limit, offset])
            lines = self.env.cr.dictfetchall()
            for line in lines:
                comp = companies.get(line['company_id'])
                if not comp: continue
                
                if comp.currency_id != active_currency:
                    line['debit'] = comp.currency_id._convert(line['debit'] or 0.0, active_currency, active_company, line['date'])
                    line['credit'] = comp.currency_id._convert(line['credit'] or 0.0, active_currency, active_company, line['date'])
                    
                running += (line['debit'] or 0.0) - (line['credit'] or 0.0)
                line['debit'] = active_currency.round(line['debit'] or 0.0)
                line['credit'] = active_currency.round(line['credit'] or 0.0)
                line['balance'] = active_currency.round(running)
                
                line['format_debit'] = self._format_currency(line['debit'], active_currency)
                line['format_credit'] = self._format_currency(line['credit'], active_currency)
                line['format_balance'] = self._format_currency(line['balance'], active_currency)
            return lines

        if partner_id:
            all_partner_ids = list(partner_id)
            page_partner_ids = all_partner_ids
        else:
            self.env.cr.execute(f"""
                SELECT DISTINCT move_line.partner_id
                FROM account_move_line move_line
                    INNER JOIN account_account account ON move_line.account_id = account.id
                WHERE move_line.partner_id IS NOT NULL {filter_clause}
            """, filter_params)
            all_partner_ids = [row[0] for row in self.env.cr.fetchall()]
            page_partner_ids = (all_partner_ids if is_report
                                else all_partner_ids[offset:offset + limit])

        partner_dict = {}
        partner_totals = {}
        total_debit_sum = 0
        total_credit_sum = 0
        if page_partner_ids:
            page_tuple = tuple(page_partner_ids)
            partner_names = {
                partner.id: partner.name
                for partner in self.env['res.partner'].browse(page_partner_ids)}
            openings = self._get_partner_openings(page_partner_ids, domain, company_ids)

            self.env.cr.execute(f"""
                SELECT move_line.partner_id AS partner_id, COUNT(*) AS count
                FROM account_move_line move_line
                    INNER JOIN account_account account ON move_line.account_id = account.id
                WHERE move_line.partner_id IN %s {filter_clause}
                GROUP BY move_line.partner_id
            """, [page_tuple] + filter_params)
            counts_by_partner = {row['partner_id']: row['count'] for row in self.env.cr.dictfetchall()}

            self.env.cr.execute(f"""
                SELECT move_line.partner_id AS partner_id, move_line.company_id, move_line.date,
                       move_line.debit, move_line.credit, move_line.amount_currency, move_line.currency_id
                FROM account_move_line move_line
                    INNER JOIN account_account account ON move_line.account_id = account.id
                WHERE move_line.partner_id IN %s {filter_clause}
            """, [page_tuple] + filter_params)
            totals_by_partner = {}
            for row in self.env.cr.dictfetchall():
                p_id = row['partner_id']
                comp = companies.get(row['company_id'])
                if not comp: continue
                debit = row['debit'] or 0.0
                credit = row['credit'] or 0.0
                
                if comp.currency_id != active_currency:
                    debit = comp.currency_id._convert(debit, active_currency, active_company, row['date'])
                    credit = comp.currency_id._convert(credit, active_currency, active_company, row['date'])
                    
                if p_id not in totals_by_partner:
                    totals_by_partner[p_id] = {'total_debit': 0.0, 'total_credit': 0.0, 'move_lines_count': counts_by_partner.get(p_id, 0)}
                totals_by_partner[p_id]['total_debit'] += debit
                totals_by_partner[p_id]['total_credit'] += credit

            detail_params = [page_tuple] + filter_params
            cap_clause = ""
            if not is_report:
                cap_clause = " WHERE sub.rn <= %s"
                detail_params = detail_params + [MOVE_LINE_LIMIT]
            self.env.cr.execute(f"""
                SELECT * FROM (
                    SELECT {detail_columns},
                           ROW_NUMBER() OVER (PARTITION BY move_line.partner_id
                                              ORDER BY move_line.date, move_line.id) AS rn
                    {detail_from}
                    WHERE move_line.partner_id IN %s {filter_clause}
                ) sub
                {cap_clause}
                ORDER BY sub.partner_id, sub.rn
            """, detail_params)
            detail_by_partner = {}
            for row in self.env.cr.dictfetchall():
                detail_by_partner.setdefault(row['partner_id'], []).append(row)

            for partner in page_partner_ids:
                detail = detail_by_partner.get(partner, [])
                totals = totals_by_partner.get(partner) or {}
                opening = openings.get(partner) or {}
                opening_debit = round(opening.get('opening_debit') or 0, 2)
                opening_credit = round(opening.get('opening_credit') or 0, 2)
                opening_net = opening_debit - opening_credit
                period_debit = totals.get('total_debit') or 0
                period_credit = totals.get('total_credit') or 0
                total_debit = round(opening_debit + period_debit, 2)
                total_credit = round(opening_credit + period_credit, 2)
                running = opening_net
                for line in detail:
                    comp = companies.get(line['company_id'])
                    if not comp: continue
                    if comp.currency_id != active_currency:
                        line['debit'] = comp.currency_id._convert(line['debit'] or 0.0, active_currency, active_company, line['date'])
                        line['credit'] = comp.currency_id._convert(line['credit'] or 0.0, active_currency, active_company, line['date'])
                    
                    running += (line['debit'] or 0.0) - (line['credit'] or 0.0)
                    line['debit'] = active_currency.round(line['debit'] or 0.0)
                    line['credit'] = active_currency.round(line['credit'] or 0.0)
                    line['balance'] = active_currency.round(running)
                    
                    line['format_debit'] = self._format_currency(line['debit'], active_currency)
                    line['format_credit'] = self._format_currency(line['credit'], active_currency)
                    line['format_balance'] = self._format_currency(line['balance'], active_currency)
                    
                partner_dict[partner] = detail
                partner_totals[partner] = {
                    'total_debit': total_debit,
                    'total_credit': total_credit,
                    'opening_debit': opening_debit,
                    'opening_credit': opening_credit,
                    'opening_balance': active_currency.round(opening_net),
                    'format_total_debit': self._format_currency(total_debit, active_currency),
                    'format_total_credit': self._format_currency(total_credit, active_currency),
                    'format_opening_debit': self._format_currency(opening_debit, active_currency),
                    'format_opening_credit': self._format_currency(opening_credit, active_currency),
                    'format_opening_balance': self._format_currency(opening_net, active_currency),
                    'format_balance': self._format_currency(total_debit - total_credit + opening_net, active_currency),
                    'currency_id': currency_id,
                    'partner_id': partner,
                    'partner_name': partner_names.get(partner),
                    'move_lines': detail,
                    'move_lines_count': totals.get('move_lines_count') or 0,
                }
                total_debit_sum += total_debit
                total_credit_sum += total_credit

        partner_dict['partner_totals'] = partner_totals
        partner_dict['totalDebitSum'] = active_currency.round(total_debit_sum)
        partner_dict['totalCreditSum'] = active_currency.round(total_credit_sum)
        partner_dict['format_totalDebitSum'] = self._format_currency(total_debit_sum, active_currency)
        partner_dict['format_totalCreditSum'] = self._format_currency(total_credit_sum, active_currency)
        partner_dict['format_totalBalanceSum'] = self._format_currency(total_debit_sum - total_credit_sum, active_currency)
        partner_dict['currency_id'] = currency_id
        return partner_dict, all_partner_ids

    def _get_partner_openings(self, partner_ids, domain, company_ids):
        """Gross debit/credit of the AR/AP lines brought forward before the
        period start (cumulative from inception), per partner.

        AR/AP are balance-sheet accounts, so the opening carries across years
        with no fiscal-year reset.

        Returns:
            dict: ``{partner_id: {opening_debit, opening_credit}}``.
        """
        if not partner_ids:
            return {}
        active_company = self.env.company
        active_currency = active_company.currency_id
        companies = {comp.id: comp for comp in self.env['res.company'].sudo().search([])}
        currencies = {curr.id: curr for curr in self.env['res.currency'].sudo().search([])}

        self.env.cr.execute("""
            SELECT move_line.partner_id AS partner_id, move_line.company_id, move_line.date,
                   move_line.debit, move_line.credit, move_line.amount_currency, move_line.currency_id
            FROM account_move_line move_line
                INNER JOIN account_account account ON account.id = move_line.account_id
            WHERE move_line.partner_id IN %s
              AND move_line.parent_state IN %s
              AND move_line.date < %s
              AND account.account_type IN %s
              AND move_line.company_id IN %s
        """, (tuple(partner_ids), domain['parent_state_domain'], domain['startDate'],
              domain['account_type'], tuple(company_ids)))
        openings = {}
        for row in self.env.cr.dictfetchall():
            p_id = row['partner_id']
            comp = companies.get(row['company_id'])
            if not comp: continue
            debit = row['debit'] or 0.0
            credit = row['credit'] or 0.0
            
            if comp.currency_id != active_currency:
                debit = comp.currency_id._convert(debit, active_currency, active_company, row['date'])
                credit = comp.currency_id._convert(credit, active_currency, active_company, row['date'])
                
            if p_id not in openings:
                openings[p_id] = {'opening_debit': 0.0, 'opening_credit': 0.0}
            openings[p_id]['opening_debit'] += debit
            openings[p_id]['opening_credit'] += credit
        return openings

    @staticmethod
    def get_domain(**kwargs):
        """Date Domain"""
        startDate = kwargs.get('startDate', None)
        endDate = kwargs.get('endDate', None)
        parent_state = kwargs.get('parent_state') or None
        account = kwargs.get('account_type') or None
        account_type_domain = []
        parent_state_domain = ['posted'] if parent_state is None else ['posted',
                                                                       'draft'] if 'draft' in parent_state else [
            'posted']
        if account is None or ('Receivable' in account and 'Payable' in account):
            account_type_domain.extend(['liability_payable', 'asset_receivable'])
        elif 'Receivable' in account:
            account_type_domain.append('asset_receivable')
        elif 'Payable' in account:
            account_type_domain.append('liability_payable')
        domain = {
            'account_type': tuple(account_type_domain),
            'parent_state_domain': tuple(parent_state_domain),
            'startDate': startDate,
            'endDate': endDate
        }
        return domain
