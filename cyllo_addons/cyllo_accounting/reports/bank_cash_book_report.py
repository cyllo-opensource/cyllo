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
from odoo import api, models

LIMIT = 100


class BankBookReport(models.AbstractModel):
    """
        This model for generating the Account Bank Book Report.
    """
    _name = 'bank.cash.book.report'
    _description = 'Account Bank/Cash Book Report'

    @api.model
    def get_partner(self, journal_type, start_date=None, end_date=None):
        """
        Get partner IDs that have posted entries in the given journal type,
        restricted to the selected date range.

        Args:
            journal_type (str): Type of journal.
            start_date (str, optional): Start of the period ('YYYY-MM-DD').
            end_date (str, optional): End of the period ('YYYY-MM-DD').

        Returns:
            list: Distinct partner IDs active within the period.
        """
        journal = self.env['account.journal'].search([('type', '=', journal_type)])
        domain = [('parent_state', '=', 'posted'), ('journal_id', 'in', journal.ids),
                  ('partner_id', '!=', False)]
        if start_date:
            domain.append(('date', '>=', start_date))
        if end_date:
            domain.append(('date', '<=', end_date))
        partner_groups = self.env['account.move.line'].read_group(
            domain, ['partner_id'], ['partner_id'])
        return [group['partner_id'][0] for group in partner_groups]

    @api.model
    def get_account_data(self, journal_type, **kwargs):
        """
        Get account data based on the specified journal type and optional filter criteria.

        Args:
            journal_type (str): Type of journal.
            **kwargs: Optional keyword arguments for additional filtering and configuration.
                - account_id (int, optional): ID of the account to filter by.
                - limit (int, optional): Maximum number of records to retrieve.
                - offset (int, optional): Offset for pagination.
                - account_name (str, optional): Name of the account to filter by.

        Returns:
            list: Account data based on the specified criteria.
        """
        account_id = kwargs.get('account_id', False)
        limit = kwargs.get('limit', LIMIT)
        offset = kwargs.get('offset', 0)
        account_name = kwargs.get('account_name', False)
        journals = self.env['account.journal'].search(
            [('type', '=', journal_type)])
        domain = self.get_domain(journals, **kwargs)
        return self._get_account_entries(
            account_id, domain, account_name, limit, offset,
            kwargs.get('company_ids'))

    def _get_account_entries(self, account_type_id, domain, account_name, limit=LIMIT, offset=0, company_ids=None):
        """
        Get account entries based on the specified account type ID and domain.

        Args:
            account_type_id (int): ID of the account type.
            domain (list): List of domain conditions for filtering account entries.
            account_name (str): Name of the account.
            limit (int, optional): Maximum number of records to retrieve. Defaults to LIMIT.
            offset (int, optional): Offset for pagination. Defaults to 0.

        Returns:
            tuple: A tuple containing:
                - list: Account entries based on the specified criteria.
                - float: Total debit amount for the account entries.
                - float: Total credit amount for the account entries.
                - float: Total balance (debit - credit) for the account entries.
                - dict: Information about the account entries including limit, offset, account ID, and total count.
        """
        new_domain = domain + [('account_id', '=', account_type_id)]
        account_entries_total = self.env['account.move.line'].search(new_domain)
        account_entries = self.env['account.move.line'].search_read(new_domain,
                                                                    ['date', 'journal_id', 'partner_id', 'move_name',
                                                                     'debit', 'annotations', 'account_id',
                                                                     'move_id', 'credit', 'name', 'ref', 'company_id'],
                                                            limit=limit, offset=offset)
        active_company = self.env.company
        active_currency = active_company.currency_id
        companies = {comp.id: comp for comp in self.env['res.company'].sudo().search([])}

        for entry in account_entries:
            date = entry['date']
            comp_id = entry['company_id'][0] if entry.get('company_id') else active_company.id
            comp = companies.get(comp_id)
            comp_currency = comp.currency_id if comp else active_currency

            debit = entry.get('debit', 0.0)
            credit = entry.get('credit', 0.0)

            if comp_currency != active_currency:
                if debit:
                    debit = comp_currency._convert(debit, active_currency, active_company, date)
                if credit:
                    credit = comp_currency._convert(credit, active_currency, active_company, date)

            entry['debit'] = active_currency.round(debit)
            entry['credit'] = active_currency.round(credit)
            entry['balance'] = active_currency.round(debit - credit)

        acc_total_debit = 0.0
        acc_total_credit = 0.0
        for entry in account_entries_total:
            date = entry.date
            comp = companies.get(entry.company_id.id)
            comp_currency = comp.currency_id if comp else active_currency

            debit = entry.debit
            credit = entry.credit

            if comp_currency != active_currency:
                if debit:
                    debit = comp_currency._convert(debit, active_currency, active_company, date)
                if credit:
                    credit = comp_currency._convert(credit, active_currency, active_company, date)

            acc_total_debit += debit
            acc_total_credit += credit

        acc_total_debit = active_currency.round(acc_total_debit)
        acc_total_credit = active_currency.round(acc_total_credit)
        acc_total_balance = active_currency.round(acc_total_debit - acc_total_credit)
        return account_entries, acc_total_debit, acc_total_credit, acc_total_balance, {
            account_name: {"limit": limit, "offset": offset, "account_id": account_type_id,
                           "total": len(
                               account_entries_total)}}

    def get_domain(self, journals, **filter_kwargs):
        """
            Construct a domain based on the provided journals and optional filter criteria.

            Args:
                journals (recordset): Recordset of account journals.
                **filter_kwargs: Optional keyword arguments for additional filtering and configuration.

            Returns:
                list: A list representing the domain for search queries.
        """
        startDate = filter_kwargs.get('startDate', None)
        endDate = filter_kwargs.get('endDate', None)
        partners = filter_kwargs.get('partners', [])
        accounts = filter_kwargs.get('accounts', [])
        parent_state = filter_kwargs.get('parent_state')
        domain = [('journal_id', 'in', journals.ids)]
        company_ids = filter_kwargs.get('company_ids')
        if company_ids:
            domain.append(('company_id', 'in', company_ids))
        if parent_state:
            domain.append(('parent_state', 'in', parent_state))
        if accounts:
            domain.append(('account_id', 'in', accounts))
        if partners:
            domain.append(('partner_id', 'in', partners))
        if startDate and endDate:
            domain.extend([('date', '>=', startDate),
                           ('date', '<=', endDate)])
        elif startDate:
            domain.extend([('date', '>=', startDate)])
        elif endDate:
            domain.extend([('date', '<=', endDate)])
        return domain

    @api.model
    def get_report(self, journal_type, **filter_kwargs):
        """
            Get a report based on the specified journal type and optional filter criteria.

            Args:
                journal_type (str): Type of journal.
                **filter_kwargs: Optional keyword arguments for additional filtering and configuration.

            Returns:
                dict: A dictionary containing various data for the report including account details,
                      total debit, total credit, total balance, account entries, and currency ID.
        """
        data = {}
        journals = self.env['account.journal'].search(
            [('type', '=', journal_type)])
        domain = self.get_domain(journals, **filter_kwargs)
        account_move_lines = self.env['account.move.line'].search(domain, order="date desc")
        all_account_domain = [('parent_state', '=', 'posted'),
                              ('journal_id', 'in', journals.ids)]
        if filter_kwargs.get('startDate'):
            all_account_domain.append(('date', '>=', filter_kwargs['startDate']))
        if filter_kwargs.get('endDate'):
            all_account_domain.append(('date', '<=', filter_kwargs['endDate']))
        all_account_groups = self.env['account.move.line'].read_group(
            all_account_domain, ['account_id'], ['account_id'])
        all_account_ids = [group['account_id'][0] for group in all_account_groups
                           if group['account_id']]
        data['accounts'] = account_move_lines.mapped('account_id').read(
            ['display_name', 'name'])
        data['all_account'] = self.env['account.account'].browse(all_account_ids).read(
            ['display_name', 'name'])

        company_ids = filter_kwargs.get('company_ids', [])
        active_company = self.env.company
        active_currency = active_company.currency_id
        companies = {comp.id: comp for comp in self.env['res.company'].sudo().search([])}
        selected_company_ids = company_ids or self.env.companies.ids
        has_multiple_currencies = len(
            self.env['res.company'].browse(selected_company_ids).mapped(
                'currency_id')) > 1

        total_debit = 0.0
        total_credit = 0.0

        for entry in account_move_lines:
            date = entry.date
            comp = companies.get(entry.company_id.id)
            comp_currency = comp.currency_id if comp else active_currency

            debit = entry.debit
            credit = entry.credit

            if comp_currency != active_currency:
                if debit:
                    debit = comp_currency._convert(debit, active_currency, active_company, date)
                if credit:
                    credit = comp_currency._convert(credit, active_currency, active_company, date)

            total_debit += debit
            total_credit += credit

        if has_multiple_currencies:
            data['total_debit'] = active_currency.round(total_debit)
            data['total_credit'] = active_currency.round(total_credit)
            data['total_balance'] = active_currency.round(
                data['total_debit'] - data['total_credit'])
        else:
            data['total_debit'] = round(total_debit, 2)
            data['total_credit'] = round(total_credit, 2)
            data['total_balance'] = data['total_debit'] - data['total_credit']
        limit = filter_kwargs.get('limit', LIMIT) if not filter_kwargs.get('is_report', False) else 0
        offset = filter_kwargs.get('offset', 0)
        data['account_entries'] = {
            account_type.get('display_name'): self._get_account_entries(account_type.get('id'), domain,
                                                                        account_type.get('display_name'), limit, offset, filter_kwargs.get('company_ids', []))
            for account_type in data['accounts']}
        data['currency_id'] = active_currency.symbol
        return data
