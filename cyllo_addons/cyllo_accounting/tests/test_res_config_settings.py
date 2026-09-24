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

class TestResConfigSettings(TransactionCase):

    def test_onchange_module(self):
        """Test onchange_module for cyllo_accounting_pdc."""
        settings = self.env['res.config.settings'].new({
            'module_cyllo_accounting_pdc': False
        })
        
        # Test that it triggers an error if pdc payments exist
        if 'account.pdc.payment' in self.env.registry.models:
            pdc_exists = self.env['account.pdc.payment'].sudo().search_count([])
            if pdc_exists:
                with self.assertRaises(UserError):
                    settings.onchange_module(False, 'module_cyllo_accounting_pdc')
        
        # Test other module (should pass normally)
        settings.onchange_module(False, 'module_some_other_module')
