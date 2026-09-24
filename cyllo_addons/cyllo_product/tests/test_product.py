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
import uuid
from odoo import SUPERUSER_ID
from odoo.tests import common


class TestProductProductApproval(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        admin_env = cls.env(user=SUPERUSER_ID)

        unique_login = f"user_{uuid.uuid4().hex}@test.com"
        cls.test_user = admin_env['res.users'].create({
            'name': 'Approval User',
            'login': unique_login,
            'email': unique_login,
            'groups_id': [(6, 0, [
                admin_env.ref('base.group_user').id
            ])],
        })

        cls.company = admin_env['res.company'].create({
            'name': 'Test Company',
            'product_approver_ids': [(6, 0, [cls.test_user.id])],
            'minimum_cost_limit': True,
            'cost_limit': 50.0,
            'minimum_price_limit': True,
            'price_limit': 100.0,
        })

        cls.test_user.write({
            'company_ids': [(4, cls.company.id)],  # add first
            'company_id': cls.company.id,           # then set main
        })

        cls.product = admin_env['product.product'] \
            .with_user(cls.test_user) \
            .with_company(cls.company) \
            .create({
                'name': 'Test Product',
                'standard_price': 60.0,
                'lst_price': 120.0,
            })
