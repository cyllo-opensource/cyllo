# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
"""
Provider-agnostic LLM client — direct HTTP, no third-party AI framework.

Single source of truth for talking to the configured LLM provider
(OpenAI / Google Gemini / OpenRouter). Reads provider config from
``ir.config_parameter``.

Two entry points:
- ``complete(prompt)``            — plain text completion (used by sub-tools).
- ``complete_with_tools(msgs, tools)`` — native function-calling for the agent
  loop; returns ``{"content": str|None, "tool_calls": [{id, name, arguments}]}``.

Later: streaming, retries/backoff, per-agent model selection.
"""
import json
import logging

import requests

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60
#: Human names for the provider keys, used in error messages.
PROVIDER_NAMES = {
    'ChatOpenAI': 'OpenAI',
    'ChatGoogleGenerativeAI': 'Google Gemini',
    'OpenRouter': 'OpenRouter',
}
# Max chars of an LLM response logged verbatim (rest is truncated).
RESPONSE_LOG_LIMIT = 6000


class LLMClient:
    """Thin HTTP client for the configured LLM provider."""

    def __init__(self, env):
        self.env = env

    # -- configuration -------------------------------------------------------

    def _config(self):
        """Resolve provider config from the cyllo.ai.config singleton."""
        return self.env['cyllo.ai.config'].sudo()._get_config()

    def is_configured(self):
        """True if a provider, key and model are all set."""
        cfg = self._config()
        return bool(cfg['provider'] and cfg['api_key'] and cfg['model_name'])

    @staticmethod
    def _log_llm_response(kind, provider, model, content, tool_calls):
        """Log the LLM's response verbatim (content + tool calls), truncated.

        Never logs the API key. Tool-call arguments are LLM-generated query
        params, safe to log for tracing.
        """
        content = content or ''
        if len(content) > RESPONSE_LOG_LIMIT:
            content = content[:RESPONSE_LOG_LIMIT] + \
                f"\n…(+{len(content) - RESPONSE_LOG_LIMIT} chars truncated)"
        tc_preview = ''
        if tool_calls:
            try:
                tc_json = json.dumps(
                    [{'name': c.get('name'), 'arguments': c.get('arguments')} for c in tool_calls],
                    default=str,
                )
            except (TypeError, ValueError):
                tc_json = str(tool_calls)
            if len(tc_json) > RESPONSE_LOG_LIMIT:
                tc_json = tc_json[:RESPONSE_LOG_LIMIT] + ' …(truncated)'
            tc_preview = f"\n  tool_calls: {tc_json}"
        _logger.info("[cyllo_ai] LLM response (%s) provider=%s model=%s:\n%s%s",
                     kind, provider, model, content, tc_preview)

    # -- plain completion ----------------------------------------------------

    def complete(self, prompt, timeout=DEFAULT_TIMEOUT):
        """
        Run a single text completion.

        :param prompt: a string (one user turn) or a list of
                       ``{"role", "content"}`` message dicts.
        :return: the model's text response.
        """
        cfg = self._config()
        provider, api_key, model_name = cfg['provider'], cfg['api_key'], cfg['model_name']
        if not api_key:
            raise UserError("LLM API key is not configured. Please set it in Settings.")

        messages = [{'role': 'user', 'content': prompt}] if isinstance(prompt, str) else list(prompt or [])
        _logger.debug("[cyllo_ai] llm.complete provider=%s model=%s msgs=%d",
                      provider, model_name, len(messages))

        if provider == 'ChatGoogleGenerativeAI':
            contents = [
                {'role': 'model' if m.get('role') == 'assistant' else 'user',
                 'parts': [{'text': m.get('content', '')}]}
                for m in messages
            ]
            data = self._post_gemini(model_name, api_key, {'contents': contents}, timeout)
            text = self._gemini_text(data)
            self._record_usage(self._usage_gemini(data))
        elif provider in ('ChatOpenAI', 'OpenRouter'):
            payload = {'model': model_name, 'messages': messages}
            data = self._post_openai(provider, api_key, payload, timeout)
            text = data['choices'][0]['message']['content']
            self._record_usage(self._usage_openai(data))
        else:
            raise UserError(f"Unsupported LLM provider: {provider}")

        self._log_llm_response("complete", provider, model_name, text, None)
        return text

    # -- function-calling ----------------------------------------------------

    def complete_with_tools(self, messages, tools, timeout=DEFAULT_TIMEOUT):
        """
        One agent step with tools available.

        :param messages: list of :class:`~..session.Message` objects.
        :param tools: list of :class:`~.tools.base.Tool` instances.
        :return: ``{"content": str|None, "tool_calls": [{"id","name","arguments"}]}``
        """
        cfg = self._config()
        provider, api_key, model_name = cfg['provider'], cfg['api_key'], cfg['model_name']
        if not api_key:
            raise UserError("LLM API key is not configured. Please set it in Settings.")

        _logger.debug("[cyllo_ai] llm.complete_with_tools provider=%s model=%s msgs=%d tools=%d",
                      provider, model_name, len(messages), len(tools))
        if provider == 'ChatGoogleGenerativeAI':
            result = self._tools_gemini(messages, tools, model_name, api_key, timeout)
        elif provider in ('ChatOpenAI', 'OpenRouter'):
            result = self._tools_openai(messages, tools, model_name, api_key, provider, timeout)
        else:
            raise UserError(f"Unsupported LLM provider: {provider}")

        self._record_usage(result.get('usage'))
        self._log_llm_response("complete_with_tools", provider, model_name,
                               result.get('content'), result.get('tool_calls'))
        return result

    # -- streaming -----------------------------------------------------------

    def stream(self, messages, tools, timeout=DEFAULT_TIMEOUT):
        """
        Stream one agent step.

        Yields ``("delta", text)`` for each content token as it arrives, and
        finally ``("final", {"content", "tool_calls"})`` with the fully
        assembled message (tool-call argument fragments concatenated).
        """
        cfg = self._config()
        provider, api_key, model_name = cfg['provider'], cfg['api_key'], cfg['model_name']
        if not api_key:
            raise UserError("LLM API key is not configured. Please set it in Settings.")

        _logger.debug("[cyllo_ai] llm.stream provider=%s model=%s msgs=%d tools=%d",
                      provider, model_name, len(messages), len(tools))
        if provider == 'ChatGoogleGenerativeAI':
            source = self._stream_gemini(messages, tools, model_name, api_key, timeout)
        elif provider in ('ChatOpenAI', 'OpenRouter'):
            source = self._stream_openai(messages, tools, model_name, api_key, provider, timeout)
        else:
            raise UserError(f"Unsupported LLM provider: {provider}")

        # Pass through events, logging the assembled response once complete — and
        # still log whatever was accumulated if the stream errors mid-flight.
        text_acc = []
        logged = False
        try:
            for ev_type, payload in source:
                if ev_type == 'delta':
                    text_acc.append(payload)
                elif ev_type == 'final':
                    p = payload or {}
                    self._record_usage(p.get('usage'))
                    self._log_llm_response("stream", provider, model_name,
                                           p.get('content') or ''.join(text_acc),
                                           p.get('tool_calls'))
                    logged = True
                yield (ev_type, payload)
        except Exception:
            if not logged:
                self._log_llm_response("stream-error", provider, model_name,
                                       ''.join(text_acc), None)
            raise

    # -- OpenAI / OpenRouter -------------------------------------------------

    @staticmethod
    def _network_error(provider, exc):
        """Turn a transport failure into one actionable sentence.

        A DNS or connection failure is precisely diagnosable, so it should not
        reach the user as "Something went wrong" nor the log as a 60-line
        traceback. It means one thing: the SERVER could not reach the provider.
        Note this is about the SERVER's connectivity, not the browser's —
        a distinction worth stating, because the user's own machine is usually
        online when they see it.
        """
        name = PROVIDER_NAMES.get(provider, provider or 'the LLM provider')
        if isinstance(exc, requests.exceptions.Timeout):
            return UserError(
                f"Cyllo AI timed out waiting for {name}. The service may be "
                f"slow or unreachable — please try again.")
        return UserError(
            f"Cyllo AI can't reach {name}. The Cyllo server has no connection "
            f"to it — check the server's internet access, then try again.")

    @staticmethod
    def _check_response(resp):
        """Raise on HTTP errors with the provider's error body (truncated).

        Replaces ``raise_for_status()``: its exception message embeds the full
        request URL, which for Gemini contains the API key — that must never
        reach logs or the UI. The body is what actually says what went wrong
        (e.g. OpenAI's "tool_calls must be followed by tool messages...").
        """
        if resp.status_code < 400:
            return
        try:
            body = (resp.text or "")[:500]
        except Exception:
            body = ""
        _logger.error("[cyllo_ai] provider HTTP %s: %s", resp.status_code, body)
        raise UserError(f"LLM provider error (HTTP {resp.status_code}): {body[:200]}")

    def _post_openai(self, provider, api_key, payload, timeout):
        if provider == 'OpenRouter':
            base_url = 'https://openrouter.ai/api/v1'
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://cyllo.com',
                'X-Title': 'Cyllo AI',
            }
        else:
            base_url = 'https://api.openai.com/v1'
            headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        try:
            response = requests.post(
                f'{base_url}/chat/completions', headers=headers, json=payload, timeout=timeout
            )
        except requests.exceptions.RequestException as e:
            _logger.warning("[cyllo_ai] cannot reach %s: %s", provider, e)
            raise self._network_error(provider, e) from e
        self._check_response(response)

        return response.json()

    def _tools_openai(self, messages, tools, model_name, api_key, provider, timeout):
        payload = {
            'model': model_name,
            'messages': self._to_openai_messages(messages),
            'tools': self._openai_specs(tools),
            'tool_choice': 'auto',
        }
        data = self._post_openai(provider, api_key, payload, timeout)
        msg = data['choices'][0]['message']
        tool_calls = []
        for tc in msg.get('tool_calls') or []:
            fn = tc.get('function', {})
            try:
                args = json.loads(fn.get('arguments') or '{}')
            except (ValueError, TypeError):
                args = {}
            tool_calls.append({'id': tc.get('id'), 'name': fn.get('name'), 'arguments': args})
        return {'content': msg.get('content'), 'tool_calls': tool_calls,
                'usage': self._usage_openai(data)}

    def _record_usage(self, usage):
        """Add one call's usage to the per-turn sink in env.context, if present.

        Every LLM call — the agent loop's and any tool-internal call (they all
        go through LLMClient) — lands here, giving a true whole-turn total. The
        orchestrator seeds ``context['cyllo_ai_usage']`` with a mutable dict and
        reads it back at the end of the turn.
        """
        if not usage:
            return
        sink = self.env.context.get('cyllo_ai_usage')
        if isinstance(sink, dict):
            p = usage.get('prompt') or 0
            c = usage.get('completion') or 0
            sink['prompt'] += p
            sink['completion'] += c
            sink['total'] += usage.get('total') or (p + c)

    @staticmethod
    def _usage_openai(data):
        """Normalize OpenAI/OpenRouter usage to {prompt, completion, total}."""
        u = (data or {}).get('usage') or {}
        if not u:
            return None
        return {'prompt': u.get('prompt_tokens') or 0,
                'completion': u.get('completion_tokens') or 0,
                'total': u.get('total_tokens') or 0}

    @staticmethod
    def _usage_gemini(data):
        """Normalize Gemini usageMetadata to {prompt, completion, total}."""
        u = (data or {}).get('usageMetadata') or {}
        if not u:
            return None
        return {'prompt': u.get('promptTokenCount') or 0,
                'completion': u.get('candidatesTokenCount') or 0,
                'total': u.get('totalTokenCount') or 0}

    @staticmethod
    def _to_openai_messages(messages):
        out = []
        for m in messages:
            if m.role == 'assistant' and m.tool_calls:
                out.append({
                    'role': 'assistant',
                    'content': m.content or None,
                    'tool_calls': [
                        {
                            'id': tc['id'],
                            'type': 'function',
                            'function': {
                                'name': tc['name'],
                                'arguments': json.dumps(tc.get('arguments') or {}),
                            },
                        }
                        for tc in m.tool_calls
                    ],
                })
            elif m.role == 'tool':
                out.append({
                    'role': 'tool',
                    'tool_call_id': m.tool_call_id,
                    'content': m.content or '',
                })
            else:
                out.append({'role': m.role, 'content': m.content or ''})
        return out

    @staticmethod
    def _openai_specs(tools):
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug("[cyllo_ai] tools passed to LLM:\n%s", json.dumps(
                [{'name': t.name, 'description': t.description, 'schema': t.input_schema}
                 for t in tools], indent=2))
        return [
            {
                'type': 'function',
                'function': {
                    'name': t.name,
                    'description': t.description,
                    'parameters': t.input_schema or {'type': 'object', 'properties': {}},
                },
            }
            for t in tools
        ]

    # -- Google Gemini -------------------------------------------------------

    def _post_gemini(self, model_name, api_key, payload, timeout):
        url = (
            f'https://generativelanguage.googleapis.com/v1beta/models/'
            f'{model_name}:generateContent?key={api_key}'
        )
        try:
            response = requests.post(url, json=payload, timeout=timeout)
        except requests.exceptions.RequestException as e:
            _logger.warning("[cyllo_ai] cannot reach Gemini: %s", e)
            raise self._network_error('ChatGoogleGenerativeAI', e) from e
        self._check_response(response)
        return response.json()

    @staticmethod
    def _gemini_text(data):
        parts = data['candidates'][0]['content']['parts']
        return ''.join(p.get('text', '') for p in parts)

    def _tools_gemini(self, messages, tools, model_name, api_key, timeout):
        payload = {
            'contents': self._to_gemini_contents(messages),
            'tools': [{'function_declarations': [
                {
                    'name': t.name,
                    'description': t.description,
                    'parameters': t.input_schema or {'type': 'object', 'properties': {}},
                }
                for t in tools
            ]}],
        }
        data = self._post_gemini(model_name, api_key, payload, timeout)
        parts = data['candidates'][0]['content'].get('parts', [])
        content = ''.join(p.get('text', '') for p in parts if 'text' in p) or None
        tool_calls = []
        for i, p in enumerate(parts):
            if 'functionCall' in p:
                fc = p['functionCall']
                tool_calls.append({
                    'id': f"call_{i}",
                    'name': fc.get('name'),
                    'arguments': fc.get('args') or {},
                })
        return {'content': content, 'tool_calls': tool_calls,
                'usage': self._usage_gemini(data)}

    @staticmethod
    def _to_gemini_contents(messages):
        contents = []
        for m in messages:
            if m.role == 'assistant' and m.tool_calls:
                contents.append({
                    'role': 'model',
                    'parts': [
                        {'functionCall': {'name': tc['name'], 'args': tc.get('arguments') or {}}}
                        for tc in m.tool_calls
                    ],
                })
            elif m.role == 'tool':
                contents.append({
                    'role': 'user',
                    'parts': [{
                        'functionResponse': {
                            'name': m.name or 'tool',
                            'response': {'result': m.content or ''},
                        }
                    }],
                })
            else:
                role = 'model' if m.role == 'assistant' else 'user'
                contents.append({'role': role, 'parts': [{'text': m.content or ''}]})
        return contents

    # -- streaming implementations ------------------------------------------

    def _stream_openai(self, messages, tools, model_name, api_key, provider, timeout):
        if provider == 'OpenRouter':
            base_url = 'https://openrouter.ai/api/v1'
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://your-domain.com',
                'X-Title': 'Cyllo Agent',
            }
        else:
            base_url = 'https://api.openai.com/v1'
            headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        payload = {
            'model': model_name,
            'messages': self._to_openai_messages(messages),
            'tools': self._openai_specs(tools),
            'tool_choice': 'auto',
            'stream': True,
        }
        # Ask for token usage in the stream (final chunk). OpenAI uses
        # stream_options.include_usage; OpenRouter uses usage.include.
        if provider == 'OpenRouter':
            payload['usage'] = {'include': True}
        else:
            payload['stream_options'] = {'include_usage': True}
        text_parts = []
        calls = {}  # index -> {id, name, args}
        usage = None
        try:
            with requests.post(f'{base_url}/chat/completions', headers=headers,
                               json=payload, stream=True, timeout=timeout) as resp:
                self._check_response(resp)
                for raw in resp.iter_lines(decode_unicode=True):
                    if not raw:
                        continue
                    if raw.startswith('data: '):
                        raw = raw[6:]
                    if raw.strip() == '[DONE]':
                        break
                    try:
                        chunk = json.loads(raw)
                    except (ValueError, TypeError):
                        continue
                    if chunk.get('usage'):
                        usage = self._usage_openai(chunk)
                    choices = chunk.get('choices') or []
                    if not choices:
                        continue
                    delta = choices[0].get('delta') or {}
                    if delta.get('content'):
                        text_parts.append(delta['content'])
                        yield ('delta', delta['content'])
                    for tcd in delta.get('tool_calls') or []:
                        idx = tcd.get('index', 0)
                        slot = calls.setdefault(idx, {'id': None, 'name': None, 'args': ''})
                        if tcd.get('id'):
                            slot['id'] = tcd['id']
                        fn = tcd.get('function') or {}
                        if fn.get('name'):
                            slot['name'] = fn['name']
                        if fn.get('arguments'):
                            slot['args'] += fn['arguments']
        except requests.exceptions.RequestException as e:
            _logger.warning("[cyllo_ai] stream to %s failed: %s", provider, e)
            raise self._network_error(provider, e) from e
        yield ('final', {'content': ''.join(text_parts) or None,
                         'tool_calls': self._assemble_calls(calls),
                         'usage': usage})

    @staticmethod
    def _assemble_calls(calls):
        tool_calls = []
        for idx in sorted(calls):
            slot = calls[idx]
            try:
                args = json.loads(slot['args'] or '{}')
            except (ValueError, TypeError):
                args = {}
            tool_calls.append({
                'id': slot['id'] or f"call_{idx}",
                'name': slot['name'],
                'arguments': args,
            })
        return tool_calls

    def _stream_gemini(self, messages, tools, model_name, api_key, timeout):
        url = (
            f'https://generativelanguage.googleapis.com/v1beta/models/'
            f'{model_name}:streamGenerateContent?alt=sse&key={api_key}'
        )
        payload = {
            'contents': self._to_gemini_contents(messages),
            'tools': [{'function_declarations': [
                {
                    'name': t.name,
                    'description': t.description,
                    'parameters': t.input_schema or {'type': 'object', 'properties': {}},
                }
                for t in tools
            ]}],
        }
        text_parts = []
        tool_calls = []
        usage = None
        try:
            with requests.post(url, json=payload, stream=True, timeout=timeout) as resp:
                self._check_response(resp)
                for raw in resp.iter_lines(decode_unicode=True):
                    if not raw:
                        continue
                    if raw.startswith('data: '):
                        raw = raw[6:]
                    if raw.strip() == '[DONE]':
                        break
                    try:
                        chunk = json.loads(raw)
                    except (ValueError, TypeError):
                        continue
                    if chunk.get('usageMetadata'):
                        usage = self._usage_gemini(chunk)  # cumulative; keep latest
                    cands = chunk.get('candidates') or []
                    if not cands:
                        continue
                    for p in cands[0].get('content', {}).get('parts', []) or []:
                        if p.get('text'):
                            text_parts.append(p['text'])
                            yield ('delta', p['text'])
                        if 'functionCall' in p:
                            fc = p['functionCall']
                            tool_calls.append({
                                'id': f"call_{len(tool_calls)}",
                                'name': fc.get('name'),
                                'arguments': fc.get('args') or {},
                            })
        except requests.exceptions.RequestException as e:
            _logger.warning("[cyllo_ai] stream to %s failed: %s", 'Gemini', e)
            raise self._network_error('ChatGoogleGenerativeAI', e) from e
        yield ('final', {'content': ''.join(text_parts) or None,
                         'tool_calls': tool_calls, 'usage': usage})
