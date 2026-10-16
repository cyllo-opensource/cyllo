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


class TestTemperatureFallback(TransactionCase):
    """temperature=0 is sent; a model that rejects it is retried without it."""

    def _resp(self, status, text=''):
        from unittest.mock import MagicMock
        r = MagicMock(status_code=status, text=text)
        return r

    def test_sends_temperature_zero(self):
        from unittest.mock import patch
        from odoo.addons.cyllo_ai.core import llm_client
        ok = self._resp(200)
        with patch.object(llm_client.requests, 'post', return_value=ok) as post:
            llm_client.LLMClient._post_with_temperature_fallback(
                'u', {}, {'model': 'm', 'temperature': 0}, 5)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs['json']['temperature'], 0)

    def test_retries_without_temperature_when_rejected(self):
        from unittest.mock import patch
        from odoo.addons.cyllo_ai.core import llm_client
        bad = self._resp(400, "Unsupported value: 'temperature' does not support 0")
        ok = self._resp(200)
        with patch.object(llm_client.requests, 'post', side_effect=[bad, ok]) as post:
            resp = llm_client.LLMClient._post_with_temperature_fallback(
                'u', {}, {'model': 'm', 'temperature': 0}, 5)
        self.assertIs(resp, ok)
        self.assertEqual(post.call_count, 2)
        self.assertNotIn('temperature', post.call_args.kwargs['json'])

    def test_other_400_is_not_retried(self):
        from unittest.mock import patch
        from odoo.addons.cyllo_ai.core import llm_client
        bad = self._resp(400, 'invalid tool schema')
        with patch.object(llm_client.requests, 'post', return_value=bad) as post:
            resp = llm_client.LLMClient._post_with_temperature_fallback(
                'u', {}, {'model': 'm', 'temperature': 0}, 5)
        self.assertIs(resp, bad)
        self.assertEqual(post.call_count, 1)
