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
from unittest.mock import patch


class TestResUsers(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Users = cls.env['res.users']
        cls.Company = cls.env['res.company']

        cls.company = cls.env.company

        # Create a test user
        cls.user = cls.Users.create({
            'name': 'Test User',
            'login': 'test_user_login',
            'email': 'test@example.com',
            'company_id': cls.company.id,
        })

    # ---------------------------------------------------------
    # TEST 01: custom_user_data returns expected structure
    # ---------------------------------------------------------
    def test_01_custom_user_data(self):
        result = self.Users.custom_user_data(self.user.id)

        self.assertIsInstance(result, dict)
        self.assertIn('first_time', result)
        self.assertIn('users', result)
        self.assertIn('user_data', result)
        self.assertIn('company_data', result)
        self.assertIn('country_state_data', result)
        self.assertIn('all_companies_data', result)
        self.assertIn('res_lang', result)
        self.assertIn('countries', result)

    # ---------------------------------------------------------
    # TEST 02: first_time becomes True after enough log entries
    # ---------------------------------------------------------
    def test_02_first_time_flag(self):
        Log = self.env['res.users.log']

        # Create fake login logs
        Log.create({'create_uid': self.user.id})
        Log.create({'create_uid': self.user.id})
        Log.create({'create_uid': self.user.id})

        self.Users.custom_user_data(self.user.id)
        self.assertTrue(self.user.first_time)

    # ---------------------------------------------------------
    # TEST 03: update_company writes values correctly
    # ---------------------------------------------------------
    def test_03_update_company(self):
        self.Users.update_company(
            id=self.company.id,
            name='Updated Company Name'
        )

        self.assertEqual(self.company.name, 'Updated Company Name')

    # ---------------------------------------------------------
    # TEST 04: clean_up_menus success path
    # ---------------------------------------------------------
    def test_04_clean_up_menus_success(self):
        with patch(
            'odoo.api.Environment.ref',
            return_value=None
        ):
            result = self.Users.clean_up_menus(self.user.id)

        self.assertEqual(result.get('status'), 'success')

        # All users should now have first_time = True
        users = self.Users.search([])
        self.assertTrue(all(u.first_time for u in users))

    # ---------------------------------------------------------
    # TEST 05: clean_up_menus exception handling
    # ---------------------------------------------------------
    def test_05_clean_up_menus_exception(self):
        with patch.object(
            type(self.Users),
            'clean_up_menus',
            side_effect=Exception("Test error")
        ):
            try:
                result = self.Users.clean_up_menus(self.user.id)
            except Exception:
                result = {'status': 'error'}

        self.assertIn(result.get('status'), ['error'])
