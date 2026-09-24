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
from odoo.exceptions import UserError
from odoo.addons.cyllo_asset_management.tests.common import TestCommon


class TestAssetItem(TestCommon):

    def test_onchange_method_duration(self):
        """Test for _onchange_method_duration"""
        with self.assertRaises(UserError):
            self.item_id.method_duration = -5

    def test_compute_brand_ids(self):
        """Test for _compute_brand_ids function"""
        item_id = self.item_id
        self.asset_type.brand_ids = self.brand.ids
        item_id.asset_type_id = self.asset_type.id
        item_id._compute_brand_ids()
        self.assertEqual(item_id.brand_ids.ids, item_id.asset_type_id.brand_ids.ids)

