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
from odoo.tests.common import TransactionCase


class TestHelpdeskSubscription(TransactionCase):
    """Tests for cyllo_helpdesk_subscription bridge."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # 1. Recurrence requirement for subscription.order
        cls.recurrence = cls.env['time.based.price'].create({
            'name': 'Test Recurrence',
            'subscription_unit': 'months',
        })

        # 2. Helpdesk Teams
        cls.team_with_sub = cls.env['helpdesk.team'].create({
            'name': 'Subscription Support Team',
            'use_subscription': True,
        })
        cls.team_without_sub = cls.env['helpdesk.team'].create({
            'name': 'Regular Support Team',
            'use_subscription': False,
        })

        # 3. Partners (Company & Individual)
        cls.parent_company = cls.env['res.partner'].create({
            'name': 'Enterprise Corp',
            'is_company': True,
        })
        cls.employee_contact = cls.env['res.partner'].create({
            'name': 'Bob Employee',
            'parent_id': cls.parent_company.id,
            'is_company': False,
        })

        # 4. Helpdesk Stage
        cls.stage = cls.env['helpdesk.stage'].search([], limit=1)
        if not cls.stage:
            cls.stage = cls.env['helpdesk.stage'].create({
                'name': 'New',
                'sequence': 1,
                'is_closed': False,
            })

    def test_01_fields_existence(self):
        """Verify new configuration fields exist on the models."""
        self.assertIn('use_subscription', self.env['helpdesk.team']._fields)
        self.assertIn('use_subscription', self.env['helpdesk.ticket']._fields)
        self.assertIn('is_subscription', self.env['sale.order']._fields)

    def test_02_related_field_relay(self):
        """Verify that use_subscription relays correctly from team to ticket."""
        ticket_with_sub = self.env['helpdesk.ticket'].create({
            'name': 'Ticket 1',
            'team_id': self.team_with_sub.id,
            'stage_id': self.stage.id,
        })
        self.assertTrue(ticket_with_sub.use_subscription)

        ticket_without_sub = self.env['helpdesk.ticket'].create({
            'name': 'Ticket 2',
            'team_id': self.team_without_sub.id,
            'stage_id': self.stage.id,
        })
        self.assertFalse(ticket_without_sub.use_subscription)

    def test_03_subscription_order_counting(self):
        """Verify child-partner and parent-partner subscription order counts are resolved correctly."""
        # Create tickets
        ticket_company = self.env['helpdesk.ticket'].create({
            'name': 'Company Ticket',
            'team_id': self.team_with_sub.id,
            'customer_id': self.parent_company.id,
            'stage_id': self.stage.id,
        })
        ticket_employee = self.env['helpdesk.ticket'].create({
            'name': 'Employee Ticket',
            'team_id': self.team_with_sub.id,
            'customer_id': self.employee_contact.id,
            'stage_id': self.stage.id,
        })

        # Count initially 0
        ticket_company._compute_customer_subscription_count()
        ticket_employee._compute_customer_subscription_count()
        self.assertEqual(ticket_company.customer_subscription_count, 0)
        self.assertEqual(ticket_employee.customer_subscription_count, 0)

        # Create subscription for parent company
        self.env['subscription.order'].create({
            'partner_id': self.parent_company.id,
            'time_based_price_id': self.recurrence.id,
        })

        # Recalculate
        ticket_company._compute_customer_subscription_count()
        ticket_employee._compute_customer_subscription_count()

        # Both should see 1 because employee is child of commercial partner
        self.assertEqual(ticket_company.customer_subscription_count, 1)
        self.assertEqual(ticket_employee.customer_subscription_count, 1)

    def test_04_action_view_customer_subscriptions(self):
        """Verify the returned action from ticket to view subscriptions is pre-filtered and read-only."""
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Ticket to action',
            'team_id': self.team_with_sub.id,
            'customer_id': self.employee_contact.id,
            'stage_id': self.stage.id,
        })
        
        action = ticket.action_view_customer_subscriptions()
        
        # Verify target model and basic options
        self.assertEqual(action.get('res_model'), 'subscription.order')
        self.assertEqual(action.get('view_mode'), 'tree,form')
        
        # Verify read-only context
        context = action.get('context', {})
        self.assertFalse(context.get('create'))
        self.assertFalse(context.get('edit'))
        self.assertFalse(context.get('delete'))

        # Verify domain
        expected_domain = [('partner_id', 'child_of', ticket.customer_id.commercial_partner_id.id)]
        self.assertEqual(action.get('domain'), expected_domain)
