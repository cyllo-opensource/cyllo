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
import psycopg2

from odoo import http
from odoo.http import request

SIZE = 5


class MasterSearch(http.Controller):
    """Controller for the master search functionality."""

    @http.route("/cy/master/search", methods=["POST"], type="json",
                auth="user")
    def cy_master_search(self, query, page, company_ids):
        """
        Search for records across multiple models with master search enabled.
        """
        data = []
        ttl_records = request.env['ir.model'].sudo().search(
            [('master_search', '=', True)]).sorted('id')
        ttl_records = ttl_records.filtered(
            lambda r: 'name' in r.field_id.filtered(lambda f: f.store).mapped(
                'name'))
        total_records = len(ttl_records)
        offset = max((page - 1) * SIZE, 0)
        limit = SIZE + offset
        if query != '':
            models = ttl_records[offset: limit]
            for rec in models:
                stored_fields = rec.field_id.filtered(lambda f: f.store)
                fields = stored_fields.mapped('name')
                if rec._rec_name in fields:
                    st_filed = stored_fields.filtered(
                        lambda x: x.name == rec._rec_name)
                    column = "name->> 'en_US'" if st_filed.translate else "name"
                    temp_data = []
                    operator = "IN" if len(company_ids) > 1 else "="
                    company = tuple(company_ids) if len(company_ids) > 1 else \
                    company_ids[0]
                    has_company_column = 'company_id' in fields
                    try:
                        if has_company_column:
                            sql_query = (
                                f"SELECT * FROM {rec.model.replace('.', '_')} WHERE {column} "
                                f"ILIKE %s AND company_id {operator} %s LIMIT 10")
                            params = ('%' + query + '%', company)
                        else:
                            sql_query = f"SELECT * FROM {rec.model.replace('.', '_')} WHERE {column} ILIKE %s LIMIT 10"
                            params = ('%' + query + '%',)
                        request.env.cr.execute(sql_query, params)
                        records = request.env.cr.dictfetchall()
                        if len(records) >= 1:
                            temp_data.append({
                                'title': rec.name,
                                'name': None,
                                'id': None,
                                'isChild': False,
                                'isParent': True,
                                'model': rec.model
                            })
                            for val in records:
                                temp_data.append({
                                    'title': None,
                                    'name': val['name'],
                                    'id': val['id'],
                                    'isChild': True,
                                    'isParent': False,
                                    'model': rec.model,
                                    'isJson': st_filed.translate
                                })
                        if records:
                            data.append(temp_data)
                        request.env.cr.commit()
                    except psycopg2.Error:
                        request.env.cr.rollback()
                        try:
                            domain = [('name', 'ilike', query)]
                            if has_company_column:
                                domain.append(
                                    ('company_id', 'in', company_ids))
                            records = request.env[rec.model].search(
                                domain, limit=10)
                            temp_data = []
                            if records:
                                temp_data.append({
                                    'title': rec.name,
                                    'name': None,
                                    'id': None,
                                    'isChild': False,
                                    'isParent': True,
                                    'model': rec.model
                                })
                                for val in records:
                                    temp_data.append({
                                        'title': None,
                                        'name': val['name'],
                                        'id': val['id'],
                                        'isChild': True,
                                        'isParent': False,
                                        'model': rec.model
                                    })
                                data.append(temp_data)
                            request.env.cr.commit()
                        except Exception:
                            request.env.cr.rollback()
        return data, not (limit + offset >= total_records)
