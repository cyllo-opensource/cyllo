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

class TestPartnerUnlink(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_with_participant = cls.env['res.partner'].create({'name': 'Partner with Participant'})
        cls.participant = cls.env['marketing.participant'].create({
            'record_id': cls.partner_with_participant.id,
            'record': f'res.partner,{cls.partner_with_participant.id}',
        })
        cls.partner_without_participant = cls.env['res.partner'].create({'name': 'Partner without Participant'})

    def test_unlink(self):
        """
        Test unlinking a partner linked to a marketing participant.
        - It should raise a ValidationError and the record should remain in the database.
        Test unlinking a partner not linked to any participant.
        - It should succeed and the record should be removed from the database.
        """
        _logger.info('Starts test_unlink')
        with self.assertRaises(ValidationError):
            self.partner_with_participant.unlink()

        self.assertTrue(
            self.env['res.partner'].search([('id', '=', self.partner_with_participant.id)]),
            "Partner linked to a participant should not be deleted."
        )
        self.partner_without_participant.unlink()
        self.assertFalse(
            self.env['res.partner'].search([('id', '=', self.partner_without_participant.id)]),
            "Partner not linked to a participant should be deletable."
        )
        _logger.info('Ends test_unlink')
