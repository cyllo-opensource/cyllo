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
"""Holds one or more Cyllo AI provider configurations; exactly one is active.

Replaces the former ``res.config.settings`` fields (which stored the config in
``ir.config_parameter``). Kept in its own table so that saving AI configuration
never writes ``res.company``. On large databases a ``res.company`` write forces
Odoo to recompute stored company-related fields across millions of rows (e.g.
``account_move_line.company_currency_id``), which materialises every affected
row-id in memory and can OOM. Living on its own model side-steps that path
entirely.
"""
import logging

import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

#: Bus channel used to tell open browser sessions the AI config changed.
#: Config is global (one per instance), so an instance-wide broadcast is
#: intentional: every session should re-derive whether the chat icon shows.
CONFIG_CHANNEL = "cyllo_ai_config"


class CylloAiConfig(models.Model):
    _name = 'cyllo.ai.config'
    _description = 'Cyllo AI Configuration'
    _order = 'is_active desc, id'

    name = fields.Char(required=True)
    is_active = fields.Boolean(
        string='Use For AI', default=False,
        help='The one configuration Cyllo AI actually talks to. '
             'Selecting this on a record deselects every other one.')
    provider = fields.Selection([
        ('ChatOpenAI', 'ChatGPT'),
        ('ChatGoogleGenerativeAI', 'Google Gemini'),
        ('OpenRouter', 'OpenRouter'),
    ], string='LLM Provider')
    api_key = fields.Char(string='API Key')
    llm_model_id = fields.Many2one(
        'cyllo.llm', string='Model',
        domain="[('wrapper', '=', provider)]",
        help='Applies to ChatGPT and Google Gemini providers.')
    openrouter_model = fields.Char(
        string='OpenRouter Model',
        help='Paste the model id from https://openrouter.ai/models '
             '(e.g. openai/gpt-4o).')
    is_configured = fields.Boolean(
        compute='_compute_is_configured',
        help='True when this configuration has everything it needs to run: '
             'a provider, an API key and a model.')
    last_test_ok = fields.Boolean(string='Last Test Succeeded', readonly=True)
    last_tested = fields.Datetime(string='Last Tested', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('configured', 'Configured'),
        ('tested', 'Tested'),
    ], default='draft', compute='_compute_state', store=True,
        help='Draft: missing provider/key/model. Configured: ready to test. '
             'Tested: last connection test succeeded.')

    @api.depends('provider', 'api_key', 'llm_model_id', 'openrouter_model')
    def _compute_is_configured(self):
        for rec in self:
            if rec.provider == 'OpenRouter':
                has_model = bool(rec.openrouter_model)
            else:
                has_model = bool(rec.llm_model_id)
            rec.is_configured = bool(rec.provider and rec.api_key and has_model)

    @api.depends('is_configured', 'last_test_ok')
    def _compute_state(self):
        for rec in self:
            if not rec.is_configured:
                rec.state = 'draft'
            elif rec.last_test_ok:
                rec.state = 'tested'
            else:
                rec.state = 'configured'

    # -- active-config access -------------------------------------------------

    @api.model
    def _get(self):
        """Return the config currently selected for use (empty recordset if none)."""
        return self.sudo().search([('is_active', '=', True)], limit=1)

    @api.model
    def _get_config(self):
        """Provider config for the LLM client: ``{provider, api_key, model_name}``.

        Same shape the client consumed from ``ir.config_parameter`` before, so
        :mod:`..core.llm_client` needs no other change.
        """
        rec = self._get()
        if rec.provider == 'OpenRouter':
            model_name = rec.openrouter_model or ''
        else:
            model_name = rec.llm_model_id.name or '' if rec.llm_model_id else ''
        return {
            'provider': rec.provider or '',
            'api_key': rec.api_key or '',
            'model_name': model_name,
        }

    # -- single-active guard --------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records.filtered('is_active'):
            rec._make_active_exclusive()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_active'):
            self._make_active_exclusive()
        # Advisory test flags shouldn't fire a config-changed broadcast.
        if not set(vals) <= {'last_test_ok', 'last_tested'}:
            self._notify_config_changed()
        return res

    def _make_active_exclusive(self):
        """Deselect every other config so ``self`` is the only active one."""
        self.ensure_one()
        others = self.sudo().search([('id', '!=', self.id), ('is_active', '=', True)])
        others.write({'is_active': False})

    def _notify_config_changed(self):
        """Broadcast the active config's state so open sessions update the chat icon."""
        active = self.sudo()._get()
        self.env['bus.bus']._sendone(CONFIG_CHANNEL, 'cyllo_ai_config', {
            'configured': bool(active.is_configured),
        })

    # -- UI actions ----------------------------------------------------------

    def action_test_connection(self):
        """Ping the configured provider to validate the key/model.

        Advisory only: it records the outcome and shows a notification. It does
        NOT gate the chat icon (visibility is derived from :attr:`is_configured`).
        """
        self.ensure_one()
        try:
            self._ping_provider()
        except UserError as e:
            self.sudo().write({'last_test_ok': False,
                               'last_tested': fields.Datetime.now()})
            return self._notification(_('Connection Failed'), str(e), 'danger')
        self.sudo().write({'last_test_ok': True,
                           'last_tested': fields.Datetime.now()})
        return self._notification(
            _('Success'), _('Cyllo AI connected successfully'), 'success')

    def _ping_provider(self):
        """Send a minimal request to the provider; raise UserError on failure."""
        self.ensure_one()
        if not self.provider:
            raise UserError(_('Please select an LLM provider.'))

        if self.provider == 'ChatOpenAI':
            if not self.api_key or len(self.api_key) < 10:
                raise UserError(_('OpenAI API key looks too short.'))
            model_name = self.llm_model_id.name or 'gpt-4o-mini'
            try:
                response = requests.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={'Authorization': f'Bearer {self.api_key}',
                             'Content-Type': 'application/json'},
                    json={'model': model_name,
                          'messages': [{'role': 'user', 'content': 'Ping'}],
                          'max_tokens': 5},
                    timeout=15)
            except requests.exceptions.RequestException as e:
                raise UserError(_('There is a problem connecting to OpenAI.\n\n'
                                  'Error:\n%s') % str(e))
            if response.status_code == 401:
                raise UserError(_('Invalid OpenAI API key.'))
            if response.status_code == 429:
                raise UserError(_('OpenAI quota limit exceeded. Please check '
                                  'your plan and billing details.'))
            if response.status_code != 200:
                raise UserError(_('OpenAI API error (%(code)s): %(body)s',
                                  code=response.status_code, body=response.text))
            if not response.json().get('choices'):
                raise UserError(_('OpenAI API key is valid but returned no content.'))

        elif self.provider == 'ChatGoogleGenerativeAI':
            if not self.api_key or len(self.api_key) < 20:
                raise UserError(_('Google Gemini API key looks too short.'))
            model_name = self.llm_model_id.name or 'gemini-pro'
            url = (f'https://generativelanguage.googleapis.com/v1beta/models/'
                   f'{model_name}:generateContent?key={self.api_key}')
            try:
                response = requests.post(
                    url, json={'contents': [{'parts': [{'text': 'Ping'}]}]},
                    timeout=15)
            except requests.exceptions.RequestException as e:
                raise UserError(_('There is a problem connecting to Google '
                                  'Gemini.\n\nError:\n%s') % str(e))
            if response.status_code == 429:
                raise UserError(_('Quota limit exceeded for this API key. '
                                  'Please check your plan and billing details.'))
            if response.status_code == 400:
                raise UserError(_('Invalid Gemini API key or model name.'))
            if response.status_code != 200:
                raise UserError(_('Gemini API error (%(code)s): %(body)s',
                                  code=response.status_code, body=response.text))
            if not response.json().get('candidates'):
                raise UserError(_('Gemini API key is valid but returned no content.'))

        elif self.provider == 'OpenRouter':
            if not self.api_key or len(self.api_key) < 10:
                raise UserError(_('OpenRouter API key looks too short.'))
            if not self.openrouter_model:
                raise UserError(_('Please enter an OpenRouter model.'))
            try:
                response = requests.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={'Authorization': f'Bearer {self.api_key}',
                             'Content-Type': 'application/json',
                             'HTTP-Referer': 'https://cyllo.com',
                             'X-Title': 'Cyllo AI'},
                    json={'model': self.openrouter_model,
                          'messages': [{'role': 'user', 'content': 'Ping'}],
                          'max_tokens': 5},
                    timeout=15)
            except requests.exceptions.RequestException as e:
                raise UserError(_('There is a problem connecting to '
                                  'OpenRouter.\n\nError:\n%s') % str(e))
            if response.status_code == 401:
                raise UserError(_('Invalid OpenRouter API key.'))
            if response.status_code == 429:
                raise UserError(_('OpenRouter quota limit exceeded. Please check '
                                  'your plan and billing details.'))
            if response.status_code != 200:
                raise UserError(_('OpenRouter API error (%(code)s): %(body)s',
                                  code=response.status_code, body=response.text))
            if not response.json().get('choices'):
                raise UserError(_('OpenRouter API key is valid but returned no content.'))
        else:
            raise UserError(_('Unsupported LLM provider: %s') % self.provider)

    @staticmethod
    def _notification(title, message, kind):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title, 'message': message,
                'type': kind, 'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
