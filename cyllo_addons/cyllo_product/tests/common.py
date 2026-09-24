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
from odoo import SUPERUSER_ID
from odoo.tests import common


class TestCyProduct(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        admin_env = cls.env(user=SUPERUSER_ID)

        cls.pro_approve = admin_env['product.approve'].create({
            'product_approver_id': admin_env.user.id,
            'status': 'pending',
        })

        cls.pro_temp = admin_env['product.template'].create({
            'name': 'Test pro',
            'list_price': 100.0,
            'product_approver_line_ids': [
                (6, 0, [cls.pro_approve.id])
            ],
        })
