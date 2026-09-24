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
import logging
from odoo import SUPERUSER_ID
from odoo.tests import common

_logger = logging.getLogger(__name__)


class TestCyPlanning(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        admin_env = cls.env(user=SUPERUSER_ID)

        cls.res_company = admin_env.company

        unique_login = f"user_{uuid.uuid4().hex}@test.com"
        cls.res_users = admin_env['res.users'].create({
            'name': 'Test User',
            'login': unique_login,
            'email': unique_login,
            'company_id': cls.res_company.id,
            'company_ids': [(6, 0, [cls.res_company.id])],
            'groups_id': [(6, 0, [
                admin_env.ref('base.group_user').id
            ])],
        })

        cls.allocation_type = admin_env['allocation.type'].create({
            'name': 'Type',
            'user_id': cls.res_users.id,
            'company_id': cls.res_company.id,
        })

        cls.hr_employee = admin_env['hr.employee'].create({
            'name': 'Ben John',
            'company_id': cls.res_company.id,
        })

        cls.plan_allocation = admin_env['plan.allocation'].create({
            'name': 'Ben John Type',
            'start_datetime': '2025-01-01 09:33:43',
            'end_datetime': '2025-01-01 12:33:43',
            'employee_id': cls.hr_employee.id,
            'user_id': cls.res_users.id,
            'company_id': cls.res_company.id,
            'allocation_type_id': cls.allocation_type.id,
        })
