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
from datetime import date


class TestResCompany(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestResCompany, cls).setUpClass()
        cls.company = cls.env.user.company_id
        cls.FiscalYear = cls.env['account.fiscal.year']
        
        cls.fiscal_year = cls.FiscalYear.create({
            'name': 'Company Fiscal Year 2024',
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
            'company_id': cls.company.id,
        })

    def test_compute_fiscalyear_dates_within_fiscal_year(self):
        """Test compute_fiscalyear_dates when a fiscal year covers the date."""
        result = self.company.compute_fiscalyear_dates(date(2024, 6, 15))
        self.assertEqual(result.get('date_from'), date(2024, 1, 1))
        self.assertEqual(result.get('date_to'), date(2024, 12, 31))

    def test_compute_fiscalyear_dates_outside_fiscal_year(self):
        """Test compute_fiscalyear_dates when no explicit fiscal year covers the date."""
        self.company.fiscalyear_last_day = 31
        self.company.fiscalyear_last_month = '12'
        result = self.company.compute_fiscalyear_dates(date(2025, 6, 15))
        self.assertEqual(result.get('date_from'), date(2025, 1, 1))
        self.assertEqual(result.get('date_to'), date(2025, 12, 31))
