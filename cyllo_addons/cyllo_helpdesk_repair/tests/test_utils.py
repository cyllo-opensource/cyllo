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

"""
Test utilities and factory methods for cyllo_helpdesk_repair tests.
"""


class TestDataFactory:
    """Factory class for creating test data with sensible defaults."""
    
    @staticmethod
    def create_customer(env, name=None, email=None, **kwargs):
        """Create a test customer with defaults.
        
        Args:
            env: Odoo environment
            name: Customer name (default: 'Test Customer')
            email: Customer email (default: 'test@example.com')
            **kwargs: Additional fields
            
        Returns:
            res.partner record
        """
        defaults = {
            'name': name or 'Test Customer',
            'email': email or 'test@example.com',
            'phone': '+1234567890',
        }
        defaults.update(kwargs)
        return env['res.partner'].create(defaults)
    
    @staticmethod
    def create_product(env, name=None, price=100.0, **kwargs):
        """Create a test product with defaults.
        
        Args:
            env: Odoo environment
            name: Product name (default: 'Test Product')
            price: List price (default: 100.0)
            **kwargs: Additional fields
            
        Returns:
            product.product record
        """
        defaults = {
            'name': name or 'Test Product',
            'type': 'product',
            'list_price': price,
        }
        defaults.update(kwargs)
        return env['product.product'].create(defaults)
    
    @staticmethod
    def create_helpdesk_ticket(env, team_id, customer_id=None, name=None, **kwargs):
        """Create a test helpdesk ticket.
        
        Args:
            env: Odoo environment
            team_id: Helpdesk team ID
            customer_id: Customer ID (optional)
            name: Ticket name (default: 'Test Ticket')
            **kwargs: Additional fields
            
        Returns:
            helpdesk.ticket record
        """
        defaults = {
            'name': name or 'Test Ticket',
            'team_id': team_id,
        }
        if customer_id:
            defaults['customer_id'] = customer_id
        defaults.update(kwargs)
        return env['helpdesk.ticket'].create(defaults)
    
    @staticmethod
    def create_repair_order(env, product_id, partner_id, 
                          helpdesk_ticket_id=None, **kwargs):
        """Create a test repair order.
        
        Args:
            env: Odoo environment
            product_id: Product ID to repair
            partner_id: Customer/Partner ID
            helpdesk_ticket_id: Helpdesk ticket ID (optional)
            **kwargs: Additional fields
            
        Returns:
            repair.order record
        """
        defaults = {
            'product_id': product_id,
            'partner_id': partner_id,
        }
        if helpdesk_ticket_id:
            defaults['helpdesk_ticket_id'] = helpdesk_ticket_id
        defaults.update(kwargs)
        return env['repair.order'].create(defaults)
    
    @staticmethod
    def create_sale_order(env, partner_id, product_id=None, qty=1, price=100.0, **kwargs):
        """Create a test sales order.
        
        Args:
            env: Odoo environment
            partner_id: Customer ID
            product_id: Product ID (optional)
            qty: Order line quantity (default: 1)
            price: Price unit (default: 100.0)
            **kwargs: Additional fields
            
        Returns:
            sale.order record
        """
        defaults = {
            'partner_id': partner_id,
        }
        
        if product_id:
            defaults['order_line'] = [
                (0, 0, {
                    'product_id': product_id,
                    'product_uom_qty': qty,
                    'price_unit': price,
                })
            ]
        
        defaults.update(kwargs)
        return env['sale.order'].create(defaults)


class TestAssertions:
    """Helper assertions for test cases."""
    
    @staticmethod
    def assert_action_valid(action):
        """Assert action dict has valid structure.
        
        Args:
            action: Action dict returned from action method
            
        Returns:
            True if valid, raises AssertionError otherwise
        """
        assert isinstance(action, dict), "Action should be a dict"
        assert 'res_model' in action, "Action missing res_model"
        assert 'view_mode' in action, "Action missing view_mode"
        return True
    
    @staticmethod
    def assert_context_has_defaults(context, expected_defaults):
        """Assert context contains expected default values.
        
        Args:
            context: Context dict from action
            expected_defaults: Dict of {key: value} pairs to check
            
        Returns:
            True if all defaults present, raises AssertionError otherwise
        """
        for key, expected_value in expected_defaults.items():
            assert key in context, f"Context missing key: {key}"
            assert context[key] == expected_value, \
                f"Context[{key}] = {context[key]}, expected {expected_value}"
        return True
    
    @staticmethod
    def assert_ticket_repair_linked(ticket, repair):
        """Assert ticket and repair are properly linked.
        
        Args:
            ticket: helpdesk.ticket record
            repair: repair.order record
            
        Returns:
            True if linked, raises AssertionError otherwise
        """
        assert repair in ticket.repair_ids, \
            "Repair not in ticket's repair_ids"
        assert repair.helpdesk_ticket_id == ticket, \
            "Repair's helpdesk_ticket_id doesn't point to ticket"
        return True
    
    @staticmethod
    def assert_repair_count_matches(ticket, expected_count):
        """Assert repair_count matches expected value.
        
        Args:
            ticket: helpdesk.ticket record
            expected_count: Expected repair count
            
        Returns:
            True if matches, raises AssertionError otherwise
        """
        actual_count = len(ticket.repair_ids)
        assert ticket.repair_count == expected_count, \
            f"repair_count = {ticket.repair_count}, expected {expected_count}"
        assert actual_count == expected_count, \
            f"Actual repair_ids length = {actual_count}, expected {expected_count}"
        return True


class TestScenarios:
    """Pre-built test scenarios for common workflows."""
    
    @staticmethod
    def create_ticket_with_repairs(env, num_repairs=3):
        """Create a ticket with multiple linked repairs.
        
        Args:
            env: Odoo environment
            num_repairs: Number of repairs to create
            
        Returns:
            Tuple of (ticket, repairs_list)
        """
        factory = TestDataFactory()
        
        # Create prerequisites
        customer = factory.create_customer(env)
        product = factory.create_product(env)
        team = env['helpdesk.team'].search([], limit=1) or \
               env['helpdesk.team'].create({'name': 'Test Team'})
        
        # Create ticket
        ticket = factory.create_helpdesk_ticket(
            env,
            team_id=team.id,
            customer_id=customer.id
        )
        
        # Create repairs
        repairs = []
        for i in range(num_repairs):
            repair = factory.create_repair_order(
                env,
                product_id=product.id,
                partner_id=customer.id,
                helpdesk_ticket_id=ticket.id,
            )
            repairs.append(repair)
        
        return ticket, repairs
    
    @staticmethod
    def create_multi_customer_repairs(env, num_customers=3, repairs_per_customer=2):
        """Create multiple customers with repair orders.
        
        Args:
            env: Odoo environment
            num_customers: Number of customers
            repairs_per_customer: Repairs per customer
            
        Returns:
            Dict of {customer: [repairs]}
        """
        factory = TestDataFactory()
        product = factory.create_product(env)
        team = env['helpdesk.team'].search([], limit=1) or \
               env['helpdesk.team'].create({'name': 'Test Team'})
        
        result = {}
        
        for c in range(num_customers):
            customer = factory.create_customer(env, name=f'Customer {c+1}')
            ticket = factory.create_helpdesk_ticket(
                env,
                team_id=team.id,
                customer_id=customer.id,
                name=f'Ticket {c+1}'
            )
            
            repairs = []
            for r in range(repairs_per_customer):
                repair = factory.create_repair_order(
                    env,
                    product_id=product.id,
                    partner_id=customer.id,
                    helpdesk_ticket_id=ticket.id
                )
                repairs.append(repair)
            
            result[customer] = repairs
        
        return result


class TestDataValidator:
    """Utility methods for validating test data."""
    
    @staticmethod
    def validate_ticket_repair_consistency(ticket):
        """Validate that ticket's repair data is consistent.
        
        Args:
            ticket: helpdesk.ticket record
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        # Check repair_count matches actual count
        actual_count = len(ticket.repair_ids)
        if ticket.repair_count != actual_count:
            errors.append(
                f"repair_count ({ticket.repair_count}) != "
                f"actual repairs ({actual_count})"
            )
        
        # Check all repairs point back to ticket
        for repair in ticket.repair_ids:
            if repair.helpdesk_ticket_id != ticket:
                errors.append(
                    f"Repair {repair.id} points to "
                    f"{repair.helpdesk_ticket_id}, not this ticket"
                )
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_repair_ticket_link(repair):
        """Validate that repair's ticket link is valid.
        
        Args:
            repair: repair.order record
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []
        
        if not repair.helpdesk_ticket_id:
            return True, errors
        
        ticket = repair.helpdesk_ticket_id
        
        # Check ticket knows about this repair
        if repair not in ticket.repair_ids:
            errors.append(
                f"Repair {repair.id} not in "
                f"ticket {ticket.id}'s repair_ids"
            )
        
        # Check ticket still exists
        if not ticket.exists():
            errors.append(f"Linked ticket {ticket.id} no longer exists")
        
        return len(errors) == 0, errors


# Convenience functions

def create_test_customer(env, **kwargs):
    """Shortcut to TestDataFactory.create_customer()"""
    return TestDataFactory.create_customer(env, **kwargs)


def create_test_product(env, **kwargs):
    """Shortcut to TestDataFactory.create_product()"""
    return TestDataFactory.create_product(env, **kwargs)


def create_test_ticket(env, team_id, **kwargs):
    """Shortcut to TestDataFactory.create_helpdesk_ticket()"""
    return TestDataFactory.create_helpdesk_ticket(env, team_id, **kwargs)


def create_test_repair(env, product_id, partner_id, **kwargs):
    """Shortcut to TestDataFactory.create_repair_order()"""
    return TestDataFactory.create_repair_order(env, product_id, partner_id, **kwargs)
