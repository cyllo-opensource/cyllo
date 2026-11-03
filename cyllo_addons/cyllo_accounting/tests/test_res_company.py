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
from datetime import date

from odoo.tests.common import TransactionCase


class TestResCompany(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestResCompany, cls).setUpClass()
        cls.company = cls.env.user.company_id
        cls.FiscalYear = cls.env['account.fiscal.year']
        cls.today = date.today()
        cls.current_year = cls.today.year
        cls.fiscal_year = cls.FiscalYear.create({
            'name': 'Company Fiscal Year %s' % cls.current_year,
            'start_date': date(cls.current_year, 1, 1),
            'end_date': date(cls.current_year, 12, 31),
            'company_id': cls.company.id,
        })

    def test_compute_fiscalyear_dates_within_fiscal_year(self):
        """Test compute_fiscalyear_dates when a fiscal year covers the date."""
        result = self.company.compute_fiscalyear_dates(self.today)
        self.assertEqual(result.get('date_from'), date(self.current_year, 1, 1))
        self.assertEqual(result.get('date_to'), date(self.current_year, 12, 31))

    def test_compute_fiscalyear_dates_outside_fiscal_year(self):
        """Test compute_fiscalyear_dates when no explicit fiscal year covers the date."""
        self.company.fiscalyear_last_day = 31
        self.company.fiscalyear_last_month = '12'
        next_year = self.current_year + 1
        result = self.company.compute_fiscalyear_dates(
            self.today.replace(year=next_year, day=1)
        )
        self.assertEqual(result.get('date_from'), date(next_year, 1, 1))
        self.assertEqual(result.get('date_to'), date(next_year, 12, 31))
