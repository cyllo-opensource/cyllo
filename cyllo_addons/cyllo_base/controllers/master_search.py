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
from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request

SIZE = 5


class MasterSearch(http.Controller):
    """Controller for the master search functionality."""

    @staticmethod
    def _user_can_read_model(model_name):
        """Return whether the current user has read ACL on an installed model."""
        if model_name not in request.env.registry.models:
            return False
        return request.env[model_name].check_access_rights(
            'read', raise_exception=False)

    @staticmethod
    def _searchable_name_field(model_name):
        model = request.env[model_name]
        field = model._fields.get(model._rec_name or 'name')
        return field if field and field.store and field.type in (
            'char', 'text', 'html') else False

    @http.route("/cy/master/models", methods=["POST"], type="json",
                auth="user")
    def cy_master_models(self, query=""):
        """Return enabled model candidates the current user can read."""
        query = (query or '').strip()
        if not query:
            return []
        model_records = request.env['ir.model'].sudo().search(
            [('master_search', '=', False),
             '|', ('name', 'ilike', query), ('model', 'ilike', query)],
            order='name, id')
        candidates = []
        for record in model_records:
            model_name = record.model
            if model_name not in request.env.registry.models:
                continue
            if not self._user_can_read_model(model_name):
                continue
            if not self._searchable_name_field(model_name):
                continue
            candidates.append({'model': model_name, 'name': record.name})
        return candidates

    @http.route("/cy/master/add_model", methods=["POST"], type="json",
                auth="user")
    def cy_master_add_model(self, model):
        """Enable a readable model after validating the client request."""
        model_record = request.env['ir.model'].sudo().search(
            [('model', '=', model)], limit=1)
        if not model_record or model not in request.env.registry.models:
            return False
        if not self._user_can_read_model(model) \
                or not self._searchable_name_field(model):
            return False
        model_record.write({'master_search': True})
        return True

    @http.route("/cy/master/search", methods=["POST"], type="json",
                auth="user")
    def cy_master_search(self, query, page, company_ids):
        """
        Search for records across multiple models with master search enabled.
        """
        data = []
        ttl_records = request.env['ir.model'].sudo().search(
            [('master_search', '=', True)]).sorted('id')
        ttl_records = ttl_records.filtered(lambda r:
            r.model in request.env.registry.models
            and self._user_can_read_model(r.model)
            and self._searchable_name_field(r.model))
        total_records = len(ttl_records)
        offset = max((page - 1) * SIZE, 0)
        limit = SIZE + offset
        models = ttl_records[offset: limit] if query else ttl_records[:3]
        for rec in models:
            field = self._searchable_name_field(rec.model)
            try:
                if query:
                    records = request.env[rec.model].search(
                        [(field.name, 'ilike', query)], limit=10)
                else:
                    records = request.env[rec.model].search(
                        [], limit=5, order='id desc')
                if records:
                    group = [{
                        'title': rec.name,
                        'name': None,
                        'id': None,
                        'isChild': False,
                        'isParent': True,
                        'model': rec.model,
                    }]
                    group.extend({
                        'title': None,
                        'name': record.display_name,
                        'id': record.id,
                        'isChild': True,
                        'isParent': False,
                        'model': rec.model,
                    } for record in records)
                    data.append(group)
            except (AccessError, ValueError):
                # A model can have custom search behavior or field access
                # restrictions; skip it without exposing records.
                continue
        return data, not (limit + offset >= total_records)
