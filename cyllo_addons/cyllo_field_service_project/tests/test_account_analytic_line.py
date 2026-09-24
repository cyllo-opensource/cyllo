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
from odoo import fields


class TestAccountAnalyticLine(TransactionCase):
    """
    Test suite for verifying the custom behavior of the
    `account.analytic.line` model when extended with the
    `service_id` compute field.

    This class focuses on ensuring that the `service_id`
    field is correctly populated from the context when
    creating analytic lines, and remains False otherwise.
    """
    @classmethod
    def setUpClass(cls):
        """
        Set up the initial test environment.

        This method creates the required base records:
        - A partner (`res.partner`) to associate with the service request.
        - A skill category (`field.service.skill.category`) required for service requests.
        - A service request (`field.service.request`) that will be linked to analytic lines
          via context during compute.

        These records are shared across all test methods in this class.
        """
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})
        cls.skill_category = cls.env['field.service.skill.category'].create({
            'name': 'Test Skill Category',
        })
        cls.service_request = cls.env['field.service.request'].create({
            'name': 'Test Request',
            'partner_id': cls.partner.id,
            'skill_category_id': cls.skill_category.id,
        })

    def test_compute_service_id(self):
        """
        Test the computation of `service_id` in `account.analytic.line`.

        Scenario 1:
            - Create an analytic line with context `service_id` set to a
              `field.service.request` record.
            - Expectation: The analytic line's `service_id` should equal
              the provided service request.

        Scenario 2:
            - Create an analytic line without any `service_id` in the context.
            - Expectation: The analytic line's `service_id` should remain False.

        This ensures that the compute method `compute_service_id`
        respects the context when assigning values and defaults to
        False when no service request is available.
        """
        analytic_line = self.env['account.analytic.line'].with_context(
            service_id=self.service_request.id
        ).create({
            'name': 'Work on service request',
            'date': fields.Date.today(),
            'unit_amount': 5.0,
        })
        self.assertEqual(analytic_line.service_id.id, self.service_request.id)
        analytic_line_1 = self.env['account.analytic.line'].create({
            'name': 'Work on service request',
            'date': fields.Date.today(),
            'unit_amount': 3.0,
        })
        self.assertFalse(analytic_line_1.service_id)
