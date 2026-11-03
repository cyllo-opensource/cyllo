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
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestAccountJournal(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountJournal, cls).setUpClass()
        cls.Journal = cls.env['account.journal']
        cls.journal = cls.Journal.create({
            'name': 'Bank Journal',
            'code': 'BNK99',
            'type': 'bank',
        })

    def test_action_new_transaction(self):
        result = self.journal.action_new_transaction()
        self.assertEqual(result.get('context').get('default_journal_id'), self.journal.id)

    def test_pull_bank_statements_skips_unconfigured_journal(self):
        """Do not fetch statements for journals without a provider account."""
        with patch.object(type(self.journal), '_create_bank_statements') as create_statements:
            self.journal._pull_bank_statements()

        create_statements.assert_not_called()
