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
from . common import TestCommon


class TestConsolidationJournal(TestCommon):
    """Test methods of the Consolidation Journal"""

    def test_compute_currency_id(self):
        cons_journal = self.cons_journal
        cons_journal._compute_currency_id()
        self.assertEqual(cons_journal.currency_id,  cons_journal.chart_id.currency_id)

    def test_compute_total(self):
        cons_journal = self.cons_journal
        cons_journal._compute_total()
        self.assertEqual(cons_journal.total, 0.0)



