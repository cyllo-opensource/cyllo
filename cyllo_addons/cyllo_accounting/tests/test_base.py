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
from lxml import etree

class TestBase(TransactionCase):

    def test_get_default_reconcile_view(self):
        """Test _get_default_reconcile_view function."""
        # Using res.partner as it inherits base and has _rec_name 'name' by default
        base_model = self.env['res.partner']
        view = base_model._get_default_reconcile_view()
        self.assertEqual(view.tag, 'tree')
        self.assertTrue(len(view) > 0)
        self.assertEqual(view[0].tag, 'field')
        self.assertEqual(view[0].get('name'), base_model._rec_name_fallback())
