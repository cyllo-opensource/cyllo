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
import logging

from odoo.exceptions import ValidationError
from odoo.tests import common

_logger = logging.getLogger(__name__)

class TestMarketingFilter(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        """Super setUpClass to create records to test fields in
            marketing_filter.

           Creates a valid marketing filter.
        """
        super().setUpClass()
        cls.valid_filter = cls.env['marketing.filter'].create({
            'name': 'Valid Filter',
            'user_id': cls.env.user.id,
            'model_id': cls.env.ref('hr.model_hr_department').id,
            'domain': [('id', '=', 1)],
        })

    def test_check_domain(self):
        """
            Test the _check_domain method.

            Checks if the method correctly validates the domain for the filter.
        """
        _logger.info('Starts test_check_domain')
        self.valid_filter._check_domain()
        vals = {
            'name': 'Invalid Filter',
            'user_id': self.env.user.id,
            'model_id': self.env.ref('mail.model_mail_thread_cc').id,
            'domain': [("id", ">=", 1)],
        }
        with self.assertRaises(ValidationError):
            self.env['marketing.filter'].sudo().create(vals)
        _logger.info('Ends test_check_domain')

