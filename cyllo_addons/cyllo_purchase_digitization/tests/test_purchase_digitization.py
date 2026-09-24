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


class TestPurchaseDigitization(TransactionCase):
    """
    Test suite for verifying functionality of the `purchase.digitization` model.

    This suite validates:
        * Default field values on creation.
        * Only one record can be active at a time (create + write override).
        * Activating one configuration correctly deactivates all others.
        * Updating non-relevant fields does not affect activation states.
    """

    def test_create(self):
        """
        Test the create() override for purchase.digitization.

        Validates:
            1. First active configuration stays active.
            2. Creating a second active configuration deactivates the first.
            3. Creating an inactive configuration does not affect the active one.
        """
        rec1 = self.env['purchase.digitization'].create({
            'name': 'Config 1',
            'active_configuration': True,
        })

        rec1 = rec1.browse(rec1.id)
        self.assertTrue(rec1.active_configuration)

        rec2 = self.env['purchase.digitization'].create({
            'name': 'Config 2',
            'active_configuration': True,
        })
        rec1 = rec1.browse(rec1.id)
        rec2 = rec2.browse(rec2.id)
        self.assertTrue(rec2.active_configuration)
        self.assertFalse(rec1.active_configuration)

        rec3 = self.env['purchase.digitization'].create({
            'name': 'Config 3',
            'active_configuration': False,
        })

        rec2 = rec2.browse(rec2.id)
        rec3 = rec3.browse(rec3.id)
        self.assertTrue(rec2.active_configuration)
        self.assertFalse(rec3.active_configuration)

    def test_write(self):
        """
        Test the write() override of purchase.digitization.

        Validates:
            1. Updating a record to active must deactivate all others.
            2. Updating an inactive record's name must NOT affect active status.
            3. Writing active=True on a different record switches activation.
        """
        rec1 = self.env['purchase.digitization'].create({
            'name': 'Config 1',
            'active_configuration': True,
        })
        rec2 = self.env['purchase.digitization'].create({
            'name': 'Config 2',
            'active_configuration': False,
        })
        rec1 = rec1.browse(rec1.id)
        rec2 = rec2.browse(rec2.id)
        self.assertTrue(rec1.active_configuration)
        self.assertFalse(rec2.active_configuration)

        rec2.write({'active_configuration': True})
        rec1 = rec1.browse(rec1.id)
        rec2 = rec2.browse(rec2.id)
        self.assertTrue(rec2.active_configuration)
        self.assertFalse(rec1.active_configuration)

        rec2.write({'name': 'Updated Name'})
        rec1 = rec1.browse(rec1.id)
        rec2 = rec2.browse(rec2.id)
        self.assertTrue(rec2.active_configuration)
        self.assertFalse(rec1.active_configuration)

        rec3 = self.env['purchase.digitization'].create({
            'name': 'Config 3',
            'active_configuration': False,
        })
        rec3.write({'active_configuration': True})
        rec1 = rec1.browse(rec1.id)
        rec2 = rec2.browse(rec2.id)
        rec3 = rec3.browse(rec3.id)
        self.assertTrue(rec3.active_configuration)
        self.assertFalse(rec1.active_configuration)
        self.assertFalse(rec2.active_configuration)
