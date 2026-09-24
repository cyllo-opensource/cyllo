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
from odoo.exceptions import ValidationError
from odoo.addons.cyllo_field_service.tests.common import TestCylloFieldService


class TestFsServiceChecklist(TestCylloFieldService):

    def test_action_mark_as_done(self):
        """When action_mark_as_done function called if state in
         field.service.request is 'in progress' then status is completd"""
        checklist2 = self.env['field.service.checklist'].create({
            'status': 'pending',
            'required': True,
            'service_cost': 100,
            'field_service_request_id': self.service_request4.id,
            'product_id': self.product.id
        })
        checklist3 = self.env['field.service.checklist'].create({
            'status': 'pending',
            'required': True,
            'service_cost': 100,
            'field_service_request_id': self.service_request3.id,
            'product_id': self.product.id
        })
        checklist2.action_mark_as_done()
        self.assertEqual(checklist2.status, 'completed')
        with self.assertRaises(ValidationError,
                               msg='To mark job as done, assign workers and start service'):
            checklist3.action_mark_as_done()
