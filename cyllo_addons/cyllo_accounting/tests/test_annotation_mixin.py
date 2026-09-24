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

class TestAnnotationMixin(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAnnotationMixin, cls).setUpClass()
        # Since annotation.mixin is an abstract or mixin model, we can test it using a model that inherits it
        # account.account inherits annotation.mixin
        cls.Account = cls.env['account.account']
        cls.record = cls.Account.create({
            'name': 'Test Account Annotation',
            'code': '999999.TEST.ANN',
            'account_type': 'asset_receivable',
        })

    def test_write_annotations(self):
        """Test write_annotations function."""
        self.record.write_annotations('1', 'Test Annotation')
        self.assertEqual(self.record.annotations.get('1'), 'Test Annotation')

    def test_remove_annotations(self):
        """Test remove_annotations function."""
        self.record.write_annotations('1', 'Test Annotation')
        self.assertEqual(self.record.annotations.get('1'), 'Test Annotation')
        self.record.remove_annotations('1')
        self.assertNotIn('1', self.record.annotations or {})
