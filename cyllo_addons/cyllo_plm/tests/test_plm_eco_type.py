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


class TestPlmEcoType(TransactionCase):

    def test_create_eco_type_default_values(self):
        """ Verify that an ECO type is created correctly with default values. """
        eco_type = self.env['plm.eco.type'].create({
            'name': 'Test ECO Type Product',
        })
        self.assertEqual(eco_type.name, 'Test ECO Type Product')
        self.assertEqual(eco_type.eco_type, 'product', "Default category type should be 'product'")
        self.assertEqual(eco_type.company_id, self.env.company, "Default company should match current user's environment company")

    def test_create_eco_type_bom(self):
        """ Verify that an ECO type of category 'bom' is created correctly. """
        eco_type = self.env['plm.eco.type'].create({
            'name': 'Test ECO Type BoM',
            'eco_type': 'bom',
            'description': 'BoM change requests type',
        })
        self.assertEqual(eco_type.name, 'Test ECO Type BoM')
        self.assertEqual(eco_type.eco_type, 'bom')
        self.assertEqual(eco_type.description, 'BoM change requests type')
