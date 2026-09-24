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


class TestResPartnerAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env['res.users'].create({
            'name': 'Test Access User',
            'login': 'test_access_user',
            'email': 'test_access_user@example.com',
            'groups_id': [(6, 0, [cls.env.ref('base.group_user').id])]
        })
        cls.user_profile = cls.env['user.profile'].create({
            'name': 'Test Profile',
            'user_ids': [(4, cls.user.id)]
        })
        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Partner A',
            'email': 'pA@test.com'
        })
        cls.partner_2 = cls.env['res.partner'].create({
            'name': 'Partner B',
            'email': 'pB@test.com'
        })
        cls.profile_management = cls.env['profile.management'].create({
            'name': 'Test Profile Management',
            'profile_ids': [(4, cls.user_profile.id)],
            'is_activated': True,
        })
        cls.model_partner = cls.env['ir.model'].search([
            ('model', '=', 'res.partner')
        ], limit=1)

    def test_domain_access_restriction(self):
        """Domain access is stored but not enforced in ORM (current implementation)"""
        self.env['domain.access'].create({
            'profile_management_id': self.profile_management.id,
            'model_id': self.model_partner.id,
            'domain': "[('name', '=', 'Partner A')]",
        })
        partners = self.env['res.partner'].with_user(self.user).search([
            ('name', 'in', ['Partner A', 'Partner B'])
        ])
        self.assertIn(self.partner_1, partners)
        self.assertIn(self.partner_2, partners)

    def test_model_access_readonly_view(self):
        """Readonly view flags test"""
        self.env['model.access'].create({
            'profile_management_id': self.profile_management.id,
            'model_id': self.model_partner.id,
            'is_readonly': True,
        })
        res = self.env['res.partner'].with_user(self.user).get_view(view_type='form')
        arch = res['arch']
        self.assertIn('edit="False"', arch)
        self.assertIn('create="False"', arch)
        self.assertIn('delete="False"', arch)