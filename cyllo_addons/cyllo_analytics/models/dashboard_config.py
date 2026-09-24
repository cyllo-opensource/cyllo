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
import re
import logging
_logger = logging.getLogger(__name__)

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DashboardConfig(models.Model):
    """Dashboard Configuration Model"""
    _name = 'dashboard.config'
    _description = 'Dashboard Configuration'
    _inherit = ['image.mixin', 'mail.thread']

    def _get_default_user_ids(self):
        """Returns the default admin user ids"""
        return self._get_default_users().ids

    def _get_default_groups(self):
        """Returns the default admin groups"""
        return self.env.ref('cyllo_analytics.group_cyllo_analytics_admin').ids

    def _get_default_banner(self):
        """Method to get the default banner ID."""
        return self.env.ref('cyllo_analytics.dashboard_banner_no_banner').id

    def _get_default_theme(self):
        """Returns the default theme"""
        return self.env.ref("cyllo_analytics.dashboard_theme_cyllo").id

    name = fields.Char(required=True, size=32)
    banner_id = fields.Many2one(
        "dashboard.banner",
        string="Banner",
        default=_get_default_banner,
    )
    group_ids = fields.Many2many(
        'res.groups',
        string='Groups',
        default=_get_default_groups
    )
    user_ids = fields.Many2many(
        'res.users',
        string='Users',
        default=_get_default_user_ids
    )
    limit = fields.Integer()
    theme_id = fields.Many2one(
        'dashboard.theme',
        default=_get_default_theme
    )
    sheet_ids = fields.Many2many(
        'dashboard.sheet',
        string='Sheets'
    )
    global_filter_ids = fields.One2many(
        'dashboard.global.filter',
        'dashboard_config_id'
    )
    users_ids = fields.Many2many(
        'res.users',
        'dashboard_config_user_rel',
        compute="_compute_users_ids",
        store=True
    )
    company_id = fields.Many2one('res.company', string="Company")

    share_link_ids = fields.One2many('dashboard.share.link', 'dashboard_id', string="Shareable Links")

    def generate_share_link(self):
        """Generate a new shareable link."""
        date_from = self.env.context.get('default_date_from')
        date_to = self.env.context.get('default_date_to')
        self.env['dashboard.share.link'].create({
            'dashboard_id': self.id,
            'sheet_queries': self.env.context.get('default_sheet_queries'),
            'date_from': date_from.replace('/', '-') if isinstance(date_from, str) else date_from,
            'date_to': date_to.replace('/', '-') if isinstance(date_to, str) else date_to,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dashboard.config',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    skip_filter = fields.Boolean(
        "Skip filter",
        default=False
    )
    ir_menu_ids = fields.Many2many(
        'ir.ui.menu',
        string='Linked Menus'
    )

    def _get_default_users(self):
        """Returns the default admin users"""
        return self.env.ref('cyllo_analytics.group_cyllo_analytics_admin').users

    @api.depends("group_ids", "user_ids", "create_uid")
    def _compute_users_ids(self):
        """Computes the users and groups and assigns it back"""
        default_group_id = self.env.ref(
            'cyllo_analytics.group_cyllo_analytics_admin')
        admin_user = default_group_id.mapped('users')
        for record in self:
            user_ids = record.group_ids.mapped(
                'users') + record.user_ids + admin_user
            record.users_ids = [fields.Command.set(user_ids.ids)]
            admin_ids = self._get_default_users()
            record.user_ids |= admin_ids
            record.group_ids |= default_group_id

    @api.model
    def get_sheets(self, res_id):
        """Get all the sheets"""

        def get_a_sheet():
            """Method to get a sheet associated with the current user."""
            return self.search([
                '|',
                ('users_ids', 'in', self.env.user.ids),
                ('group_ids', 'in', self.env.user.groups_id.ids)
            ], limit=1)

        if res_id:
            rec = self.search([
                ('id', '=', res_id),
                '|',
                ('users_ids', 'in', self.env.user.ids),
                ('group_ids', 'in', self.env.user.groups_id.ids)
            ])
            if not rec:
                rec = get_a_sheet()
        else:
            rec = get_a_sheet()
        theme_id = rec.theme_id or self.env.ref(
            'cyllo_analytics.dashboard_theme_walden')
        return [rec.get_data(), rec.id, theme_id.read_theme(), rec.name or 'Dashboard',
                rec.banner_id.read(['name', 'image_1920'])]

    def get_data(self, field_list=None):
        """Method to get data for the specified fields from associated sheets (optimized)."""
        if not field_list:
            # Need to explicitly request non-stored computed fields, otherwise Odoo skips them
            field_list = ['name', 'query', 'dimension', 'measure', 'dimension_axis', 'type', 'limit',
                          'kpi_target', 'kpi_description', 'kpi_redirect', 'kpi_view', 'kpi_icon']

        # Batch read sheets metadata
        sheets_data = self.sheet_ids.read(field_list)
        sheets_map = {s['id']: s for s in sheets_data}

        # Batch fetch all related data to avoid N+1 performance issues
        # Options (attributes for position/size)
        options = self.env['dashboard.sheet.option'].search([
            ('dashboard_sheet_id', 'in', self.sheet_ids.ids),
            ('dashboard_config_id', '=', self.id)
        ])
        options_read = options.read(['attributes', 'dashboard_sheet_id'])
        options_map = {}
        for opt in options_read:
            options_map.setdefault(opt['dashboard_sheet_id'][0], []).append(opt)

        # Parallel read for main related models
        all_filters = self.sheet_ids.mapped('filter_ids').read(
            ["name", "domain", "is_active", "sheet_id", "domain_py_expression"]
        )
        all_tables = self.sheet_ids.mapped('table_ids').read()
        all_axes = self.sheet_ids.mapped('axis_ids').read()

        filters_map = {}
        for f in all_filters: filters_map.setdefault(f['sheet_id'][0], []).append(f)
        tables_map = {}
        for t in all_tables: tables_map.setdefault(t['sheet_id'][0], []).append(t)
        axes_map = {}
        for a in all_axes: axes_map.setdefault(a['sheet_id'][0], []).append(a)
        
        all_color_mappings = self.sheet_ids.mapped('color_mapping_ids').read(
            ["measure_alias", "min_value", "max_value", "color", "indicator", "notes", "sheet_id"]
        )
        color_mappings_map = {}
        for cm in all_color_mappings: color_mappings_map.setdefault(cm['sheet_id'][0], []).append(cm)

        all_annotations = self.sheet_ids.mapped('annotation_ids').read(
            ["measure_alias", "dimension_label", "notes", "sheet_id"]
        )
        annotations_map = {}
        for a in all_annotations: annotations_map.setdefault(a['sheet_id'][0], []).append(a)

        # Global Filters (sheet_filter_ids) - requires deeper batch fetch
        global_filters = self.env['dashboard.sheet.global'].search([
            ('sheet_id', 'in', self.sheet_ids.ids),
            ('global_filter_id.dashboard_config_id', '=', self.id)
        ])
        gf_read = global_filters.read(["field", "name", "sheet_id", "global_filter_id"])
        g_filter_ids = [gf['global_filter_id'][0] for gf in gf_read if gf['global_filter_id']]
        g_filters_read = self.env['dashboard.global.filter'].browse(g_filter_ids).read(
            ["name", "type", "dashboard_config_id", "relation", "code", "operator"]
        )
        g_filters_map = {f['id']: f for f in g_filters_read}

        global_filters_processed_map = {}
        for gf in gf_read:
            res_gf = {
                "id": gf["id"],
                "field": gf["field"],
                "name": gf["name"],
                "sheet_id": gf["sheet_id"],
                "global_filter_id": g_filters_map.get(gf["global_filter_id"][0]) if gf["global_filter_id"] else False
            }
            global_filters_processed_map.setdefault(gf['sheet_id'][0], []).append(res_gf)

        results = []
        for sheet in self.sheet_ids:
            res = sheets_map.get(sheet.id, {}).copy()
            res["dashboard_sheet_option_ids"] = sorted(options_map.get(sheet.id, []), key=lambda x: x['id'])
            res["filter_ids"] = filters_map.get(sheet.id, [])
            res["table_ids"] = tables_map.get(sheet.id, [])
            res["axis_ids"] = axes_map.get(sheet.id, [])
            res["color_mappings"] = color_mappings_map.get(sheet.id, [])
            res["annotations"] = annotations_map.get(sheet.id, [])
            res["sheet_filter_ids"] = global_filters_processed_map.get(sheet.id, [])
            results.append(res)

        return results

    @api.model
    def sql_execute(self, sql):
        """Execute SQL query"""
        try:
            if sql:
                # Resolve {selectedCurrency} before ANY processing.
                # The stored `query` field may be stale, or the JS may pass
                # the raw query directly — this is the guaranteed choke-point.
                company_currency_id = str(self.env.company.currency_id.id)
                sql = sql.replace('{selectedCurrency}', company_currency_id)

                params = []
                before, sep, after = sql.rpartition("FROM")
                after = sep + after
                tables = re.findall(r'(?i)(?:FROM|JOIN)\s+([`"]?[\w\.]+[`"]?)', after)
                models = self.env['ir.model'].search([('table_name', 'in', tables)]).mapped('model')
                for model in models:
                    model = self.env[model]
                    query_obj = model._where_calc([])
                    model._apply_ir_rules(query_obj, 'read')

                    # Convert domain to SQL clauses
                    from_clause, where_clause, where_params = query_obj.get_sql()
                    join = "LEFT JOIN" if 'LEFT JOIN' in from_clause.upper() else "RIGHT JOIN" if 'RIGHT JOIN' in from_clause.upper() else "JOIN" if 'JOIN' in from_clause.upper() else ""
                    join_clause = join + from_clause.split(f"{join}", 1)[1] if join else ""
                    params = where_params + params

                    if 'WHERE' in after.upper():
                        # Split query at WHERE
                        parts = re.split(r'\bWHERE\b', after, maxsplit=1, flags=re.IGNORECASE)

                        if len(parts) == 2:
                            before_where = parts[0]
                            after_where = parts[1]

                            # Reconstruct with ir.rule
                            after = f"{before_where} {join_clause} WHERE ({where_clause}) AND {after_where}" if where_clause else f"{before_where} {join_clause} WHERE {after_where}"
                    else:
                        # No WHERE clause - add one if ir.rules exist
                        if where_clause:
                            replacement = rf'\1{join_clause} WHERE {where_clause} \2'
                        else:
                            replacement = rf'\1{join_clause} \2'
                        # Find position after FROM clause(s)
                        after = re.sub(
                            r'(FROM\b[\s\S]*?)(\bORDER BY\b|\bGROUP BY\b|\bLIMIT\b|$)',
                            replacement,
                            after,
                            count=1,
                            flags=re.IGNORECASE,
                        )
                new_query = before + after
                _logger.info("============== EXECUTING DASHBOARD SQL ==============")
                _logger.info(new_query)
                
                # Write to tmp file for raw debugging
                with open('/tmp/dashboard_sql_debug.txt', 'w') as f:
                    f.write(new_query + "\n\nPARAMS: " + str(params))
                    
                self.env.cr.execute(new_query, params)
                res = self.env.cr.dictfetchall()
                _logger.info("============== RESULT LENGTH: %s ==============", len(res))
                return res
            else:
                return False
        except Exception as error:
            self.env.cr.rollback()
            return {"__query_error__": True, "message": str(error)}

    def save_position(self, vals):
        """Save the position of the graph in the dashboard (optimized)."""
        sheet_ids = [val["id"] for val in vals["children"]]
        options = self.env['dashboard.sheet.option'].search([
            ('dashboard_sheet_id', 'in', sheet_ids),
            ('dashboard_config_id', "=", self.id)
        ])
        options_map = {opt.dashboard_sheet_id.id: opt for opt in options}

        to_create = []
        for val in vals["children"]:
            # GridStack omits w/h from save() when they equal its internal default
            # of 1, so a missing value means 1 — NOT 3. Defaulting to 3 forced
            # resized KPIs (h=1/2) back to height 3. Floor at 1; the frontend
            # computeStyle re-applies per-type minimums (KPI 1 or 2, charts 3).
            attributes = {
                "x": val["x"],
                "y": val["y"],
                "graph_height": max(val.get("h") or 1, 1),
                "graph_width": max(val.get("w") or 1, 1),
            }
            sheet_option = options_map.get(val["id"])
            if sheet_option:
                sheet_option.write({"attributes": attributes})
            else:
                to_create.append({
                    "dashboard_sheet_id": val["id"],
                    "dashboard_config_id": self.id,
                    "attributes": attributes
                })
        if to_create:
            self.env['dashboard.sheet.option'].create(to_create)

    def get_dashboard_data(self):
        """Get the dashboard data for json export"""
        return {
            "sheets": self.get_data(
                ["name", "query", "dimension", "measure", "type",
                 "dimension_axis", "image_1920", "kpi_name",
                 "kpi_target", "is_enabled", "kpi_redirect",
                 "kpi_view", "kpi_description", "kpi_target_perc",
                 "kpi_icon", "table_ids", "filter_ids", "limit"]),
            "theme": self.theme_id.name,
            "name": self.name,
            "image_1920": self.image_1920,
            "limit": self.limit,
        }

    @api.model
    def import_data(self, data):
        """Import dashboard from a JSON file."""
        try:
            dashboard_config_id = self.create({
                "name": data["name"],
                "limit": data["limit"],
                "image_1920": data["image_1920"],
                "theme_id": self.env["dashboard.theme"].search(
                    [("name", "=", data["theme"])], limit=1).id,
            })
            dashboard_config_id.write({
                "sheet_ids": [fields.Command.create({
                    "name": sheet["name"],
                    "type": sheet["type"],
                    "image_1920": sheet["image_1920"],
                    "dimension_axis": sheet["dimension_axis"],
                    "limit": sheet["limit"] or 0,
                    "kpi_target": sheet.get("kpi_target", False),
                    "kpi_view": sheet.get("kpi_view", False),
                    "kpi_redirect": sheet.get("kpi_target", False),
                    "kpi_icon": sheet.get("kpi_icon", False),
                    "kpi_description": sheet.get("kpi_description", False),
                    "is_enabled": sheet["is_enabled"],
                    "axis_ids": [fields.Command.create({
                        "value": rec['value'],
                        "alias": rec['alias'],
                        "query": rec['query'],
                        "column": rec['column'],
                        "type": rec['type'],
                    }) for rec in sheet["axis_ids"]],
                    "dashboard_sheet_option_ids": [fields.Command.create({
                        "attributes": rec["attributes"],
                        "dashboard_config_id": dashboard_config_id.id
                    }) for rec in sheet["dashboard_sheet_option_ids"]],
                    "table_ids": [fields.Command.create({
                        "name": table['name'],
                        "model": table['model'],
                        "linked": table['linked'],
                        "field": table['field'],
                        "join": table['join'],
                        "model_id": self.env['ir.model'].search(
                            [('model', '=', table['model'])]).id,
                    }) for table in sheet["table_ids"]],
                    "filter_ids": [fields.Command.create({
                        "name": filter_data.get("name", False),
                        "domain": filter_data.get("domain", False),
                        "is_active": filter_data.get("is_active", False),
                    }) for filter_data in sheet["filter_ids"]],
                }) for sheet in data["sheets"]]
            })
            return True, ""
        except Exception as e:
            return False, e

    def remove_sheet(self, sheet_id):
        """Method to remove a sheet."""
        self.sheet_ids.filtered(
            lambda rec: rec.id == sheet_id).dashboard_sheet_option_ids.filtered(
            lambda item: item.dashboard_config_id == self.id).unlink()
        self.write({'sheet_ids': [(fields.Command.unlink(sheet_id))]})

    def execute_query_d(self, obj):
        """Method to execute a database query and send the result through the bus."""
        res_id = obj["id"]
        query = obj["query"]
        result = self.sql_execute(query)
        channel = "CY:ANALYTICS"
        message = {
            "result": result,
            "id": res_id,
            "channel": channel
        }
        self.env["bus.bus"]._sendone(channel, "notification", message)

    def process_query(self, sql):
        """Method to process a SQL query."""
        try:
            self.env.cr.execute(sql)
            return self.env.cr.dictfetchall()
        except Exception as error:
            return False

    @api.model
    def sql_execute_multi(self, queries_obj):
        """Method to execute multiple SQL queries asynchronously."""
        for query in queries_obj:
            self.execute_query_d(query)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """ Method to create multiple records."""
        res = super(DashboardConfig, self).create(vals_list)
        if not res.skip_filter:
            filters = ['dashboard_global_filter_start_date',
                       'dashboard_global_filter_end_date',
                       'dashboard_global_filter_company',
                       'dashboard_global_filter_user']
            for filter_id in filters:
                filter_record = self.env.ref(f"{'cyllo_analytics'}.{filter_id}")
                if filter_record:
                    vals = {
                        'name': filter_record.name,
                        'type': filter_record.type,
                        'code': filter_record.code,
                        'relation': filter_record.relation,
                        'operator': filter_record.operator,
                        'dashboard_config_id': res.id
                    }
                res.update(
                    {'global_filter_ids': [(fields.Command.create(vals))]})
        return res

    def append_menu(self, menu_id):
        """ Method to append a menu to the dashboard configuration."""
        self.write({"ir_menu_ids": [fields.Command.link(menu_id)]})

    def write(self, data):
        """ Method to write data to the record."""
        menus = data.get('ir_menu_ids')
        to_remove_menus = filter(lambda rec: rec[0] == 3,
                                 menus) if menus else []
        self.remove_added_menus(to_remove_menus)
        res = super().write(data)

        # Add Group Access to Selected Users Automatically
        if "user_ids" in data:
            group = self.env.ref("cyllo_analytics.group_cyllo_analytics_user")
            for rec in self:
                for user in rec.users_ids:
                    if group not in user.groups_id:
                        user.write(
                            {"groups_id": [(4, group.id)]}
                        )  # Add group safely
        return res

    def remove_added_menus(self, to_remove_menu_ids):
        """Method to remove added menus."""
        for rec_id in to_remove_menu_ids:
            rec_id = rec_id if type(rec_id) is int else rec_id[1]
            menu_id = self.env["ir.ui.menu"].browse(rec_id)
            if menu_id.exists():
                menu_id.action.unlink()
                menu_id.unlink()

    def clean_up_menus(self):
        """Method to clean up menus associated with the record."""
        menu_ids = self.ir_menu_ids.ids
        if menu_ids:
            self.remove_added_menus(menu_ids)

    def unlink(self):
        """Method to unlink the record."""
        if self.id == self.env.ref('cyllo_analytics.dashboard_config_main').id:
            raise ValidationError("Can't remove the main Dashboard")
        self.clean_up_menus()
        return super().unlink()

    @api.model
    def get_app_menus(self, app_id=None):
        """
        Fetch top-level apps or a specific app's nested submenus.
        If app_id is not provided, returns all top-level apps.
        If app_id is provided, returns the entire nested menu tree for that app.
        """
        IrUiMenu = self.env['ir.ui.menu'].sudo()
        if not app_id:
            # Fetch all root menus (Apps)
            apps = IrUiMenu.search([('parent_id', '=', False)], order='sequence')
            
            home_menu = self.env.ref('cyllo_dashboard.menu_cyllo_dashboard_root', raise_if_not_found=False)
            if home_menu:
                apps -= home_menu
                
            return [{'id': m.id, 'name': m.name, 'sequence': m.sequence} for m in apps]

        def get_children_recursive(menu):
            children = IrUiMenu.search([('parent_id', '=', menu.id)], order='sequence')
            result = []
            for child in children:
                result.append({
                    'id': child.id,
                    'name': child.name,
                    'sequence': child.sequence,
                    'children': get_children_recursive(child)
                })
            return result

        app = IrUiMenu.browse(app_id)
        return {
            'id': app.id,
            'name': app.name,
            'sequence': app.sequence,
            'children': get_children_recursive(app)
        }

    @api.model
    def create_menu_with_sequence(self, menu_vals, before_menu_id=None, after_menu_id=None):
        """
        Creates a new menu and precisely splices it into the correct order based on sibling IDs,
        then gracefully re-sequences all siblings by increments of 10 to clear up compression.
        """
        IrUiMenu = self.env['ir.ui.menu'].sudo()
        parent_id = menu_vals.get('parent_id')

        # Create the new menu initially
        new_menu = IrUiMenu.create(menu_vals)

        # Fetch siblings
        siblings = IrUiMenu.search(
            [('parent_id', '=', parent_id), ('id', '!=', new_menu.id)],
            order='sequence, id'
        )
        sibling_list = list(siblings)

        # Find exact insertion index
        if before_menu_id:
            idx = next((i for i, m in enumerate(sibling_list) if m.id == before_menu_id), len(sibling_list))
            sibling_list.insert(idx, new_menu)
        elif after_menu_id:
            idx = next((i for i, m in enumerate(sibling_list) if m.id == after_menu_id), len(sibling_list) - 1)
            sibling_list.insert(idx + 1, new_menu)
        else:
            sibling_list.append(new_menu)

        # Resequence safely with gaps of 10
        for i, menu in enumerate(sibling_list):
            menu.sequence = (i + 1) * 10

        return new_menu.id
