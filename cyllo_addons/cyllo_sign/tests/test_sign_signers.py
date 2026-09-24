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


class TestSignSigners(TransactionCase):
    """
    Test suite for verifying the `_compute_filtered_partner_ids()` behavior
    of the `SignSigners` transient model.

    This test ensures that:
        * When a role has a domain defined, only partners matching that domain
          are included in the computed field.
        * When no domain is defined, all partners are included by default.
    """

    @classmethod
    def setUpClass(cls):
        """
        Set up shared test data for all test cases.

        Creates:
            - Multiple partner records for validating domain filters.
            - Two sign roles: one with a city-based domain and one without.
            - A dummy `sign.generate` wizard for linking signers.
        """
        super().setUpClass()

        cls.partner_1 = cls.env['res.partner'].create(
            {'name': 'Alice', 'email': 'alice@example.com', 'city': 'Bangalore'})
        cls.partner_2 = cls.env['res.partner'].create({'name': 'Bob', 'email': 'bob@example.com', 'city': 'Chennai'})
        cls.partner_3 = cls.env['res.partner'].create(
            {'name': 'Charlie', 'email': 'charlie@example.com', 'city': 'Bangalore'})

        cls.role_with_domain = cls.env['sign.role'].create({
            'name': 'Bangalore Reviewer',
            'domain': "[('city', '=', 'Bangalore')]",
        })
        cls.role_no_domain = cls.env['sign.role'].create({
            'name': 'Global Reviewer',
            'domain': False,
        })

        cls.sign_generate = cls.env['sign.generate'].create({'subject': 'Partner Filter Test'})

    def test_compute_filtered_partner_ids(self):
        """
        Validate `_compute_filtered_partner_ids()` for both role cases:

        1. **With domain:** Only partners from Bangalore should be included.
        2. **Without domain:** All partners should be included.

        Ensures:
            - Domain filtering logic works correctly.
            - Default case includes all available partners.
        """
        signer_domain = self.env['sign.signers'].create({
            'role_id': self.role_with_domain.id,
            'sign_generate_id': self.sign_generate.id,
        })
        expected_bangalore_ids = {self.partner_1.id, self.partner_3.id}
        result_bangalore_ids = set(signer_domain.filtered_partner_ids.ids)
        self.assertEqual(result_bangalore_ids, expected_bangalore_ids)
        signer_no_domain = self.env['sign.signers'].create({
            'role_id': self.role_no_domain.id,
            'sign_generate_id': self.sign_generate.id,
        })
        expected_all_ids = {self.partner_1.id, self.partner_2.id, self.partner_3.id}
        result_all_ids = set(signer_no_domain.filtered_partner_ids.ids)
        self.assertTrue(result_all_ids.issuperset(expected_all_ids))
