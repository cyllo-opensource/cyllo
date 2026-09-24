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

class TestCylloLlm(TransactionCase):
    """
    Test cases for 'cyllo.llm' model, verifying basic CRUD operations
    for LLM configurations.
    """

    def setUp(self):
        """
        Setup test environment for LLM configuration tests.
        """
        super(TestCylloLlm, self).setUp()
        self.CylloLlm = self.env['cyllo.llm']

    def test_create_llm(self):
        """
        Test the creation of a new LLM configuration record.
        """
        llm = self.CylloLlm.create({
            'name': 'gpt-4',
            'display_name': 'GPT 4',
            'wrapper': 'ChatOpenAI'
        })
        self.assertTrue(llm.id)
        self.assertEqual(llm.name, 'gpt-4')
