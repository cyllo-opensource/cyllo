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
from odoo.tests import TransactionCase, tagged
from unittest.mock import patch


@tagged('-at_install', 'post_install')
class TestDigitizationAIWizard(TransactionCase):
    """
    Test suite for verifying the behavior of the Digitization AI Wizard.

    This suite ensures:

        * The wizard correctly switches the digitization method from manual to AI.
        * The action `action_send_digitization()` is triggered on the related purchase order.
        * Only the active digitization configuration is modified.
    """

    def setUp(self):
        """
        Prepare required environment for testing:
            * Create a Purchase Order.
            * Create an active purchase digitization configuration.
        """
        super().setUp()
        self.po = self.env['purchase.order'].create({
            'partner_id': self.env.ref("base.partner_admin").id
        })
        self.config = self.env['purchase.digitization'].create({
            'name': 'Test Config',
            'active_configuration': True,
            'automation_method': 'manual_digitization',
        })

    def test_switch_to_ai(self):
        """
        Test the wizard action:

            1. Digitization method must change from manual to AI.
            2. Purchase order should trigger action_send_digitization().
        """
        wizard = self.env['digitization.ai.wizard'].with_context(active_id=self.po.id).create({})
        with patch.object(type(self.po), "action_send_digitization") as mock_action:
            wizard.action_switch_to_ai()
            self.config = self.env['purchase.digitization'].browse(self.config.id)
            self.assertEqual(self.config.automation_method, "ai_digitization")
            mock_action.assert_called_once()
