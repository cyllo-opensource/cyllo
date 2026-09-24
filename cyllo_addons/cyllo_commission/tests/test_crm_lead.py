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
from datetime import datetime, timedelta, date

from dateutil.utils import today

from odoo.tests.common import TransactionCase


class TestCrmLead(TransactionCase):
    """

    """
    @classmethod
    def setUp(cls):
        super().setUpClass()

        cls.stage_won = cls.env['crm.stage'].create({
            'name': 'Won',
            'sequence': 1,
            'is_won': True,
        })
        cls.stage_lost = cls.env['crm.stage'].create({
            'name': 'Lost',
            'sequence': 2,
            'is_won': False,
        })
        cls.user = cls.env['res.users'].create({
            'name': 'test User',
            'login': 'test_user',
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'test partner',
        })
    def test_compute_is_closed_on_time(self):
        """

        """
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        lead1 = self.env['crm.lead'].create({
            'name': 'Lead1',
            'stage_id': self.stage_won.id,
            'date_deadline': today,
            'date_closed': datetime.combine(yesterday, datetime.min.time()),
        })
        self.assertTrue(lead1.is_closed_on_time)
        lead2 = self.env['crm.lead'].create({
            'name': 'Lead2',
            'stage_id': self.stage_won.id,
            'date_deadline': today,
            'date_closed': datetime.combine(today, datetime.max.time()),
        })
        self.assertTrue(lead2.is_closed_on_time)
        lead3 = self.env['crm.lead'].create({
            'name': 'Lead3',
            'stage_id': self.stage_won.id,
            'date_deadline': today,
            'date_closed': datetime.combine(tomorrow, datetime.min.time()),
        })
        self.assertFalse(lead3.is_closed_on_time)
        lead4 = self.env['crm.lead'].create({
            'name': 'Lead4',
            'stage_id': self.stage_lost.id,
            'date_deadline': today,
            'date_closed': datetime.combine(yesterday, datetime.max.time()),
        })
        self.assertFalse(lead4.is_closed_on_time)

    def test_compute_is_new_customer(self):
        """

        """
        first_lead = self.env['crm.lead'].create({
            'name': 'First Lead',
            'partner_id': self.partner.id,
            'user_id': self.user.id,
            'create_date': datetime.now() - timedelta(days=1),
        })
        self.assertTrue(first_lead.is_new_customer)
        second_lead = self.env['crm.lead'].create({
            'name': 'Second Lead',
            'partner_id': self.partner.id,
            'user_id': self.user.id,
            'create_date': datetime.now(),
        })
        self.assertFalse(second_lead.is_new_customer)
        lead_no_partner = self.env['crm.lead'].create({
            'name': 'No Partner Lead',
            'user_id': self.user.id,
        })
        self.assertFalse(lead_no_partner.is_new_customer)
