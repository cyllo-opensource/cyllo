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


class TestCylloAiConfig(TransactionCase):
    """Tests for cyllo.ai.config: multiple provider profiles, one active."""

    def setUp(self):
        super().setUp()
        self.Config = self.env['cyllo.ai.config']
        self.llm = self.env['cyllo.llm'].create({
            'name': 'gpt-4o-mini',
            'display_name': 'GPT 4o Mini',
            'wrapper': 'ChatOpenAI',
        })

    def test_get_with_no_active_config(self):
        """_get() is an empty recordset when nothing is selected yet."""
        self.assertFalse(self.Config._get())
        self.Config.create({'name': 'Unused', 'provider': 'ChatOpenAI'})
        self.assertFalse(self.Config._get())

    def test_only_one_config_can_be_active(self):
        """Marking a config active on create or write deselects every other one."""
        first = self.Config.create({'name': 'First', 'is_active': True})
        self.assertEqual(self.Config._get(), first)

        second = self.Config.create({'name': 'Second', 'is_active': True})
        self.assertFalse(first.is_active)
        self.assertEqual(self.Config._get(), second)

        first.write({'is_active': True})
        self.assertFalse(second.is_active)
        self.assertEqual(self.Config._get(), first)

    def test_is_configured_openai(self):
        """is_configured requires provider + key + a model."""
        cfg = self.Config.create({'name': 'OpenAI'})
        cfg.write({'provider': 'ChatOpenAI', 'api_key': 'sk-testkey123'})
        self.assertFalse(cfg.is_configured)  # no model yet
        cfg.write({'llm_model_id': self.llm.id})
        self.assertTrue(cfg.is_configured)
        cfg.write({'api_key': False})
        self.assertFalse(cfg.is_configured)

    def test_is_configured_openrouter(self):
        """OpenRouter is configured via the free-text model field."""
        cfg = self.Config.create({'name': 'OpenRouter'})
        cfg.write({'provider': 'OpenRouter', 'api_key': 'or-testkey123'})
        self.assertFalse(cfg.is_configured)
        cfg.write({'openrouter_model': 'openai/gpt-4o'})
        self.assertTrue(cfg.is_configured)

    def test_get_config_shape(self):
        """_get_config returns the {provider, api_key, model_name} the client expects."""
        cfg = self.Config.create({'name': 'OpenAI', 'is_active': True})
        cfg.write({'provider': 'ChatOpenAI',
                   'api_key': 'sk-testkey123', 'llm_model_id': self.llm.id})
        data = self.Config._get_config()
        self.assertEqual(data, {
            'provider': 'ChatOpenAI',
            'api_key': 'sk-testkey123',
            'model_name': 'gpt-4o-mini',
        })

    def test_get_config_openrouter_model_name(self):
        cfg = self.Config.create({'name': 'OpenRouter', 'is_active': True})
        cfg.write({'provider': 'OpenRouter',
                   'api_key': 'or-testkey123', 'openrouter_model': 'openai/gpt-4o'})
        self.assertEqual(self.Config._get_config()['model_name'], 'openai/gpt-4o')

    def test_get_config_ignores_inactive_configs(self):
        """A fully-configured but non-active profile must not be used."""
        self.Config.create({
            'name': 'Configured but inactive', 'provider': 'ChatOpenAI',
            'api_key': 'sk-testkey123', 'llm_model_id': self.llm.id,
        })
        self.assertEqual(self.Config._get_config(),
                         {'provider': '', 'api_key': '', 'model_name': ''})
