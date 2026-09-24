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
from odoo.tests import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestFieldServiceRequestCount(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({'name': 'Portal Partner'})
        cls.skill_category = cls.env['field.service.skill.category'].create({
            'name': 'Electrical',
        })
        cls.portal_user = cls.env['res.users'].create({
            'name': 'Portal User',
            'login': 'portal@test.com',
            'password': 'portal',
            'email': 'portal@test.com',
            'partner_id': cls.partner.id,
            'groups_id': [(6, 0, [cls.env.ref('base.group_portal').id])],
        })

        # Create 2 field service requests for this partner
        cls.env['field.service.request'].create([
            {
                'name': 'Service Request 1',
                'partner_id': cls.portal_user.partner_id.id,
                'skill_category_id': cls.skill_category.id,
                'state': 'draft',
            },
            {
                'name': 'Service Request 2',
                'partner_id': cls.portal_user.partner_id.id,
                'skill_category_id': cls.skill_category.id,
                'state': 'completed',
            },
        ])

    def test_fs_req_count(self):
        """
        Verify that the portal user can access the Field Service Request
        portal page and view all their related service requests.

        This test:
          - Authenticates as the portal user.
          - Opens the '/my/field_service_request' route.
          - Confirms the page loads successfully (HTTP 200).
          - Ensures that both created Field Service Requests appear in the page content.
        """
        self.authenticate('portal@test.com', 'portal')
        response = self.url_open('/my/field_service_request', timeout=30)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Service Request 1', response.content)
        self.assertIn(b'Service Request 2', response.content)
