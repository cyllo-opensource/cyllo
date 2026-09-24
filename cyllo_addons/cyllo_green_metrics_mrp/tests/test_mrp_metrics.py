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
from odoo.tests.common import TransactionCase

class TestMRPMetrics(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # Create core master data for Green Metrics
        cls.carbon_gas = cls.env['carbon.gas'].create({'name': 'CO2', 'code': 'CO2_test_mrp'})
        cls.carbon_scope = cls.env['carbon.scope'].create({'name': 'Scope 1', 'code': 'SCOPE1_mrp', 'description': 'Direct Emissions'})
        cls.carbon_unit = cls.env['carbon.unit'].create({'name': 'hr_test'})
        cls.carbon_source = cls.env['carbon.source'].create({
            'name': 'Electric Assembly Machine',
            'category': 'energy',
            'activity_unit': cls.carbon_unit.id,
            'scope_id': cls.carbon_scope.id,
            'company_id': cls.company.id,
        })
        cls.carbon_factor = cls.env['carbon.factor'].create({
            'name': 'Electricity Factor',
            'source_id': cls.carbon_source.id,
            'type': 'air',
            'gas_id': cls.carbon_gas.id,
            'factor_value': 2.0,
            'company_id': cls.company.id,
        })
        # Set up MRP Data
        cls.product = cls.env['product.product'].create({
            'name': 'Finished Good',
            'type': 'product',
        })
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Assembly Line',
            'company_id': cls.company.id,
        })
        # Create BoM
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product.product_tmpl_id.id,
            'company_id': cls.company.id,
        })
        # Create MRP Routing Workcenter (Operation)
        cls.routing_wc = cls.env['mrp.routing.workcenter'].create({
            'name': 'Assembly Operation',
            'workcenter_id': cls.workcenter.id,
            'bom_id': cls.bom.id,
            'company_id': cls.company.id,
        })
        # Link Carbon Source to the Operation
        cls.env['mrp.workcenter.carbon'].create({
            'operation_id': cls.routing_wc.id,
            'source_id': cls.carbon_source.id,
            'company_id': cls.company.id,
        })

    def test_01_workorder_creates_carbon_activity(self):
        """Test that completing a workorder with a duration creates carbon activities based on hours."""
        
        # Create a workorder directly (or via mrp.production)
        production = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'product_qty': 1,
            'product_uom_id': self.product.uom_id.id,
            'company_id': self.company.id,
        })
        # A workaround to test the function directly: creating a workorder
        workorder = self.env['mrp.workorder'].create({
            'name': 'Assembly Operation',
            'production_id': production.id,
            'workcenter_id': self.workcenter.id,
            'operation_id': self.routing_wc.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'duration_expected': 60,
            'company_id': self.company.id,
        })
        # Set duration to 120 minutes (which is 2 hours)
        workorder.write({
            'duration': 120.0,
            'state': 'done'
        })
        activity = self.env['carbon.activity'].search([('workorder_id', '=', workorder.id)])
        self.assertEqual(len(activity), 1, "There should be one carbon activity for the workorder.")
        self.assertEqual(activity.source_id.id, self.carbon_source.id)
        # 120 minutes = 2.0 hours. 
        self.assertEqual(activity.quantity, 2.0, "The quantity should be converted from minutes to hours (120/60 = 2).")

    def test_02_workorder_zero_duration_removes_activities(self):
        """Test that if workorder duration is set back to 0, activities are unlinked."""
        production = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'product_qty': 1,
            'product_uom_id': self.product.uom_id.id,
            'company_id': self.company.id,
        })
        workorder = self.env['mrp.workorder'].create({
            'name': 'Assembly Operation',
            'production_id': production.id,
            'workcenter_id': self.workcenter.id,
            'operation_id': self.routing_wc.id,
            'product_id': self.product.id,
            'product_uom_id': self.product.uom_id.id,
            'duration_expected': 60,
            'company_id': self.company.id,
        })
        # Create activity by setting duration to 60 (1 hr)
        workorder.write({'duration': 60.0, 'state': 'done'})
        self.assertEqual(len(self.env['carbon.activity'].search([('workorder_id', '=', workorder.id)])), 1)
        # Set duration back to 0
        workorder.write({'duration': 0.0, 'duration_expected': 0.0})
        # The activity should be unlinked
        self.assertEqual(len(self.env['carbon.activity'].search([('workorder_id', '=', workorder.id)])), 0, "Activities should be removed if duration is zero.")
