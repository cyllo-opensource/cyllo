# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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

from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestShopfloorRepair(TransactionCase):
    """Tests for cyllo_shopfloor_repair models and wizards."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create partner/customer
        cls.customer = cls.env['res.partner'].create({
            'name': 'Repair Customer',
            'email': 'customer@repairtest.com',
        })

        # Create products
        cls.product_to_repair = cls.env['product.product'].create({
            'name': 'Damaged Device',
            'type': 'product',
        })
        cls.spare_part = cls.env['product.product'].create({
            'name': 'Spare Screen',
            'type': 'product',
        })

    def test_repair_order_action_open_repair_floor(self):
        """Test action_open_repair_floor returns the repair floor client/window action with context."""
        repair = self.env['repair.order'].create({
            'product_id': self.product_to_repair.id,
            'partner_id': self.customer.id,
        })

        action = repair.action_open_repair_floor()
        self.assertEqual(action.get('type'), 'ir.actions.client')
        self.assertEqual(action.get('tag'), 'repair_floor.dashboard')
        self.assertEqual(action.get('target'), 'fullscreen')
        self.assertEqual(action.get('context', {}).get('default_repair_id'), repair.id)

    def test_repair_order_action_show_repair_notes(self):
        """Test action_show_repair_notes returns the window action for notes popup view."""
        repair = self.env['repair.order'].create({
            'product_id': self.product_to_repair.id,
            'partner_id': self.customer.id,
        })

        action = repair.action_show_repair_notes()
        self.assertEqual(action.get('type'), 'ir.actions.act_window')
        self.assertEqual(action.get('res_model'), 'repair.order')
        self.assertEqual(action.get('res_id'), repair.id)
        self.assertEqual(action.get('target'), 'new')

    def test_edit_repair_line_wizard_add_product(self):
        """Test edit.repair.line.wizard correctly adds new product moves or updates existing ones."""
        repair = self.env['repair.order'].create({
            'product_id': self.product_to_repair.id,
            'partner_id': self.customer.id,
        })

        # 1. Create wizard to add a new spare part
        wizard = self.env['edit.repair.line.wizard'].create({
            'repair_id': repair.id,
            'product_id': self.spare_part.id,
            'quantity': 1.0,
            'repair_line_type': 'add',
        })

        wizard.action_edit_repair_line()

        # Check that stock.move was created with correct fields
        move = repair.move_ids.filtered(lambda m: m.product_id == self.spare_part)
        self.assertTrue(move)
        self.assertEqual(move.product_uom_qty, 1.0)
        self.assertEqual(move.repair_line_type, 'add')

        # 2. Add the same spare part again using the wizard
        wizard_repeat = self.env['edit.repair.line.wizard'].create({
            'repair_id': repair.id,
            'product_id': self.spare_part.id,
            'quantity': 2.0,
            'repair_line_type': 'add',
        })

        wizard_repeat.action_edit_repair_line()

        # Check that existing stock.move was updated (1.0 + 2.0 = 3.0)
        self.assertEqual(move.product_uom_qty, 3.0)

    def test_edit_repair_line_wizard_remove_recycle_product(self):
        """Test edit.repair.line.wizard works for remove and recycle repair line types."""
        repair = self.env['repair.order'].create({
            'product_id': self.product_to_repair.id,
            'partner_id': self.customer.id,
        })

        # Create wizard to recycle a product
        wizard_recycle = self.env['edit.repair.line.wizard'].create({
            'repair_id': repair.id,
            'product_id': self.spare_part.id,
            'quantity': 1.0,
            'repair_line_type': 'recycle',
        })

        wizard_recycle.action_edit_repair_line()

        move_recycle = repair.move_ids.filtered(lambda m: m.product_id == self.spare_part and m.repair_line_type == 'recycle')
        self.assertTrue(move_recycle)
        self.assertEqual(move_recycle.product_uom_qty, 1.0)
        self.assertEqual(move_recycle.repair_line_type, 'recycle')
