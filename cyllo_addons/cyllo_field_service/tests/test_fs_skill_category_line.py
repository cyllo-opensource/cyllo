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
from odoo.addons.cyllo_field_service.tests.common import TestCylloFieldService


class TestFsSkillCategoryLine(TestCylloFieldService):

    def test_onchange_product_id(self):
        """Testcase for onchange_product_id"""
        category_line = self.env['field.service.skill.category.line'].create({
            'required': True,
            'time_required': 2.0,
            'service_cost': '',
            'currency_id': self.currency.id,
            'product_id': self.product.id
        })
        category_line._onchange_product_id()
        self.assertEqual(category_line.service_cost, self.product.lst_price,
                         msg="Error in _onchange_product_id")
