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
from odoo.exceptions import UserError


class TestFrontdeskStation(TransactionCase):
    """Tests for FrontdeskFrontdesk (Station) model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.station = cls.env['frontdesk.frontdesk'].create({
            'name': 'East Wing Reception',
            'is_host': True,
            'is_drink': True,
        })

        cls.drink = cls.env['frontdesk.drink'].create({'name': 'Tea'})
        cls.station.drink_selection_ids = [(4, cls.drink.id)]

        cls.alert = cls.env['frontdesk.emergency.alert'].create({
            'name': 'Fire Alert',
            'station_ids': [(4, cls.station.id)],
            'default_message': 'Fire! Please evacuate.',
            'active': True,
        })

    # ------------------------------------------------------------------
    # Visitor count
    # ------------------------------------------------------------------

    def test_visitor_count_counts_active_visitors(self):
        """visitor_count should count only planned/checked_in visitors."""
        initial = self.station.visitor_count

        v1 = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Count A',
            'visitor_type': 'enquiry',
            'station_id': self.station.id,
        })
        v2 = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Count B',
            'visitor_type': 'enquiry',
            'station_id': self.station.id,
        })

        self.station._compute_visitor_count()
        self.assertEqual(self.station.visitor_count, initial + 2)

        # Check one in then out — should be excluded from count
        v1.action_check_in()
        v1.action_check_out()
        self.station._compute_visitor_count()
        self.assertEqual(self.station.visitor_count, initial + 1)

    def test_visitor_count_excludes_cancelled(self):
        v = self.env['frontdesk.visitor'].create({
            'visitor_name': 'Cancelled',
            'visitor_type': 'enquiry',
            'station_id': self.station.id,
        })
        v.action_cancel()
        self.station._compute_visitor_count()
        # Cancelled should not count
        for vis in self.station.visitor_ids:
            self.assertNotIn(vis.state, ('cancelled',) if vis == v else ())

    # ------------------------------------------------------------------
    # has_emergency_alert
    # ------------------------------------------------------------------

    def test_has_emergency_alert_true_when_alert_configured(self):
        self.station._compute_has_emergency_alert()
        self.assertTrue(self.station.has_emergency_alert)

    def test_has_emergency_alert_false_when_no_alert(self):
        station_no_alert = self.env['frontdesk.frontdesk'].create({
            'name': 'Isolated Booth',
        })
        station_no_alert._compute_has_emergency_alert()
        self.assertFalse(station_no_alert.has_emergency_alert)

    def test_has_emergency_alert_false_when_alert_inactive(self):
        self.alert.write({'active': False})
        self.station._compute_has_emergency_alert()
        self.assertFalse(self.station.has_emergency_alert)
        # Restore
        self.alert.write({'active': True})

    # ------------------------------------------------------------------
    # Action methods return correct structure
    # ------------------------------------------------------------------

    def test_action_open_visitors_returns_action(self):
        result = self.station.action_open_visitors()
        self.assertEqual(result['res_model'], 'frontdesk.visitor')
        self.assertIn(('station_id', '=', self.station.id), result['domain'])

    def test_action_quick_register_visitor_returns_action(self):
        result = self.station.action_quick_register_visitor()
        self.assertEqual(result['res_model'], 'frontdesk.visitor')
        self.assertEqual(result['context']['default_station_id'], self.station.id)

    def test_action_configure_drinks_returns_action(self):
        result = self.station.action_configure_drinks()
        self.assertEqual(result['res_model'], 'frontdesk.drink')

    def test_action_trigger_emergency_returns_wizard_action(self):
        result = self.station.action_trigger_emergency()
        self.assertEqual(result['res_model'], 'frontdesk.emergency.wizard')
        self.assertEqual(result['context']['default_station_id'], self.station.id)

    def test_action_trigger_emergency_raises_when_no_alert(self):
        station_no_alert = self.env['frontdesk.frontdesk'].create({
            'name': 'No Alert Station',
        })
        with self.assertRaises(UserError):
            station_no_alert.action_trigger_emergency()
