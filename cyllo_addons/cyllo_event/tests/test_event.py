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


class TestEvent(TransactionCase):

    def test_event_create_disables_website_fields(self):
        vals = {'name': 'Test Event'}
        if 'website_menu' in self.env['event.event']._fields:
            vals['website_menu'] = True
        if 'menu_register_cta' in self.env['event.event']._fields:
            vals['menu_register_cta'] = True
        event = self.env['event.event'].create(vals)
        if 'website_menu' in event._fields:
            self.assertFalse(event.website_menu)
        if 'menu_register_cta' in event._fields:
            self.assertFalse(event.menu_register_cta)

    def test_event_write_disables_website_fields(self):
        event = self.env['event.event'].create({
            'name': 'Test Event',
        })
        vals = {}
        if 'website_menu' in event._fields:
            vals['website_menu'] = True
        if 'menu_register_cta' in event._fields:
            vals['menu_register_cta'] = True
        if vals:
            event.write(vals)
            if 'website_menu' in event._fields:
                self.assertFalse(event.website_menu)
            if 'menu_register_cta' in event._fields:
                self.assertFalse(event.menu_register_cta)