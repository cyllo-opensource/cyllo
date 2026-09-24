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
import json
from odoo.tests import tagged
from odoo.addons.cyllo_field_service_fleet.tests.common import TestCylloFieldServiceFleet


@tagged('-at_install', 'post_install')
class TestServiceRequest(TestCylloFieldServiceFleet):
    """
    Test suite for field service requests integrated with the fleet module.

    This suite verifies:
        - The computation of fleet domain rules for assigning vehicles
          to service requests.
        - The cancellation logic of service requests and its impact on
          linked fleet contracts.
    """

    def test_compute_fleet_domain(self):
        """
        Test the `_compute_fleet_domain` method on field service requests.

        Steps:
            1. Trigger `_compute_fleet_domain` on the service request.
            2. Decode the JSON domain stored in `request.fleet_domain`.
            3. Build the expected domain manually by:
                - Collecting vehicle IDs from open fleet contracts.
                - Collecting vehicle IDs from fleet services in 'new' or
                'running' state.
                - Collecting vehicle IDs from service requests in 'assigned'
                or 'in_progress'.
            4. Ensure the domain excludes the above vehicles and only allows
               vehicles in the "Registered" state (`state_registered`).
            5. Compare computed domain with the expected domain.
        """
        self.request._compute_fleet_domain()
        computed_domain = json.loads(self.request.fleet_domain)
        expected_vehicle_ids = list(set(
            self.env['fleet.vehicle.log.contract'].search(
                [('state', '=', 'open')]).mapped('vehicle_id').ids +
            self.env['fleet.vehicle.log.services'].search(
                [('state', 'in', ('new', 'running'))]).mapped(
                'vehicle_id').ids +
            self.env['field.service.request'].search(
                [('state', 'in', ['assigned', 'in_progress'])]).mapped(
                'fleet_id').ids
        ))
        expected_state_filter = ['state_id', '=', self.state_registered.id]
        expected_excluded_vehicles = ['id', 'not in', expected_vehicle_ids]
        expected_domain = [expected_state_filter, expected_excluded_vehicles]
        self.assertEqual(computed_domain, expected_domain)

    def test_action_cancel(self):
        """
        Test that cancelling a service removes the
        linked fleet contract.
        """
        contract = self.env['fleet.vehicle.log.contract'].create({
            'vehicle_id': self.vehicle.id,
            'state': 'futur',
            'field_service_request_id': self.request.id,
        })
        self.request.fleet_id = self.vehicle
        self.assertTrue(contract.exists())
        res = self.request.action_cancel()
        contract_exists = self.env['fleet.vehicle.log.contract'].search([
            ('id', '=', contract.id)
        ])
        self.assertFalse(contract_exists)
        self.assertIsNone(res)
