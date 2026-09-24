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
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_cyllo_green_metrics_mrp = fields.Boolean(
        string='Manufacturing Integration',
        help='Automatically calculate carbon emissions based on manufacturing order operations'
    )
    module_cyllo_green_metrics_stock = fields.Boolean(
        string='Inventory Integration',
        help='Automatically calculate carbon emissions based on Inventory operations'
    )
    module_cyllo_green_metrics_project = fields.Boolean(
        string='Initiatives',
        help='Track sustainability initiatives using Project tasks'
    )

    fleet_integration = fields.Boolean(
        related='company_id.fleet_integration',
        readonly=False,
        string='Fleet Integration',
    )

    water_cap = fields.Float(
        related='company_id.water_cap',
        readonly=False,
        string='Allocated Water',
        help='Maximum allowed water usage'
    )
    water_unit = fields.Selection(
        related='company_id.water_unit',
        readonly=False,
        string='Unit'
    )
    water_duration = fields.Selection(
        related='company_id.water_duration',
        readonly=False,
        string='Duration'
    )

    carbon_cap = fields.Float(
        related='company_id.carbon_cap',
        readonly=False,
        string='Carbon Cap',
        help='Maximum allowed carbon emissions'
    )
    previous_year_achieved = fields.Float(
        related='company_id.previous_year_achieved',
        readonly=False,
        string='Previous Year Achieved',
        help='Carbon emissions achieved in the previous year'
    )
    targeted_achievement = fields.Float(
        related='company_id.targeted_achievement',
        readonly=False,
        string='Targeted Achievement',
        help='Targeted carbon emissions achievement'
    )
    carbon_unit = fields.Selection(
        related='company_id.carbon_unit',
        readonly=False,
        string='Unit'
    )
    carbon_duration = fields.Selection(
        related='company_id.carbon_duration',
        readonly=False,
        string='Duration'
    )

    enable_credit_transfer = fields.Boolean(
        config_parameter='cyllo_green_metrics.enable_credit_transfer',
        string='Credit Transfer'
    )

    def set_values(self):
        """Apply configuration settings and synchronize related menus and emission factors."""
        super(ResConfigSettings, self).set_values()
        menu_buy = self.env.ref('cyllo_green_metrics.menu_credit_buy', raise_if_not_found=False)
        menu_sell = self.env.ref('cyllo_green_metrics.menu_credit_sell', raise_if_not_found=False)
        if menu_buy:
            menu_buy.active = self.enable_credit_transfer
        if menu_sell:
            menu_sell.active = self.enable_credit_transfer

        if self.fleet_integration:
            company = self.company_id
            source = self.env['carbon.source'].search([
                ('name', '=', 'car emission'),
                ('company_id', '=', company.id)
            ], limit=1)
            if not source:
                unit_km = self.env['carbon.unit'].search([
                    ('name', '=', 'km'),
                    ('company_id', '=', company.id)
                ], limit=1)
                if not unit_km:
                    unit_km = self.env['carbon.unit'].create({
                        'name': 'km',
                        'company_id': company.id
                    })
                source = self.env['carbon.source'].create({
                    'name': 'car emission',
                    'category': 'other',
                    'activity_unit': unit_km.id,
                    'company_id': company.id
                })

            gas_co2 = self.env['carbon.gas'].search([('name', 'ilike', 'Carbon Dioxide')], limit=1)
            if not gas_co2:
                gas_co2 = self.env['carbon.gas'].create({'name': 'Carbon Dioxide', 'code': 'CO2'})

            # Create per-vehicle factors for all vehicles with CO2 or sound values
            vehicles = self.env['fleet.vehicle'].search([
                '|', ('company_id', '=', False), ('company_id', '=', company.id)
            ])
            for vehicle in vehicles:
                # Determine CO2 in kg: check vehicle.co2 (g/km), fallback to model.default_co2 (g/km)
                v_co2_gkm = getattr(vehicle, 'co2', 0.0) or 0.0
                if not v_co2_gkm and vehicle.model_id:
                    v_co2_gkm = getattr(vehicle.model_id, 'default_co2', 0.0) or 0.0
                v_co2 = v_co2_gkm / 1000.0

                if v_co2:
                    air_factor = self.env['carbon.factor'].search([
                        ('name', '=', vehicle.name),
                        ('source_id', '=', source.id),
                        ('type', '=', 'air'),
                        ('company_id', '=', company.id),
                    ], limit=1)
                    if air_factor:
                        air_factor.write({'factor_value': v_co2})
                    else:
                        self.env['carbon.factor'].create({
                            'name': vehicle.name,
                            'factor_value': v_co2,
                            'source_id': source.id,
                            'gas_id': gas_co2.id,
                            'type': 'air',
                            'company_id': company.id,
                        })

                # Sound emission factor
                v_sound = 0.0
                if vehicle.model_id:
                    v_sound = getattr(vehicle.model_id, 'default_sound', 0.0) or 0.0
                if v_sound:
                    sound_factor = self.env['carbon.factor'].search([
                        ('name', '=', vehicle.name),
                        ('source_id', '=', source.id),
                        ('type', '=', 'sound'),
                        ('company_id', '=', company.id),
                    ], limit=1)
                    if sound_factor:
                        sound_factor.write({'factor_value': v_sound})
                    else:
                        self.env['carbon.factor'].create({
                            'name': vehicle.name,
                            'factor_value': v_sound,
                            'source_id': source.id,
                            'type': 'sound',
                            'company_id': company.id,
                        })

