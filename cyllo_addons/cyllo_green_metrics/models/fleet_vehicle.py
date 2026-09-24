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
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    default_sound = fields.Float(string='Sound Emission', help='Sound emission in dB')

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'


    @api.model
    def _get_vehicle_co2_kg(self, vehicle):
        """Return co2 in kg/km: check vehicle.co2 first, then model.default_co2 (g/km -> kg/km)."""
        v_co2 = getattr(vehicle, 'co2', 0.0) or 0.0
        if not v_co2 and vehicle.model_id:
            v_co2 = getattr(vehicle.model_id, 'default_co2', 0.0) or 0.0
        return round(v_co2 / 1000.0, 6) if v_co2 else 0.0

    @api.model
    def _get_vehicle_sound(self, vehicle):
        """Return sound emission in dB from model."""
        if vehicle.model_id:
            return getattr(vehicle.model_id, 'default_sound', 0.0) or 0.0
        return 0.0

    @api.model
    def _ensure_vehicle_factor(self, source, vehicle, factor_type='air'):
        """Find or create a per-vehicle factor under the given source."""
        factor_name = f'{vehicle.name}'
        company_id = self.env.company.id
        if factor_type == 'air':
            co2_kg = self._get_vehicle_co2_kg(vehicle)
            if not co2_kg:
                return None
            factor = self.env['carbon.factor'].search([
                ('name', '=', factor_name),
                ('source_id', '=', source.id),
                ('type', '=', 'air'),
                ('company_id', '=', company_id),
            ], limit=1)
            if factor:
                if round(factor.factor_value, 6) != co2_kg:
                    factor.write({'factor_value': co2_kg})
            else:
                gas_co2 = self.env['carbon.gas'].search([('name', 'ilike', 'Carbon Dioxide')], limit=1)
                factor = self.env['carbon.factor'].create({
                    'name': factor_name,
                    'factor_value': co2_kg,
                    'source_id': source.id,
                    'gas_id': gas_co2.id if gas_co2 else False,
                    'type': 'air',
                    'company_id': company_id,
                })
            return factor
        elif factor_type == 'sound':
            sound_val = self._get_vehicle_sound(vehicle)
            if not sound_val:
                return None
            factor = self.env['carbon.factor'].search([
                ('name', '=', factor_name),
                ('source_id', '=', source.id),
                ('type', '=', 'sound'),
                ('company_id', '=', company_id),
            ], limit=1)
            if factor:
                if round(factor.factor_value, 6) != sound_val:
                    factor.write({'factor_value': sound_val})
            else:
                factor = self.env['carbon.factor'].create({
                    'name': factor_name,
                    'factor_value': sound_val,
                    'source_id': source.id,
                    'type': 'sound',
                    'company_id': company_id,
                })
            return factor
        return None

    @api.model
    def _cron_calculate_fleet_emissions(self):
        """Cron calculate fleet emissions method."""
        companies = self.env['res.company'].search([('fleet_integration', '=', True)])
        for company in companies:
            self.with_company(company)._calculate_company_fleet_emissions(company)

    @api.model
    def _calculate_company_fleet_emissions(self, company):
        """Calculate company fleet emissions method."""
        today = fields.Date.context_today(self)

        source = self.env['carbon.source'].search([
            ('name', '=', 'car emission'),
            ('company_id', '=', company.id)
        ], limit=1)
        if not source:
            _logger.info(f"Source 'car emission' not found for company {company.name}.")
            return

        # Get today's draft calculation, or open a new one when the day's record
        # has already been submitted/approved/done.
        calc = self.env['carbon.calc']._get_or_create_draft_calc(
            today, company, name_prefix='Fleet Emission')

        # Find today's odometer records, latest per vehicle
        odometers_today = self.env['fleet.vehicle.odometer'].search(
            [('date', '=', today)], order='id desc'
        )
        vehicles_processed = {}
        for odom in odometers_today:
            if odom.vehicle_id.id not in vehicles_processed:
                if not odom.vehicle_id.company_id or odom.vehicle_id.company_id.id == company.id:
                    vehicles_processed[odom.vehicle_id.id] = odom

        if not vehicles_processed:
            _logger.info(f"No odometer records found for today for company {company.name}.")
            return

        for vehicle_id, latest_odom in vehicles_processed.items():
            vehicle = latest_odom.vehicle_id

            # Previous odometer record before today
            past_odom = self.env['fleet.vehicle.odometer'].search([
                ('vehicle_id', '=', vehicle.id),
                ('date', '<', today)
            ], order='date desc, id desc', limit=1)

            past_value = 0.0
            if past_odom and past_odom.id != latest_odom.id:
                past_value = past_odom.value

            distance = latest_odom.value - past_value
            if distance <= 0:
                _logger.info(f"Distance <= 0 for {vehicle.name}, skipping.")
                continue

            odometer_unit = getattr(vehicle, 'odometer_unit', 'kilometers')
            if odometer_unit == 'miles':
                distance *= 1.60934

            # --- CO2 / Air emission ---
            air_factor = self._ensure_vehicle_factor(source, vehicle, factor_type='air')
            if air_factor and not air_factor._is_valid_on(today):
                _logger.info(
                    f"Air factor '{air_factor.name}' is not valid on {today}, skipping.")
                air_factor = None
            if air_factor:
                self._upsert_activity(
                    calc=calc,
                    source=source,
                    vehicle=vehicle,
                    factor=air_factor,
                    distance=distance,
                    today=today,
                    label='CO2 Emission',
                )

            # --- Sound emission ---
            sound_factor = self._ensure_vehicle_factor(source, vehicle, factor_type='sound')
            if sound_factor and not sound_factor._is_valid_on(today):
                _logger.info(
                    f"Sound factor '{sound_factor.name}' is not valid on {today}, skipping.")
                sound_factor = None
            if sound_factor:
                self._upsert_activity(
                    calc=calc,
                    source=source,
                    vehicle=vehicle,
                    factor=sound_factor,
                    distance=distance,
                    today=today,
                    label='Sound Emission',
                )

    @api.model
    def _upsert_activity(self, calc, source, vehicle, factor, distance, today, label):
        """Create or update a carbon activity for a vehicle in a calculation."""
        activity_name = f'{label} for {vehicle.name}'
        company_id = self.env.company.id
        existing = self.env['carbon.activity'].search([
            ('calculation_id', '=', calc.id),
            ('source_id', '=', source.id),
            ('factor_id', '=', factor.id),
            ('name', '=', activity_name),
            ('company_id', '=', company_id),
        ], limit=1)

        if existing:
            if existing._is_carbon_locked():
                _logger.info(f"Activity '{activity_name}' is locked, skipping update.")
                return
            existing.write({'quantity': distance, 'factor_id': factor.id})
            _logger.info(f"Updated activity '{activity_name}': {distance} km")
        else:
            self.env['carbon.activity'].create({
                'name': activity_name,
                'date': today,
                'calculation_id': calc.id,
                'source_id': source.id,
                'scope_id': source.scope_id.id if source.scope_id else False,
                'uom_id': source.activity_unit.id if source.activity_unit else False,
                'quantity': distance,
                'factor_id': factor.id,
                'state': 'draft',
                'company_id': company_id,
            })
            _logger.info(f"Created activity '{activity_name}': {distance} km")
