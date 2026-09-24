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

class TestResConfigSettings(TransactionCase):
    """
    Test cases for barcode-related configuration settings, specifically 
    focusing on barcode printing actions.
    """

    def setUp(self):
        """
        Setup test environment for configuration settings.
        """
        super(TestResConfigSettings, self).setUp()
        self.ConfigSettings = self.env['res.config.settings']

    def test_action_print_barcode(self):
        """
        Test the action that initiates barcode printing for products.
        """
        config = self.ConfigSettings.create({})
        action = config.with_context(model='product.product').action_print_barcode()
        
        self.assertIn(action['type'], ['ir.actions.report', 'ir.actions.act_window'])
        if action['type'] == 'ir.actions.report':
             self.assertEqual(action['report_name'], 'cyllo_barcode.report_barcode_pdf_download')
             self.assertEqual(action['data']['mode'], 'product.product')
