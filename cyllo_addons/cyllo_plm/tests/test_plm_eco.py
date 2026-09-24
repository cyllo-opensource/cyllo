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
from odoo.exceptions import UserError


class TestPlmEco(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """Retrieve XML loaded stage and type data"""
        super().setUpClass()

        cls.stage_new = cls.env.ref('cyllo_plm.eco_stage_new')
        cls.stage_progress = cls.env.ref('cyllo_plm.eco_stage_progress')
        cls.stage_done = cls.env.ref('cyllo_plm.eco_stage_effective')
        cls.stage_cancelled = cls.env.ref('cyllo_plm.eco_stage_cancelled')

        cls.eco_type_product = cls.env['plm.eco.type'].create({
            'name': 'Product Change Type',
            'eco_type': 'product',
        })

        cls.product = cls.env['product.template'].create({
            'name': 'Test PLM Product',
            'version': '1',
        })

    def test_eco_creation_reference_and_defaults(self):
        """ Verify sequence prefix generation and default stage on ECO creation. """
        eco = self.env['plm.eco'].create({
            'product_id': self.product.id,
            'type_id': self.eco_type_product.id,
        })
        self.assertNotEqual(eco.name, 'New')
        self.assertTrue(eco.name.startswith('ECO/'), "ECO name should start with 'ECO/' sequence prefix")
        self.assertEqual(eco.stage_id, self.stage_new, "ECO should be initialized with the lowest sequence stage (New)")
        self.assertEqual(eco.company_id, self.product.company_id, "Company ID should be computed from the associated product")

    def test_eco_workflow_actions(self):
        """ Verify workflow transitions: starting, applying, and cancelling revisions. """
        eco = self.env['plm.eco'].create({
            'product_id': self.product.id,
            'type_id': self.eco_type_product.id,
        })

        eco.action_start_revision()
        self.assertEqual(eco.stage_id, self.stage_progress, "ECO should move to 'In Progress' stage")
        self.assertTrue(eco.product_snapshot, "Product snapshot should be captured on start revision")

        eco.action_apply_revision()
        self.assertEqual(eco.stage_id, self.stage_done, "ECO should move to 'Effective/Done' stage")
        self.assertEqual(eco.product_id.version, '2', "Product version should be incremented upon applying revision")

        eco_cancel = self.env['plm.eco'].create({
            'product_id': self.product.id,
            'type_id': self.eco_type_product.id,
        })
        eco_cancel.action_start_revision()
        eco_cancel.action_cancel_revision()
        self.assertEqual(eco_cancel.stage_id, self.stage_cancelled, "ECO should move to 'Cancelled' stage")

    def test_eco_write_constraints(self):
        """ Verify that a Done/Effective ECO cannot be modified or moved backward in workflow. """
        eco = self.env['plm.eco'].create({
            'product_id': self.product.id,
            'type_id': self.eco_type_product.id,
        })
        eco.action_start_revision()
        eco.action_apply_revision()

        with self.assertRaises(UserError, msg="Should block moving backward once in Effective stage"):
            eco.write({'stage_id': self.stage_progress.id})

        with self.assertRaises(UserError, msg="Should block moving to Cancelled once in Effective stage"):
            eco.write({'stage_id': self.stage_cancelled.id})

    def test_version_increment(self):
        """ Verify the version string increment logic. """
        eco = self.env['plm.eco'].create({
            'product_id': self.product.id,
            'type_id': self.eco_type_product.id,
        })
        self.assertEqual(eco._increment_version('1'), '2')
        self.assertEqual(eco._increment_version('V1'), 'V2')
        self.assertEqual(eco._increment_version('1.0'), '1.1')
        self.assertEqual(eco._increment_version('A'), 'A1')
        self.assertEqual(eco._increment_version(''), '1')
        self.assertEqual(eco._increment_version(None), '1')
