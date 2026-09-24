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


class TestFrontdeskDrink(TransactionCase):
    """Tests for FrontdeskDrink model."""

    def test_create_drink(self):
        drink = self.env['frontdesk.drink'].create({'name': 'Lemonade'})
        self.assertEqual(drink.name, 'Lemonade')
        self.assertTrue(drink.active)
        self.assertEqual(drink.sequence, 10)

    def test_drink_default_active(self):
        drink = self.env['frontdesk.drink'].create({'name': 'Juice'})
        self.assertTrue(drink.active)

    def test_drink_archive(self):
        drink = self.env['frontdesk.drink'].create({'name': 'Water'})
        drink.write({'active': False})
        self.assertFalse(drink.active)

    def test_drink_notify_users(self):
        employee = self.env['hr.employee'].create({
            'name': 'Barista',
            'work_email': 'barista@example.com',
        })
        drink = self.env['frontdesk.drink'].create({
            'name': 'Espresso',
            'notify_user_ids': [(4, employee.id)],
        })
        self.assertIn(employee, drink.notify_user_ids)

    def test_drink_ordering_by_sequence(self):
        d1 = self.env['frontdesk.drink'].create({'name': 'Zap', 'sequence': 20})
        d2 = self.env['frontdesk.drink'].create({'name': 'Aaa', 'sequence': 5})
        drinks = self.env['frontdesk.drink'].search([
            ('name', 'in', ['Zap', 'Aaa'])
        ])
        names_in_order = drinks.mapped('name')
        self.assertEqual(names_in_order.index('Aaa'), 0)
        self.assertEqual(names_in_order.index('Zap'), 1)

    def test_station_drink_selection_linkage(self):
        station = self.env['frontdesk.frontdesk'].create({
            'name': 'Drink Station',
            'is_drink': True,
        })
        drink = self.env['frontdesk.drink'].create({'name': 'Matcha'})
        station.drink_selection_ids = [(4, drink.id)]

        self.assertIn(drink, station.drink_selection_ids)

        # Visitor should see the drink in related field
        visitor = self.env['frontdesk.visitor'].new({
            'visitor_name': 'Drink Tester',
            'visitor_type': 'enquiry',
            'station_id': station.id,
        })
        self.assertIn(drink, visitor.drink_selection_ids)


class TestFrontdeskEmergencyAlert(TransactionCase):
    """Tests for FrontdeskEmergencyAlert model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.station = cls.env['frontdesk.frontdesk'].create({
            'name': 'Alert Station',
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Alert Guard',
            'work_email': 'guard@example.com',
        })

        cls.user = cls.env['res.users'].create({
            'name': 'Alert Watcher',
            'login': 'alert_watcher_test',
            'email': 'watcher@example.com',
            'groups_id': [(4, cls.env.ref('base.group_user').id)],
        })

    def test_create_emergency_alert(self):
        alert = self.env['frontdesk.emergency.alert'].create({
            'name': 'Medical Emergency',
            'station_ids': [(4, self.station.id)],
            'default_message': 'Call an ambulance!',
        })
        self.assertEqual(alert.name, 'Medical Emergency')
        self.assertTrue(alert.active)
        self.assertIn(self.station, alert.station_ids)

    def test_alert_default_active(self):
        alert = self.env['frontdesk.emergency.alert'].create({
            'name': 'Test Active',
            'station_ids': [(4, self.station.id)],
            'default_message': 'Test.',
        })
        self.assertTrue(alert.active)

    def test_alert_with_employee_recipients(self):
        alert = self.env['frontdesk.emergency.alert'].create({
            'name': 'Employee Alert',
            'station_ids': [(4, self.station.id)],
            'default_message': 'Emergency!',
            'recipient_employee_ids': [(4, self.employee.id)],
        })
        self.assertIn(self.employee, alert.recipient_employee_ids)

    def test_alert_with_user_recipients(self):
        alert = self.env['frontdesk.emergency.alert'].create({
            'name': 'User Alert',
            'station_ids': [(4, self.station.id)],
            'default_message': 'Emergency!',
            'recipient_user_ids': [(4, self.user.id)],
        })
        self.assertIn(self.user, alert.recipient_user_ids)

    def test_alert_with_discuss_channel(self):
        channel = self.env['discuss.channel'].create({
            'name': 'Emergency Channel',
            'channel_type': 'channel',
        })
        alert = self.env['frontdesk.emergency.alert'].create({
            'name': 'Channel Alert',
            'station_ids': [(4, self.station.id)],
            'default_message': 'Channel emergency!',
            'recipient_channel_ids': [(4, channel.id)],
        })
        self.assertIn(channel, alert.recipient_channel_ids)

    def test_archive_alert_removes_from_station_has_alert(self):
        station = self.env['frontdesk.frontdesk'].create({
            'name': 'Archive Test Station',
        })
        alert = self.env['frontdesk.emergency.alert'].create({
            'name': 'Temp Alert',
            'station_ids': [(4, station.id)],
            'default_message': 'Temp!',
            'active': True,
        })
        station._compute_has_emergency_alert()
        self.assertTrue(station.has_emergency_alert)

        alert.write({'active': False})
        station._compute_has_emergency_alert()
        self.assertFalse(station.has_emergency_alert)

    def test_alert_multiple_stations(self):
        station2 = self.env['frontdesk.frontdesk'].create({'name': 'Station Beta'})
        alert = self.env['frontdesk.emergency.alert'].create({
            'name': 'Multi-Station Alert',
            'station_ids': [(4, self.station.id), (4, station2.id)],
            'default_message': 'Multi alert!',
        })
        self.assertIn(self.station, alert.station_ids)
        self.assertIn(station2, alert.station_ids)
