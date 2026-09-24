# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class CarbonActivity(models.Model):
    _name = 'carbon.activity'
    _description = 'Carbon Activity'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'date, name'

    name = fields.Char(required=True)
    date = fields.Date(required=True, default=fields.Date.context_today, help="Date on which the emission activity occurred.")
    calculation_id = fields.Many2one('carbon.calc', ondelete='set null', help="Calculation record this emission belongs to.")
    source_id = fields.Many2one('carbon.source', ondelete='restrict',  help="Emission source used for this record.")
    scope_id = fields.Many2one('carbon.scope', related='source_id.scope_id', store=True, readonly=False,
                               help="Emission scope derived from the selected source.")
    quantity = fields.Float(required=True, help="Measured quantity of the emission activity.")
    uom_id = fields.Many2one('carbon.unit', related="source_id.activity_unit", string='Unit', help="Unit of measure for the entered quantity.")
    factor_id = fields.Many2one(
        'carbon.factor',
        ondelete='restrict',
        domain="[('source_id', '=', source_id), "
               "'|', ('valid_from', '=', False), ('valid_from', '<=', date), "
               "'|', ('valid_to', '=', False), ('valid_to', '>=', date)]",
        help="Emission factor used to calculate emissions. Only factors valid on "
             "the activity date can be selected."
    )
    gas_id = fields.Many2one(
        'carbon.gas',
        ondelete='restrict',
        compute='_compute_gas_id',
        store=True,
        readonly=False,
        precompute=True,
        help="Greenhouse gas associated with this emission. Taken from the emission "
             "factor, and can be overridden manually."
    )
    factor_value = fields.Float(related='factor_id.factor_value',store=True,readonly=True,  help="Emission factor value applied in the calculation.")
    emission_total = fields.Float(string='Emissions', compute='_compute_emissions', store=True,
                                  help="Total calculated emissions based on the quantity and emission factor.")
    emission_type = fields.Selection(
        related='factor_id.type',
        store=True,
        readonly=True,
        string='Emission Type',
        help="Type of emission produced by the selected emission factor."
    )
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft', required=True)
    note = fields.Text(help="Additional notes or comments about this emission.")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    account_move_id = fields.Many2one("account.move", string="Related Journal Entry")
    account_move_line_id = fields.Many2one("account.move.line", string="Related Journal Item",
                                           copy=False)
    partner_id = fields.Many2one("res.partner", related="account_move_id.partner_id", store=True)

    def init(self):
        """Backfill the gas of activities created before it cascaded from the factor.

        Those records were left with an empty gas and showed up as an
        "Unknown Gas" slice on the dashboard breakdown.
        """
        self.env.cr.execute("""
            UPDATE carbon_activity act
               SET gas_id = factor.gas_id
              FROM carbon_factor factor
             WHERE act.factor_id = factor.id
               AND act.gas_id IS NULL
               AND factor.gas_id IS NOT NULL
        """)
        if self.env.cr.rowcount:
            self.env.invalidate_all()

    @api.depends('quantity', 'factor_value')
    def _compute_emissions(self):
        """Compute emissions for the record."""
        for rec in self:
            rec.emission_total = rec.quantity * rec.factor_value if rec.quantity and rec.factor_value else 0.0

    @api.depends('factor_id')
    def _compute_gas_id(self):
        """Cascade the emission factor's greenhouse gas onto the activity.

        Done as a stored compute rather than an onchange so the gas follows the
        factor on every path: manual entry, the inline editor on the calculation
        form, assignation rules, and the Manufacturing/Inventory/Fleet
        integrations. The field stays writable, so a manual choice is kept until
        the factor changes again.
        """
        for rec in self:
            rec.gas_id = rec.factor_id.gas_id

    @api.onchange('source_id')
    def _onchange_source_id(self):
        """Update the unit and scope, and reset the emission factor when the source changes."""
        if self.source_id:
            self.uom_id = self.source_id.activity_unit
            self.scope_id = self.source_id.scope_id
            self.factor_id = False

    @api.onchange('account_move_line_id')
    def _onchange_account_move_line_id(self):
        """Update the quantity based on the selected journal item."""
        if self.account_move_line_id:
            self.quantity = self.account_move_line_id.quantity

    @api.onchange('factor_id')
    def _onchange_factor_id(self):
        """Retain the source activity unit when the emission factor changes."""
        if self.factor_id:
            # Stop overwriting uom_id with factor unit; it must stay as source activity unit
            if self.source_id and self.source_id.activity_unit:
                self.uom_id = self.source_id.activity_unit

    @api.onchange('date')
    def _onchange_date(self):
        """Drop the emission factor when it is not valid on the new activity date."""
        if self.factor_id and not self.factor_id._is_valid_on(self.date):
            factor_name = self.factor_id.name
            validity = self.factor_id._validity_label()
            self.factor_id = False
            return {'warning': {
                'title': "Emission Factor Removed",
                'message': f"The factor '{factor_name}' is only valid {validity}, "
                           f"so it cannot be used on {self.date}.",
            }}

    @api.constrains('quantity', 'factor_value')
    def _check_values(self):
        """Ensure the quantity and emission factor values are non-negative."""
        for rec in self:
            if rec.quantity < 0 or rec.factor_value < 0:
                raise ValidationError('Quantity and factor must be non-negative.')

    @api.constrains('date', 'factor_id')
    def _check_factor_validity(self):
        """Reject emission factors that are not valid on the activity date."""
        for rec in self:
            if rec.factor_id and not rec.factor_id._is_valid_on(rec.date):
                raise ValidationError(
                    f"The emission factor '{rec.factor_id.name}' is only valid "
                    f"{rec.factor_id._validity_label()} and cannot be used for an "
                    f"activity dated {rec.date}."
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Create activities and validate the carbon limit for affected companies."""
        records = super(CarbonActivity, self).create(vals_list)
        for company in records.mapped('company_id'):
            company.check_carbon_limit()
        return records

    def _get_locked_fields(self):
        """Return the fields that can no longer be changed once an activity is done."""
        return {
            'name', 'date', 'calculation_id', 'source_id', 'scope_id', 'quantity',
            'uom_id', 'factor_id', 'gas_id', 'note', 'company_id',
            'account_move_id', 'account_move_line_id',
        }

    def _is_carbon_locked(self):
        """Return whether this activity may no longer be touched by an integration.

        An activity is locked once it is Done, or once its calculation has left
        the Draft state.
        """
        self.ensure_one()
        return self.state == 'done' or (
            self.calculation_id and self.calculation_id.state != 'draft')

    def _check_done_lock(self, vals):
        """Block edits on activities that are already in the Done state."""
        changed = set(vals) & self._get_locked_fields()
        if not changed:
            return
        done = self.filtered(lambda act: act.state == 'done')
        if done:
            raise UserError(
                "You cannot modify an activity that is in the Done state: %s. "
                "Reset it to Draft first." % ", ".join(done.mapped('name'))
            )

    def write(self, vals):
        """Update activities and validate the carbon limit for affected companies."""
        self._check_done_lock(vals)
        res = super(CarbonActivity, self).write(vals)
        for company in self.mapped('company_id'):
            company.check_carbon_limit()
        return res

    def unlink(self):
        """Delete activities and revalidate the carbon limit for affected companies."""
        companies = self.mapped('company_id')
        res = super(CarbonActivity, self).unlink()
        for company in companies:
            company.check_carbon_limit()
        return res


    def action_apply_rules(self):
        """Apply matching assignment rules to populate the emission source and factor."""
        for rec in self:
            if rec.factor_id or rec.state == 'done':
                continue
            rules = self.env['carbon.assign.rule'].search([
                ('model_id.model', '=', 'carbon.activity'),
                ('active', '=', True),
                ('company_id', '=', rec.company_id.id),
            ], order='priority, id')
            for rule in rules:
                if rule._match(rec):
                    rec.source_id = rule.source_id
                    # A rule factor is only applied when it is valid on the activity date.
                    if rule.factor_id and rule.factor_id._is_valid_on(rec.date):
                        # The factor's gas cascades through _compute_gas_id.
                        rec.factor_id = rule.factor_id
                    # An explicit gas on the rule wins, and covers factor-less rules.
                    if rule.gas_id:
                        rec.gas_id = rule.gas_id
                    break

    def action_mark_done(self):
        """Mark the selected activities as done after validating the user's access rights."""
        if not self.env.user.has_group('cyllo_green_metrics.group_carbon_manager'):
            raise ValidationError("Only a Green Metrics Manager can move an activity to Done state.")
        for rec in self:
            rec.state = 'done'

    def action_compute(self):
        """Validate the emission factor and mark the activity as done."""
        for rec in self:
            if not rec.factor_value:
                raise ValidationError('Selected factor has no value.')
            # Safety net for activities that predate the gas cascade.
            if not rec.gas_id and rec.factor_id.gas_id:
                rec.gas_id = rec.factor_id.gas_id

    def action_set_draft(self):
        """Reopen done activities so they can be edited again."""
        if not self.env.user.has_group('cyllo_green_metrics.group_carbon_manager'):
            raise UserError("Only a Green Metrics Manager can reset an activity to Draft.")
        self.write({'state': 'draft'})

    @api.model
    def _get_initiative_stats(self, xml_id, start_date=False, end_date=False, scope_filter='all'):
        """Retrieve initiative statistics for the specified project and filters."""
        if 'project.task' not in self.env or 'project.project' not in self.env:
            return {
                'project_id': False,
                'idea_stage_id': False,
                'prog_stage_id': False,
                'done_stage_id': False,
                'ideas_cnt': 0,
                'prog_cnt': 0,
                'done_cnt': 0,
                'total_cnt': 0,
                'total_reduced_kg': 0.0,
                'total_recycled_water': 0.0
            }
        project = self.env.ref(xml_id, raise_if_not_found=False)
        ideas_cnt, prog_cnt, done_cnt, total_cnt = 0, 0, 0, 0
        idea_stage_id, prog_stage_id, done_stage_id = False, False, False
        total_reduced_kg = 0.0
        total_recycled_water = 0.0

        if project:
            stages = self.env['project.task.type'].search([('project_ids', 'in', project.id)])
            idea_stage = stages.filtered(lambda s: 'Ideas' in s.name)
            prog_stage = stages.filtered(lambda s: 'Progress' in s.name)
            done_stage = stages.filtered(lambda s: 'Done' in s.name)
            
            idea_stage_id = idea_stage.id if idea_stage else False
            prog_stage_id = prog_stage.id if prog_stage else False
            done_stage_id = done_stage.id if done_stage else False

            domain = [('project_id', '=', project.id)]
            if start_date:
                domain.append(('create_date', '>=', start_date))
            if end_date:
                domain.append(('create_date', '<=', end_date))
            
            if scope_filter == 'available':
                domain.append(('scope_id', '!=', False))
            elif scope_filter == 'no_scope':
                domain.append(('scope_id', '=', False))
            elif scope_filter and scope_filter != 'all':
                try:
                    scope_id = int(scope_filter)
                    domain.append(('scope_id', '=', scope_id))
                except (ValueError, TypeError):
                    pass

            tasks_aggr = self.env['project.task'].read_group(domain, ['stage_id', 'reduced_emissions:sum', 'recycled_water:sum'], ['stage_id'])
            for t_grp in tasks_aggr:
                cnt = t_grp['stage_id_count']
                total_cnt += cnt
                s_id = t_grp['stage_id'][0] if t_grp.get('stage_id') else False
                if idea_stage_id and s_id == idea_stage_id:
                    ideas_cnt += cnt
                elif prog_stage_id and s_id == prog_stage_id:
                    prog_cnt += cnt
                elif done_stage_id and s_id == done_stage_id:
                    done_cnt += cnt
                    total_reduced_kg += t_grp.get('reduced_emissions', 0.0)
                    total_recycled_water += t_grp.get('recycled_water', 0.0)
        
        return {
            'project_id': project.id if project else False,
            'idea_stage_id': idea_stage_id,
            'prog_stage_id': prog_stage_id,
            'done_stage_id': done_stage_id,
            'ideas_cnt': ideas_cnt,
            'prog_cnt': prog_cnt,
            'done_cnt': done_cnt,
            'total_cnt': total_cnt,
            'total_reduced_kg': total_reduced_kg,
            'total_recycled_water': total_recycled_water
        }

    @api.model
    def get_dashboard_data(self, water_date_filter='yearly', water_scope_filter='all', water_start_date=False, water_end_date=False):
        """Retrieve dashboard data."""
        from dateutil.relativedelta import relativedelta
        from datetime import datetime
        # Use context_today for timezone-aware calculations
        today = fields.Date.context_today(self)
        company = self.env.company

        def get_duration_dates(duration):
            if duration == 'today':
                return today, today
            elif duration == 'monthly':
                import calendar
                start = today.replace(day=1)
                end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
                return start, end
            elif duration == 'quarterly':
                import calendar
                start_month = 3 * ((today.month - 1) // 3) + 1
                start = today.replace(month=start_month, day=1)
                end_month = start_month + 2
                end = today.replace(month=end_month, day=calendar.monthrange(today.year, end_month)[1])
                return start, end
            elif duration == 'half_yearly':
                if today.month <= 6:
                    start = today.replace(month=1, day=1)
                    end = today.replace(month=6, day=30)
                else:
                    start = today.replace(month=7, day=1)
                    end = today.replace(month=12, day=31)
                return start, end
            elif duration == 'yearly':
                start = today.replace(month=1, day=1)
                end = today.replace(month=12, day=31)
                return start, end
            return today.replace(month=1, day=1), today.replace(month=12, day=31)
        
        # --- COMMON FILTER LOGIC ---
        start_date = False
        end_date = today
        
        if water_date_filter == 'today':
            start_date = today
            end_date = today
        elif water_date_filter == 'monthly':
            import calendar
            start_date = today.replace(day=1)
            end_date = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        elif water_date_filter == 'quarterly':
            import calendar
            start_month = 3 * ((today.month - 1) // 3) + 1
            start_date = today.replace(month=start_month, day=1)
            end_month = start_month + 2
            end_date = today.replace(month=end_month, day=calendar.monthrange(today.year, end_month)[1])
        elif water_date_filter == 'yearly':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
        elif water_date_filter == 'range':
            if water_start_date:
                start_date = fields.Date.from_string(water_start_date)
            if water_end_date:
                end_date = fields.Date.from_string(water_end_date)
        else:
            # Fallback to yearly if no specific filter
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)

        # Safety fallback: ensure start_date and end_date are always valid dates
        if not start_date:
            start_date = today.replace(month=1, day=1)
        if not end_date or end_date < start_date:
            end_date = today

        def get_scoped_activities(calc_ids, factor_type):
            """Retrieve scoped activities."""
            domain = [('calculation_id', 'in', calc_ids), ('factor_id.type', '=', factor_type)]
            
            if not water_scope_filter or water_scope_filter == 'all':
                return self.env['carbon.activity'].search(domain)
            
            # Handle multiple selections (passed as a list or comma-separated string)
            scope_filters = []
            if isinstance(water_scope_filter, list):
                scope_filters = water_scope_filter
            elif isinstance(water_scope_filter, str):
                scope_filters = water_scope_filter.split(',')

            scope_ids = []
            include_no_scope = False
            for f in scope_filters:
                if f == 'all':
                    return self.env['carbon.activity'].search(domain)
                if f == 'no_scope':
                    include_no_scope = True
                else:
                    try:
                        scope_ids.append(int(f))
                    except (ValueError, TypeError):
                        pass
            
            if scope_ids and include_no_scope:
                domain.append('|')
                domain.append(('scope_id', 'in', scope_ids))
                domain.append(('scope_id', '=', False))
            elif scope_ids:
                domain.append(('scope_id', 'in', scope_ids))
            elif include_no_scope:
                domain.append(('scope_id', '=', False))
            else:
                # If everything is deselected, return nothing as per user request
                return self.env['carbon.activity'].browse()

            return self.env['carbon.activity'].search(domain)

        # Filter calculations in the current period - BOTH 'approved' and 'done' records
        calcs = self.env['carbon.calc'].search([
            ('state', 'in', ['approved', 'done']),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('company_id', '=', company.id)
        ])
        calc_ids = calcs.ids
        
        # --- CAP VS USAGE CALCULATION (CARBON) - DYNAMIC FROM SETTINGS ---
        carbon_duration = company.carbon_duration or 'yearly'
        carbon_unit = company.carbon_unit or 't'
        carbon_duration_label = dict(self.env['res.company']._fields['carbon_duration'].selection).get(carbon_duration) or 'Yearly'
        carbon_unit_label = 'kg CO2e' if carbon_unit == 'kg' else 't CO2e'

        enable_credit_transfer = self.env['res.company']._is_credit_transfer_enabled()

        credits = self.env['account.move']._get_available_credits(company.id)
        if carbon_unit == 'kg':
            cap_amount = (company.carbon_cap or 0.0) + credits * 1000.0
        else:
            cap_amount = (company.carbon_cap or 0.0) + credits

        start_c, end_c = get_duration_dates(carbon_duration)
        calcs_carbon = self.env['carbon.calc'].search([
            ('state', 'in', ['approved', 'done']),
            ('date', '>=', start_c),
            ('date', '<=', end_c),
            ('company_id', '=', company.id)
        ])
        air_activities_carbon = self.env['carbon.activity'].search([
            ('calculation_id', 'in', calcs_carbon.ids),
            ('factor_id.type', '=', 'air')
        ])
        raw_used_carbon = sum(act.emission_total for act in air_activities_carbon)
        used_amount_carbon = raw_used_carbon / 1000.0 if carbon_unit == 't' else raw_used_carbon

        used_amount = used_amount_carbon
        air_activities = get_scoped_activities(calc_ids, 'air')
        if carbon_unit == 'kg':
            filtered_used_amount = sum(act.emission_total for act in air_activities)
        else:
            filtered_used_amount = sum((act.emission_total / 1000.0) for act in air_activities)

        cap_data = {
            'cap': cap_amount,
            'used': round(used_amount_carbon, 3),
            'filtered_used': round(filtered_used_amount, 3),
            'duration': carbon_duration_label,
            'unit': carbon_unit_label,
            'previous_year_achieved': company.previous_year_achieved or 0.0,
            'targeted_achievement': company.targeted_achievement or 0.0,
        }

        # 1. Overall Gas Emissions (Type = air) - Grouped by Gas
        gas_labels = []
        gas_values = []
        if air_activities:
            gas_groups = self.env['carbon.activity'].read_group(
                domain=[('id', 'in', air_activities.ids)],
                fields=['gas_id', 'emission_total:sum'],
                groupby=['gas_id']
            )
            for g in gas_groups:
                gas_name = g['gas_id'][1] if g['gas_id'] else 'Unknown Gas'
                gas_labels.append(gas_name)
                gas_values.append(g['emission_total'])

        # 2. Scope Breakdown
        scope_breakdown = []
        if air_activities:
            scope_groups = self.env['carbon.activity'].read_group(
                domain=[('id', 'in', air_activities.ids)],
                fields=['scope_id', 'emission_total:sum'],
                groupby=['scope_id']
            )
            # Pre-calculate the REAL total across all scopes before computing percentages
            scope_total_emissions = sum(
                sg['emission_total'] / 1000.0 for sg in scope_groups
            )
            for scope_data in scope_groups:
                scope_id = scope_data['scope_id'][0] if scope_data['scope_id'] else False
                scope_name = scope_data['scope_id'][1] if scope_data['scope_id'] else 'No Scope'
                scope_val = scope_data['emission_total'] / 1000.0
                pct = (scope_val / scope_total_emissions * 100.0) if scope_total_emissions > 0 else 0.0
                scope_breakdown.append({
                    'id': scope_id,
                    'name': scope_name,
                    'value': round(scope_val, 3),
                    'percentage': round(pct, 1)
                })

        # Generate trend labels based on duration (daily vs monthly)
        date_delta_days = (end_date - start_date).days
        is_daily_trend = date_delta_days <= 31
        
        labels_map_template = {}
        if is_daily_trend:
            curr_d = start_date
            while curr_d <= end_date:
                labels_map_template[curr_d.strftime('%Y-%m-%d')] = 0.0
                curr_d += relativedelta(days=1)
        else:
            curr_m = start_date.replace(day=1)
            end_m = end_date.replace(day=1)
            while curr_m <= end_m:
                labels_map_template[curr_m.strftime('%Y-%m')] = 0.0
                curr_m += relativedelta(months=1)
                
        display_labels = []
        for k in labels_map_template.keys():
            if is_daily_trend:
                display_labels.append(datetime.strptime(k, '%Y-%m-%d').strftime('%d %b'))
            else:
                display_labels.append(datetime.strptime(k, '%Y-%m').strftime('%b %Y'))

        num_labels = len(display_labels)
        keys_list = list(labels_map_template.keys())

        # 3. Sound Analysis (Type = sound) - Dynamic Trend
        sound_activities = get_scoped_activities(calc_ids, 'sound')
        sound_labels_map = labels_map_template.copy()
        
        for act in sound_activities:
            if not act.date: continue
            k = act.date.strftime('%Y-%m-%d') if is_daily_trend else act.date.strftime('%Y-%m')
            if k in sound_labels_map:
                sound_labels_map[k] += act.emission_total

        sound_labels = display_labels
        sound_values = list(sound_labels_map.values())

        # 4. Water Pollution Chart (Type = water) - Dynamic Trend
        water_activities_trend = get_scoped_activities(calc_ids, 'water')
        water_labels_map = labels_map_template.copy()
        
        for act in water_activities_trend:
            if not act.date: continue
            k = act.date.strftime('%Y-%m-%d') if is_daily_trend else act.date.strftime('%Y-%m')
            if k in water_labels_map:
                water_labels_map[k] += act.emission_total
        
        water_labels = display_labels
        water_values = list(water_labels_map.values())

        # 5. Air Trend (Type = air) - Dynamic Trend
        air_labels_map = labels_map_template.copy()
        for act in air_activities:
            if not act.date: continue
            k = act.date.strftime('%Y-%m-%d') if is_daily_trend else act.date.strftime('%Y-%m')
            if k in air_labels_map:
                air_labels_map[k] += (act.emission_total / 1000.0) # Tonnes
        
        air_trend_labels = display_labels
        air_trend_values = list(air_labels_map.values())

        # Compute Monthly Scope Breakdown Trend (Type = air) - Dynamic
        scopes_list = self.env['carbon.scope'].search([])
        scope_names_map = {scope.id: scope.name for scope in scopes_list}
        
        datasets = {s_name: [0.0] * num_labels for s_name in scope_names_map.values()}
        datasets['No Scope'] = [0.0] * num_labels
        
        for act in air_activities:
            if not act.date: continue
            k = act.date.strftime('%Y-%m-%d') if is_daily_trend else act.date.strftime('%Y-%m')
            if k in keys_list:
                idx = keys_list.index(k)
                val = act.emission_total / 1000.0 # Convert to Tonnes
                s_name = act.scope_id.name if act.scope_id else 'No Scope'
                if s_name not in datasets:
                    datasets[s_name] = [0.0] * num_labels
                datasets[s_name][idx] += val
                
        monthly_scope_datasets = []
        for s_name, val_list in datasets.items():
            monthly_scope_datasets.append({
                'label': s_name,
                'data': [round(v, 3) for v in val_list]
            })
            
        monthly_scope_emissions = {
            'labels': display_labels,
            'datasets': monthly_scope_datasets
        }

        # 6. Initiatives (Green, Water, Sound)
        project_installed = self.env['ir.module.module'].search([
            ('name', '=', 'cyllo_green_metrics_project'),
            ('state', '=', 'installed')
        ], limit=1)
        show_initiatives = bool(project_installed)

        if show_initiatives:
            green_stats = self._get_initiative_stats('cyllo_green_metrics_project.project_green_initiatives', start_date, end_date, water_scope_filter)
            water_stats = self._get_initiative_stats('cyllo_green_metrics_project.project_water_initiatives', start_date, end_date, water_scope_filter)
            sound_stats = self._get_initiative_stats('cyllo_green_metrics_project.project_sound_initiatives', start_date, end_date, water_scope_filter)
        else:
            empty_stats = {
                'project_id': False,
                'idea_stage_id': False,
                'prog_stage_id': False,
                'done_stage_id': False,
                'ideas_cnt': 0,
                'prog_cnt': 0,
                'done_cnt': 0,
                'total_cnt': 0,
                'total_reduced_kg': 0.0,
                'total_recycled_water': 0.0
            }
            green_stats = empty_stats
            water_stats = empty_stats
            sound_stats = empty_stats

        # Available Credit = Allocated Cap - Used Amount + Reduced Emissions + Transfer Credits
        # Retrieve reduced emissions from initiatives in the carbon_duration period
        green_stats_c = self._get_initiative_stats('cyllo_green_metrics_project.project_green_initiatives', start_c, end_c, water_scope_filter)
        water_stats_c = self._get_initiative_stats('cyllo_green_metrics_project.project_water_initiatives', start_c, end_c, water_scope_filter)
        sound_stats_c = self._get_initiative_stats('cyllo_green_metrics_project.project_sound_initiatives', start_c, end_c, water_scope_filter)
        total_reduced_kg_c = green_stats_c['total_reduced_kg'] + water_stats_c['total_reduced_kg'] + sound_stats_c['total_reduced_kg']

        if carbon_unit == 'kg':
            reduced_emissions_c = total_reduced_kg_c
            transfer_credits_c = credits * 1000.0
        else:
            reduced_emissions_c = total_reduced_kg_c / 1000.0
            transfer_credits_c = credits

        original_used = float(used_amount)
        cap_val = float(cap_amount)

        credit = cap_val - original_used + reduced_emissions_c + transfer_credits_c
        cap_data['available_credit'] = round(credit, 3)

        # Visibility logic for available credit
        show_credit = (cap_val > 0) and (credit > 0.0001)
        if abs(cap_val - original_used) < 0.0001 and abs(reduced_emissions_c) < 0.0001:
            show_credit = False
            
        cap_data['show_available_credit'] = show_credit
        cap_data['used'] = round(original_used, 3)

        # --- WATER CAP VS USAGE CALCULATION WITH FILTERS ---
        water_unit = company.water_unit or 'L'
        water_cap_amount = company.water_cap or 0.0
        water_duration = company.water_duration or 'yearly'
        water_duration_label = dict(self.env['res.company']._fields['water_duration'].selection).get(water_duration) or 'Yearly'
        
        # Fetch all scopes for the filter dropdown
        scopes = self.env['carbon.scope'].search_read([], ['id', 'name'])
        
        start_w, end_w = get_duration_dates(water_duration)
        calcs_water = self.env['carbon.calc'].search([
            ('state', 'in', ['approved', 'done']),
            ('date', '>=', start_w),
            ('date', '<=', end_w),
            ('company_id', '=', company.id)
        ])
        water_activities_duration = self.env['carbon.activity'].search([
            ('calculation_id', 'in', calcs_water.ids),
            ('factor_id.type', '=', 'water')
        ])
        water_used_amount = 0.0
        
        for activity in water_activities_duration:
            act_unit = activity.uom_id.name or ""
            qty = activity.quantity
            if act_unit.lower() == 'l':
                qty_in_l = qty
            elif act_unit.lower() in ('kl', 'tonnes'):
                qty_in_l = qty * 1000.0
            else:
                qty_in_l = qty

            if water_unit == 'L':
                water_used_amount += qty_in_l
            elif water_unit in ('KL', 'tonnes'):
                water_used_amount += (qty_in_l / 1000.0)

        water_stats_duration = self._get_initiative_stats('cyllo_green_metrics_project.project_water_initiatives', start_w, end_w, water_scope_filter)
        recycled_kl = water_stats_duration['total_recycled_water']
        if water_unit == 'L':
            recycled_water = recycled_kl * 1000.0
        else:
            recycled_water = recycled_kl
            
        water_credit = water_cap_amount - water_used_amount + recycled_water
        show_water_credit = (water_cap_amount > 0) and (water_credit > 0.0001)
        if abs(water_cap_amount - water_used_amount) < 0.0001 and abs(recycled_water) < 0.0001:
            show_water_credit = False

        water_cap_data = {
            'cap': float(water_cap_amount),
            'used': round(float(water_used_amount), 3),
            'duration': water_duration_label,
            'unit': water_unit,
            'available_credit': round(float(water_credit), 3),
            'show_available_credit': show_water_credit
        }

        return {
            'cap_data': cap_data,
            'water_cap_data': water_cap_data,
            'enable_credit_transfer': enable_credit_transfer,
            'projects': green_stats if show_initiatives else False,
            'water_projects': water_stats if show_initiatives else False,
            'sound_projects': sound_stats if show_initiatives else False,
            'show_initiatives': show_initiatives,
            'scopes': scopes,
            'gas': {
                'labels': gas_labels,
                'values': gas_values
            },
            'sound': {
                'labels': sound_labels,
                'values': sound_values
            },
            'water': {
                'labels': water_labels,
                'values': water_values
            },
            'air_trend': {
                'labels': air_trend_labels,
                'values': air_trend_values
            },
            'scope_breakdown': scope_breakdown,
            'monthly_scope_emissions': monthly_scope_emissions,
            'transfer_credits': self.env['account.move']._get_available_credits(),
        }
