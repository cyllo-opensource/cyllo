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
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestCarbonMetrics(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # Create core master data
        cls.carbon_gas = cls.env['carbon.gas'].create({'name': 'CO2', 'code': 'CO2_test'})
        cls.carbon_scope = cls.env['carbon.scope'].create({'name': 'Scope 1', 'code': 'SCOPE1', 'description': 'Direct Emissions'})
        cls.carbon_unit = cls.env['carbon.unit'].create({'name': 'Liters'})
        cls.carbon_source = cls.env['carbon.source'].create({
            'name': 'Diesel Generator',
            'category': 'energy',
            'activity_unit': cls.carbon_unit.id,
            'scope_id': cls.carbon_scope.id,
            'company_id': cls.company.id,
        })
        cls.carbon_factor = cls.env['carbon.factor'].create({
            'name': 'Diesel Factor',
            'source_id': cls.carbon_source.id,
            'type': 'air',
            'gas_id': cls.carbon_gas.id,
            'factor_value': 2.5,
            'company_id': cls.company.id,
        })

    def test_01_activity_emission_calculation(self):
        """Test that carbon activity emission_total is correctly calculated"""
        calc = self.env['carbon.calc'].create({
            'name': 'Monthly Calc',
            'company_id': self.company.id,
        })
        activity = self.env['carbon.activity'].create({
            'name': 'Burned Diesel',
            'calculation_id': calc.id,
            'source_id': self.carbon_source.id,
            'quantity': 100.0,
            'factor_id': self.carbon_factor.id,
            'company_id': self.company.id,
        })
        self.assertEqual(activity.emission_total, 250.0)

    def test_02_negative_quantity_validation(self):
        """Test that negative quantity raises ValidationError"""
        with self.assertRaises(ValidationError):
            self.env['carbon.activity'].create({
                'name': 'Negative Burned Diesel',
                'source_id': self.carbon_source.id,
                'quantity': -50.0,
                'factor_id': self.carbon_factor.id,
                'company_id': self.company.id,
            })
            
    def test_03_calc_totals(self):
        """Test that calculation totals are aggregated correctly"""
        calc = self.env['carbon.calc'].create({
            'name': 'Aggregated Calc',
            'company_id': self.company.id,
        })
        self.env['carbon.activity'].create([
            {
                'name': 'Act 1',
                'calculation_id': calc.id,
                'source_id': self.carbon_source.id,
                'quantity': 10.0,
                'factor_id': self.carbon_factor.id,
                'company_id': self.company.id,
            },
            {
                'name': 'Act 2',
                'calculation_id': calc.id,
                'source_id': self.carbon_source.id,
                'quantity': 20.0,
                'factor_id': self.carbon_factor.id,
                'company_id': self.company.id,
            }
        ])
        self.assertEqual(calc.total_emissions, 75.0)
        self.assertEqual(calc.total_air_pollution, 75.0)
        self.assertEqual(calc.total_water_pollution, 0.0)
