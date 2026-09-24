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
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestHelpdeskStock(TransactionCase):
    """Test suite for the Cyllo Helpdesk Stock Return/Replacement integration."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Stock Test Customer',
            'email': 'stock@test.com',
        })

        # Create helpdesk team
        cls.team = cls.env['helpdesk.team'].create({
            'name': 'Stock Support Team',
        })

        # Create sale order
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
        })

        # Find picking types
        cls.picking_type_out = cls.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
        ], limit=1)

        cls.picking_type_in = cls.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
        ], limit=1)

        # Create a location
        cls.location = cls.env['stock.location'].create({
            'name': 'Test Location',
            'usage': 'internal',
        })

        # Create a test product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
        })

    def _create_picking(self, picking_type, state='draft', sale_id=False, helpdesk_ticket_id=False):
        """Helper to create a stock picking."""
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner.id,
            'picking_type_id': picking_type.id,
            'location_id': self.location.id,
            'location_dest_id': self.location.id,
            'helpdesk_ticket_id': helpdesk_ticket_id,
        })
        if state != 'draft':
            # Create a stock move to satisfy Odoo's _compute_state requirements
            move = self.env['stock.move'].create({
                'name': 'Test Move',
                'product_id': self.product.id,
                'product_uom_qty': 1.0,
                'product_uom': self.product.uom_id.id,
                'picking_id': picking.id,
                'location_id': self.location.id,
                'location_dest_id': self.location.id,
            })
            # Force the move and the picking state directly in DB
            self.env.cr.execute(
                "UPDATE stock_move SET state = %s WHERE id = %s",
                [state, move.id]
            )
            self.env.cr.execute(
                "UPDATE stock_picking SET state = %s WHERE id = %s",
                [state, picking.id]
            )
            move.invalidate_recordset(['state'])
            picking.invalidate_recordset(['state'])

        if sale_id:
            self.env.cr.execute(
                "UPDATE stock_picking SET sale_id = %s WHERE id = %s",
                [sale_id, picking.id]
            )
            picking.invalidate_recordset(['sale_id'])
        return picking

    def test_picking_compute_and_autolink(self):
        """Test that creating a picking with helpdesk_ticket_id auto-links it and computes count."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Picking Auto-Link Ticket',
            'team_id': self.team.id,
        })

        picking = self._create_picking(self.picking_type_out, helpdesk_ticket_id=ticket.id)

        ticket._compute_picking_count()
        self.assertEqual(ticket.picking_count, 1)
        self.assertIn(picking, ticket.picking_ids)

    def test_action_create_return_validation(self):
        """Test validation and error raising on action_create_return."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Return Validation Ticket',
            'team_id': self.team.id,
        })

        # No sale order selected
        with self.assertRaises(UserError):
            ticket.action_create_return()

        # Sale order selected but no done delivery
        ticket.sale_order_id = self.sale_order.id
        with self.assertRaises(UserError):
            ticket.action_create_return()

    def test_action_create_return_single_picking(self):
        """Test action_create_return when there is exactly one done delivery order."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Single Return Ticket',
            'team_id': self.team.id,
            'sale_order_id': self.sale_order.id,
        })

        # Create exactly one done delivery picking
        picking = self._create_picking(self.picking_type_out, state='done', sale_id=self.sale_order.id)

        action = ticket.action_create_return()
        # Should return the return wizard window action
        self.assertEqual(action.get('context', {}).get('active_model'), 'stock.picking')
        self.assertEqual(action.get('context', {}).get('default_helpdesk_ticket_id'), ticket.id)

    def test_action_create_return_multiple_pickings(self):
        """Test action_create_return when there are multiple done deliveries."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Multiple Return Ticket',
            'team_id': self.team.id,
            'sale_order_id': self.sale_order.id,
        })

        # Create two done delivery pickings
        picking1 = self._create_picking(self.picking_type_out, state='done', sale_id=self.sale_order.id)
        picking2 = self._create_picking(self.picking_type_out, state='done', sale_id=self.sale_order.id)

        action = ticket.action_create_return()
        # Should open the helpdesk.ticket.return.wizard form view
        self.assertEqual(action.get('res_model'), 'helpdesk.ticket.return.wizard')
        self.assertEqual(action.get('view_mode'), 'form')
        self.assertEqual(action.get('context', {}).get('default_ticket_id'), ticket.id)

    def test_action_view_pickings(self):
        """Test action_view_pickings return action domain."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'View Picking Ticket',
            'team_id': self.team.id,
        })
        picking = self._create_picking(self.picking_type_out, helpdesk_ticket_id=ticket.id)
        ticket._compute_picking_count()

        action = ticket.action_view_pickings()
        self.assertEqual(action.get('view_mode'), 'list,form')
        self.assertEqual(action.get('domain'), [('id', 'in', [picking.id])])

    def test_team_returns_compute_and_view(self):
        """Test return_count computation and view action for helpdesk.team."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Team Returns Ticket',
            'team_id': self.team.id,
        })

        # Create an incoming (return) picking linked to this ticket
        self._create_picking(self.picking_type_in, helpdesk_ticket_id=ticket.id)

        self.team._compute_return_count()
        self.assertEqual(self.team.return_count, 1)

        action = self.team.action_view_team_returns()
        self.assertEqual(action.get('res_model'), 'stock.picking')
        self.assertEqual(action.get('view_mode'), 'tree,form')
        self.assertIn(('helpdesk_ticket_id.team_id', '=', self.team.id), action.get('domain', []))

    def test_return_wizard_action_confirm(self):
        """Test confirmation in the helpdesk ticket return wizard."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Wizard Return Ticket',
            'team_id': self.team.id,
        })
        picking = self._create_picking(self.picking_type_out, state='done')

        wizard = self.env['helpdesk.ticket.return.wizard'].create({
            'ticket_id': ticket.id,
            'sale_order_id': self.sale_order.id,
            'picking_id': picking.id,
        })

        action = wizard.action_confirm()
        self.assertEqual(action.get('context', {}).get('active_model'), 'stock.picking')
        self.assertEqual(action.get('context', {}).get('active_id'), picking.id)
        self.assertEqual(action.get('context', {}).get('default_helpdesk_ticket_id'), ticket.id)

    def test_stock_return_picking_override(self):
        """Test that stock.return.picking override successfully assigns the helpdesk_ticket_id."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Stock Return Override Ticket',
            'team_id': self.team.id,
        })
        picking = self._create_picking(self.picking_type_out, state='done')

        # Instantiate stock.return.picking transient model
        return_wiz = self.env['stock.return.picking'].with_context(
            active_model='stock.picking',
            active_id=picking.id,
            active_ids=[picking.id],
            default_helpdesk_ticket_id=ticket.id,
        ).create({
            'picking_id': picking.id,
        })

        # Mock the super() method by creating a dummy picking return
        # Since _create_returns uses super() and writes to the new picking:
        dummy_returned_picking = self._create_picking(self.picking_type_in)
        
        from unittest.mock import patch
        with patch('odoo.addons.stock.wizard.stock_picking_return.ReturnPicking._create_returns', return_value=(dummy_returned_picking.id, self.picking_type_in.id)):
            new_picking_id, pick_type_id = return_wiz._create_returns()

        self.assertEqual(new_picking_id, dummy_returned_picking.id)
        self.assertEqual(dummy_returned_picking.helpdesk_ticket_id, ticket)
