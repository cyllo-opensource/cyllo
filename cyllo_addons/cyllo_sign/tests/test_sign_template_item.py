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

class TestSignTemplateItem(TransactionCase):
    """
    Test suite for verifying the functionality of the `SignTemplateItem` model.

    Focus:
        * Ensure `get_datas()` returns correct structured information for the item.
    """

    @classmethod
    def setUpClass(cls):
        """Set up sample template item data for testing."""
        super().setUpClass()

        cls.role = cls.env['sign.role'].create({'name': 'Manager', 'color': 5})
        cls.field = cls.env['sign.field'].create({
            'name': 'Signature Field',
            'field_type': 'signature',
        })
        cls.template = cls.env['sign.template'].create({
            'name': 'Test Template',
        })
        cls.item = cls.env['sign.template.item'].create({
            'template_id': cls.template.id,
            'name': 'Manager Signature',
            'field_id': cls.field.id,
            'role_id': cls.role.id,
            'required': True,
            'page': 1,
            'position_x': 15.5,
            'position_y': 25.5,
            'width': 30,
            'height': 10,
            'placeholder': 'Sign here',
            'value': 'Sample Signature',
        })

    def test_get_datas(self):
        """Verify that `get_datas()` returns correct structured information."""
        data = self.item.get_datas()
        self.assertIsInstance(data, dict)
        expected_keys = {
            "id", "field_id", "name", "role_id", "page", "required",
            "position_x", "position_y", "width", "height", "placeholder",
            "color", "field_type", "value"
        }
        self.assertTrue(expected_keys.issubset(data.keys()))

        self.assertEqual(data["id"], self.item.id)
        self.assertEqual(data["field_id"], self.field.id)
        self.assertEqual(data["name"], self.field.name)
        self.assertEqual(data["role_id"], self.role.id)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["required"], True)
        self.assertEqual(data["position_x"], 15.5)
        self.assertEqual(data["position_y"], 25.5)
        self.assertEqual(data["width"], 30)
        self.assertEqual(data["height"], 10)
        self.assertEqual(data["placeholder"], 'Sign here')
        self.assertEqual(data["color"], self.role.color)
        self.assertEqual(data["field_type"], self.field.field_type)
        self.assertEqual(data["value"], 'Sample Signature')
