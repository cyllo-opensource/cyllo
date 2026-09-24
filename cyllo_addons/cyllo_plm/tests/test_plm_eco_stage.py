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
from odoo.exceptions import ValidationError


class TestPlmEcoStage(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """Clean up any existing stages created by XML data to ensure a clean test state"""
        super().setUpClass()
        cls.env['plm.eco.stage'].search([]).unlink()

        cls.stage_draft = cls.env['plm.eco.stage'].create({
            'name': 'New/Draft',
            'sequence': 10,
        })
        cls.stage_progress = cls.env['plm.eco.stage'].create({
            'name': 'In Progress',
            'sequence': 20,
            'in_progress': True,
        })
        cls.stage_effective = cls.env['plm.eco.stage'].create({
            'name': 'Effective',
            'sequence': 30,
            'done': True,
        })
        cls.stage_cancel = cls.env['plm.eco.stage'].create({
            'name': 'Cancelled',
            'sequence': 40,
            'cancelled': True,
        })

    def test_stage_done_uniqueness_constraint(self):
        """ Ensure that only one stage in the system can be marked as 'done'. """
        with self.assertRaises(ValidationError, msg="Only one done stage should be allowed"):
            self.env['plm.eco.stage'].create({
                'name': 'Another Effective Stage',
                'done': True,
            })

    def test_stage_cancelled_uniqueness_constraint(self):
        """ Ensure that only one stage in the system can be marked as 'cancelled'. """
        with self.assertRaises(ValidationError, msg="Only one cancelled stage should be allowed"):
            self.env['plm.eco.stage'].create({
                'name': 'Another Cancelled Stage',
                'cancelled': True,
            })

    def test_stage_exclusivity_constraint(self):
        """ Ensure a stage cannot be marked as more than one of 'in_progress', 'done', or 'cancelled'. """
        with self.assertRaises(ValidationError, msg="A stage cannot be done and cancelled at the same time"):
            self.env['plm.eco.stage'].create({
                'name': 'Invalid Stage Multi-Type',
                'done': True,
                'cancelled': True,
            })

        with self.assertRaises(ValidationError, msg="A stage cannot be in_progress and done at the same time"):
            self.env['plm.eco.stage'].create({
                'name': 'Invalid Stage Multi-Type 2',
                'in_progress': True,
                'done': True,
            })
