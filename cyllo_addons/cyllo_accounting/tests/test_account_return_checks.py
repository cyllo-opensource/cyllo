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

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAccountReturnChecks(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAccountReturnChecks, cls).setUpClass()
        cls.journal = cls.env['account.journal'].create({
            'name': 'Validation Test Journal',
            'type': 'general',
            'code': 'VALTST',
        })
        cls.tax_return = cls.env['account.return'].create({
            'periodicity': 'monthly',
            'date_from': date.today(),
            'date_to': date.today(),
            'journal_id': cls.journal.id,
        })

    def test_model_loaded(self):
        self.assertTrue('account.return.checks' in self.env)

    def test_invalid_validation_domain_raises(self):
        template = self.env['account.return.checks'].create({
            'name': 'Invalid domain',
            'model_name': 'account.move',
            'domain': '[',
        })
        validation = self.env['account.return.validation'].create({
            'template_id': template.id,
            'return_id': self.tax_return.id,
        })

        with self.assertRaises(ValidationError):
            validation._get_failing_records_domain()

    def test_non_list_validation_domain_raises(self):
        template = self.env['account.return.checks'].create({
            'name': 'Non-list domain',
            'model_name': 'account.move',
            'domain': "'not a domain'",
        })
        validation = self.env['account.return.validation'].create({
            'template_id': template.id,
            'return_id': self.tax_return.id,
        })

        with self.assertRaises(ValidationError):
            validation._get_failing_records_domain()
