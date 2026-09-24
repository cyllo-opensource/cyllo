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
from odoo.exceptions import ValidationError


class CarbonCalculation(models.Model):
    _name = 'carbon.calc'
    _description = 'Carbon Calculation'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'date desc, name'

    name = fields.Char(required=True, help="Name of the carbon emission calculation.")
    date = fields.Date(required=True, default=fields.Date.context_today, help="Date of the carbon emission calculation.")
    carbon_activity_ids = fields.One2many('carbon.activity', 'calculation_id', string='Activities')
    total_emissions = fields.Float(compute='_compute_totals', string='Total Emissions', store=True,
                                   help="Total emissions from all associated activities.")
    total_air_pollution = fields.Float(compute='_compute_totals', string='Total Air Pollution', store=True,
                                       help="Total air emissions from associated activities.")
    total_water_pollution = fields.Float(compute='_compute_totals', string='Total Water Pollution', store=True,
                                         help="Total water pollution from associated activities.")
    total_sound_pollution = fields.Float(compute='_compute_totals', string='Total Sound Pollution', store=True,
                                         help="Total sound pollution from associated activities.")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('done', 'Done'),
    ], default='draft', required=True)
    note = fields.Text(help="Additional notes or remarks for this calculation.")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    highest_source_id = fields.Many2one('carbon.source', string='Highest Emitting Source',
        compute='_compute_highest_source', store=True, help="Emission source with the highest calculated emissions.")

    emission_type_filter = fields.Selection([
        ('all', 'All Types'),
        ('air', 'Air (Carbon)'),
        ('water', 'Water Pollution'),
        ('sound', 'Sound / Noise'),
    ], string='Emission Type to Print', default='all', required=True, help="Select the emission type.")
    print_note = fields.Boolean(string='Print Notes', default=True, help="Enable to include notes in the printed report.")
    print_activities = fields.Boolean(string='Print Activity Details', default=True,
                                      help="Enable to include activity details in the printed report.")

    @api.depends('carbon_activity_ids.emission_total', 'carbon_activity_ids.emission_type')
    def _compute_totals(self):
        """Compute totals for the record."""
        for rec in self:
            rec.total_emissions = sum(rec.carbon_activity_ids.mapped('emission_total'))
            rec.total_air_pollution = sum(
                rec.carbon_activity_ids.filtered(lambda a: a.emission_type == 'air').mapped('emission_total'))
            rec.total_water_pollution = sum(
                rec.carbon_activity_ids.filtered(lambda a: a.emission_type == 'water').mapped('emission_total'))
            rec.total_sound_pollution = sum(
                rec.carbon_activity_ids.filtered(lambda a: a.emission_type == 'sound').mapped('emission_total'))

    @api.depends('carbon_activity_ids.emission_total', 'carbon_activity_ids.source_id')
    def _compute_highest_source(self):
        """Compute highest source for the record."""
        for calc in self:
            emissions_by_source = {}
            for act in calc.carbon_activity_ids:
                if act.source_id:
                    emissions_by_source[act.source_id] = emissions_by_source.get(act.source_id,
                                                                                 0.0) + act.emission_total
            if emissions_by_source:
                calc.highest_source_id = max(emissions_by_source, key=emissions_by_source.get)
            else:
                calc.highest_source_id = False

    @api.model_create_multi
    def create(self, vals_list):
        """Create carbon calculations and validate the carbon limit for affected companies."""
        records = super(CarbonCalculation, self).create(vals_list)
        for company in records.mapped('company_id'):
            company.check_carbon_limit()
        return records

    def write(self, vals):
        """Update calculations and validate the carbon limit for affected companies."""
        res = super(CarbonCalculation, self).write(vals)
        for company in self.mapped('company_id'):
            company.check_carbon_limit()
        return res

    def unlink(self):
        """Delete calculations and revalidate the carbon limit for affected companies."""
        companies = self.mapped('company_id')
        res = super(CarbonCalculation, self).unlink()
        for company in companies:
            company.check_carbon_limit()
        return res

    @api.model
    def _get_next_calc_name(self, date, company, name_prefix):
        """Build a calculation name for ``date``, suffixed when siblings already exist."""
        base_name = f"{name_prefix} {date}"
        twins = self.search_count([
            ('name', '=like', f"{base_name}%"),
            ('company_id', '=', company.id),
        ])
        return base_name if not twins else f"{base_name} ({twins + 1})"

    @api.model
    def _get_or_create_draft_calc(self, date, company, name_prefix="Calculations for",
                                  extra_vals=None):
        """Return the draft calculation of ``date`` for ``company``, creating one if needed.

        Integrations (Manufacturing, Inventory, Fleet) may only feed activities into
        a calculation that is still in Draft. When the day's calculation has already
        been submitted, approved or marked done, a new draft one is opened instead of
        touching the closed record.
        """
        calc = self.search([
            ('date', '=', date),
            ('state', '=', 'draft'),
            ('company_id', '=', company.id),
        ], limit=1)
        if calc:
            return calc
        vals = {
            'name': self._get_next_calc_name(date, company, name_prefix),
            'date': date,
            'state': 'draft',
            'company_id': company.id,
        }
        vals.update(extra_vals or {})
        return self.create(vals)

    def get_activities_to_print(self):
        """Retrieve activities to print."""
        self.ensure_one()
        activities = self.carbon_activity_ids
        if self.emission_type_filter != 'all':
            activities = activities.filtered(lambda a: a.factor_id.type == self.emission_type_filter)
        return activities

    def get_total_emissions_to_print(self):
        """Retrieve total emissions to print."""
        self.ensure_one()
        activities = self.get_activities_to_print()
        return sum(activities.mapped('emission_total'))

    def get_total_air_pollution_to_print(self):
        """Retrieve total air pollution to print."""
        self.ensure_one()
        activities = self.get_activities_to_print()
        return sum(activities.filtered(lambda a: a.emission_type == 'air').mapped('emission_total'))

    def get_total_water_pollution_to_print(self):
        """Retrieve total water pollution to print."""
        self.ensure_one()
        activities = self.get_activities_to_print()
        return sum(activities.filtered(lambda a: a.emission_type == 'water').mapped('emission_total'))

    def get_total_sound_pollution_to_print(self):
        """Retrieve total sound pollution to print."""
        self.ensure_one()
        activities = self.get_activities_to_print()
        return sum(activities.filtered(lambda a: a.emission_type == 'sound').mapped('emission_total'))

    def get_source_summary(self):
        """Retrieve source summary."""
        self.ensure_one()
        sources = self.env['carbon.source'].search([])
        summary = []
        for source in sources:
            activities = self.carbon_activity_ids.filtered(lambda a: a.source_id == source)
            air = sum(activities.filtered(lambda a: a.emission_type == 'air').mapped('emission_total'))
            water = sum(activities.filtered(lambda a: a.emission_type == 'water').mapped('emission_total'))
            sound = sum(activities.filtered(lambda a: a.emission_type == 'sound').mapped('emission_total'))
            summary.append({
                'source': source.name,
                'air': air,
                'water': water,
                'sound': sound,
            })
        return summary

    def get_company_comparison_data(self):
        """Retrieve company comparison data."""
        companies = self.env['res.company'].search([])
        today = fields.Date.context_today(self)
        start_date = today.replace(month=1, day=1)
        end_date = today
        comparison = []
        for company in companies:
            calcs = self.env['carbon.calc'].search([
                ('state', 'in', ['approved', 'done']),
                ('date', '>=', start_date),
                ('date', '<=', end_date),
                ('company_id', '=', company.id)
            ])
            air_activities = self.env['carbon.activity'].search([
                ('calculation_id', 'in', calcs.ids),
                ('factor_id.type', '=', 'air')
            ])
            used_amount = sum(activity.emission_total / 1000.0 for activity in air_activities)
            credits = self.env['account.move']._get_available_credits(company.id)
            cap_amount = (company.carbon_cap or 0.0) + credits
            comparison.append({
                'company_name': company.name,
                'cap': cap_amount,
                'used': used_amount,
                'status': 'Exceeded' if used_amount > cap_amount else 'Under Cap'
            })
        return comparison

    def get_selected_companies_names(self):
        """Retrieve selected companies names."""
        return ", ".join(self.env.companies.mapped('name'))

    def get_company_wise_pollution(self):
        """Retrieve company wise pollution."""
        selected_companies = self.env.companies
        company_data = []
        for company in selected_companies:
            activities = self.carbon_activity_ids.filtered(lambda a: a.company_id == company)
            air = sum(activities.filtered(lambda a: a.emission_type == 'air').mapped('emission_total'))
            water = sum(activities.filtered(lambda a: a.emission_type == 'water').mapped('emission_total'))
            sound = sum(activities.filtered(lambda a: a.emission_type == 'sound').mapped('emission_total'))
            
            today = fields.Date.context_today(self)
            start_date = today.replace(month=1, day=1)
            end_date = today
            calcs = self.env['carbon.calc'].search([
                ('state', 'in', ['approved', 'done']),
                ('date', '>=', start_date),
                ('date', '<=', end_date),
                ('company_id', '=', company.id)
            ])
            air_activities = self.env['carbon.activity'].search([
                ('calculation_id', 'in', calcs.ids),
                ('factor_id.type', '=', 'air')
            ])
            used_amount = sum(activity.emission_total / 1000.0 for activity in air_activities)
            credits = self.env['account.move']._get_available_credits(company.id)
            cap_amount = (company.carbon_cap or 0.0) + credits

            company_data.append({
                'company_name': company.name,
                'air': air,
                'water': water,
                'sound': sound,
                'cap': cap_amount,
                'used': used_amount,
                'status': 'Exceeded' if used_amount > cap_amount else 'Under Cap'
            })
        return company_data

    def action_draft(self):
        """Perform the draft action."""
        self.write({'state': 'draft'})

    def action_submit(self):
        """Perform the submit action."""
        self.write({'state': 'submitted'})

    def action_approve(self):
        """Approve the calculation after validating the user's access rights."""
        if not self.env.user.has_group('cyllo_green_metrics.group_carbon_manager'):
            from odoo.exceptions import ValidationError
            raise ValidationError("Only a Green Metrics Manager can approve this calculation.")
        self.write({'state': 'approved'})

    def action_done(self):
        """Mark the calculation as done after validating the user's access rights."""
        if not self.env.user.has_group('cyllo_green_metrics.group_carbon_manager'):
            from odoo.exceptions import ValidationError
            raise ValidationError("Only a Green Metrics Manager can move this calculation to Done state.")
        self.write({'state': 'done'})


