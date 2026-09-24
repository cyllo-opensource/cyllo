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
from odoo.tests import common


class TestCylloFieldServiceFleet(common.TransactionCase):
    """
    Test class for the Cyllo Field Service Fleet module.

    This class sets up common test data required for testing
    field service requests integrated with the Fleet module.
    It ensures that vehicles, contracts, services, employees,
    checklists, and related records are available for reuse
    across all test cases.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up reusable test records for all test cases in this class.

        The setup includes:
        - Vehicle states (registered, reserved) from fleet data.
        - A test vehicle brand and model.
        - A test vehicle with odometer reading and registered state.
        - A fleet contract and log service linked to the vehicle.
        - A customer partner and a user to assign requests.
        - A company and skill records (type, skill, category).
        - A field service request linked to the vehicle, partner, and skill.
        - A test product and a pending checklist item.
        - A test employee and worker linked to the request.

        These records simulate a realistic environment to validate
        fleet assignment, service lifecycle, and worker allocation.
        """
        super().setUpClass()

        # Create test users instead of relying on 'admin'
        cls.user_admin = cls.env['res.users'].create({
            'name': 'Administrator',
            'login': 'test_admin',
        })
        cls.user_a = cls.env['res.users'].create({
            'name': 'User A',
            'login': 'user_a',
        })

        # Partner
        cls.partner = cls.env['res.partner'].create({'name': 'Customer A'})

        # Company
        cls.company = cls.env['res.company'].create({'name': 'Test Company'})

        # Fleet setup
        cls.state_registered = cls.env.ref('fleet.fleet_vehicle_state_registered')
        cls.state_reserved = cls.env.ref('fleet.fleet_vehicle_state_reserve')

        cls.brand = cls.env['fleet.vehicle.model.brand'].create({'name': 'Test Brand'})
        cls.model = cls.env['fleet.vehicle.model'].create({
            'name': 'Test Model',
            'brand_id': cls.brand.id
        })
        cls.vehicle = cls.env['fleet.vehicle'].create({
            'license_plate': 'TEST123',
            'state_id': cls.state_registered.id,
            'odometer': 1234.0,
            'model_id': cls.model.id,
        })

        # Fleet contracts and services
        cls.contract = cls.env['fleet.vehicle.log.contract'].create({
            'vehicle_id': cls.vehicle.id,
            'state': 'open'
        })

        cls.log_service = cls.env['fleet.vehicle.log.services'].create({
            'vehicle_id': cls.vehicle.id,
            'state': 'new'
        })

        # Skills
        cls.skill_type = cls.env['hr.skill.type'].create({'name': 'Skill Type 1'})
        cls.hr_skill = cls.env['hr.skill'].create({
            'name': 'Test Skill',
            'skill_type_id': cls.skill_type.id,
        })
        cls.skill_category = cls.env['field.service.skill.category'].create({
            'name': 'Category',
            'company_id': cls.company.id,
            'hr_skill_ids': [(6, 0, cls.hr_skill.ids)]
        })

        # Field Service Request
        cls.request = cls.env['field.service.request'].create({
            'name': 'FS0001',
            'partner_id': cls.partner.id,
            'user_id': cls.user_a.id,  # assign test user
            'fleet_id': cls.vehicle.id,
            'skill_category_id': cls.skill_category.id,
        })

        # Product and Checklist
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'lst_price': 50.0,
        })
        cls.checklist_pending = cls.env['field.service.checklist'].create({
            'field_service_request_id': cls.request.id,
            'status': 'pending',
            'required': True,
            'service_cost': 50.0,
            'product_id': cls.product.id,
        })

        # Employee and worker
        cls.employee = cls.env['hr.employee'].create({'name': 'Worker 1'})
        cls.worker = cls.env['field.service.worker'].create({
            'field_service_request_id': cls.request.id,
            'employee_id': cls.employee.id,
        })
