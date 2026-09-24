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
from odoo import models


class GeneralLedgerReport(models.AbstractModel):
    _inherit = 'report.cyllo_accounting.general_ledger'

    def _get_data(self, account_id, **kwargs):
        """
        Retrieve detailed move line data for a specific account.

        Args:
            account_id (int): The ID of the account to retrieve detailed move lines for.
            **kwargs: Additional keyword arguments for filtering move lines, including:
                - target_move (list): List of target move states to consider.
                - analytic_ids (list): List of analytic account IDs for additional filtering.
                - journal_ids (list): List of journal IDs for additional filtering.
                - company_ids (list): List of company IDs for additional filtering.
                - start_date (str): Start date of the period to retrieve move lines for in 'YYYY-MM-DD' format.
                - end_date (str): End date of the period to retrieve move lines for in 'YYYY-MM-DD' format.

        Returns:
            list: A list of dictionaries containing detailed move line data, with keys:
                - 'id': ID of the move line.
                - 'annotations': Annotations of the move line.
                - 'account_id': ID of the account.
                - 'credit': Credit amount.
                - 'date': Date of the move line.
                - 'debit': Debit amount.
                - 'journal_id': ID of the journal.
                - 'move_id': ID of the move.
                - 'move_name': Name of the move.
                - 'name': Name of the move line.
                - 'partner_name': Name of the partner (can be NULL if no partner).
                - 'partner_id': ID of the partner (can be NULL if no partner).
        """
        target_move = kwargs.get('target_move', [])
        analytic_ids = kwargs.get('analytic_ids', [])
        journal_ids = kwargs.get('journal_ids', [])
        company_ids = kwargs.get('company_ids', [])
        start_date = kwargs.get('start_date', "")
        end_date = kwargs.get('end_date', "")

        query = """SELECT move_line.id, move_line.annotations, move_line.account_id, move_line.credit,
                   move_line.date, move_line.debit, move_line.journal_id,
                   move_line.move_id, move_line.move_name, move_line.name,
                   partner.name AS partner_name, partner.id AS partner_id
                   FROM account_move_line move_line
                   LEFT JOIN res_partner partner
                   ON move_line.partner_id = partner.id
                   WHERE move_line.account_id = %s
                   AND move_line.parent_state IN %s
                   AND move_line.date >= %s 
                   AND move_line.date <= %s"""

        params = (account_id, tuple(target_move), start_date, end_date)
        if company_ids:
            if len(company_ids) > 1:
                query += f""" AND move_line.company_id IN {tuple(company_ids)}"""
            else:
                query += f""" AND move_line.company_id = {company_ids[0]}"""
        if journal_ids:
            if len(journal_ids) > 1:
                query += f""" AND move_line.journal_id IN {tuple(journal_ids)}"""
            else:
                query += f""" AND move_line.journal_id = {journal_ids[0]}"""
        if analytic_ids:
            if len(analytic_ids) > 1:
                query += " AND ("
                for idx, rec in enumerate(analytic_ids):
                    query += f""" (move_line.analytic_distribution->> '{rec}') IS NOT NULL {'OR' if idx < len(analytic_ids) - 1 else ''}"""
                query += " )"
            else:
                query += f""" AND (move_line.analytic_distribution->> '{analytic_ids[0]}') IS NOT NULL"""
        query += """ ORDER BY move_line.id DESC"""
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()
