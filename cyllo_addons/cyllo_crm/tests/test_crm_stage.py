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


class TestCrmStage(TransactionCase):
    """
    Test suite for the `crm.stage` model with the custom `type` field
    and the `get_pipeline_stages` method.

    This class verifies:
    - Creation of pipeline stages with different attributes (name, sequence,
     is_won, type).
    - Correct behavior of the `get_pipeline_stages` method, ensuring it
      retrieves all stages as a list of dictionaries.
    - Presence of required fields (`name`, `sequence`, `is_won`) in each stage
     dictionary.
    - Validation that created stages (e.g., 'Stage A' and 'Stage B') are
      included in the result set and that their properties are correctly preserved.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.satge1 = cls.env['crm.stage'].create({
            'name': 'Stage A',
            'sequence': 1,
            'is_won': False,
            'type': 'lead',
        })
        cls.stage2 = cls.env['crm.stage'].create({
            'name': 'Stage B',
            'sequence': 2,
            'is_won': True,
            'type': 'opportunity',
        })

    def test_get_pipeline_stages(self):
        """
        Test that get_pipeline_stages returns stages with required fields
        """
        stages = self.env['crm.stage'].get_pipeline_stages()
        self.assertIsInstance(stages, list)
        for stage in stages:
            self.assertIsInstance(stage, dict)
            self.assertIn('name', stage)
            self.assertIn('sequence', stage)
            self.assertIn('is_won', stage)

        stage_names = [s['name'] for s in stages]
        self.assertIn('Stage A', stage_names)
        self.assertIn('Stage B', stage_names)
        satge_b = next(s for s in stages if s['name'] == 'Stage B')
        self.assertTrue(satge_b['is_won'])
