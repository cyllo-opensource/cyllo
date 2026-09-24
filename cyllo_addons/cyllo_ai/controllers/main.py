
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
import base64
import json
import logging

import requests
import odoo
from odoo import api, fields, http
from odoo.http import Controller, request

_logger = logging.getLogger(__name__)


class ChatBotController(Controller):

    @http.route('/cyllo/get_ai_widget_enabled', type='json', auth='user')
    def get_ai_widget_enabled(self):
        """Whether the chat widget should show — derived from the config state."""
        config = request.env['cyllo.ai.config'].sudo()._get()
        return '1' if config.is_configured else '0'

    @http.route('/cyllo/get_model_label', type='json', auth='user')
    def get_model_label(self):
        """Provider + model display name, for the composer's model chip.

        Deliberately narrow. ``cyllo.ai.config`` is admin-only and its
        ``_get_config()`` returns the API key, so neither may be handed to the
        client: this returns two display strings and nothing else, and returns
        nothing at all until the assistant is fully configured.
        """
        config = request.env['cyllo.ai.config'].sudo()._get()
        if not config.is_configured:
            return {}
        provider_labels = dict(config._fields['provider'].selection)
        if config.provider == 'OpenRouter':
            model = config.openrouter_model or ''
        else:
            model = config.llm_model_id.display_name or config.llm_model_id.name or ''
        return {
            'provider': provider_labels.get(config.provider, config.provider or ''),
            'model': model,
        }

    @http.route('/cyllo/speech_to_text', type='json', auth='user')
    def get_text(self, encoded_audio, mime=None):
        """
        Convert speech to text using the configured LLM provider via direct HTTP.

        :param encoded_audio: Base64 encoded audio string
        :param mime: the audio mime type the browser actually recorded
                     (e.g. 'audio/webm' on Chrome/Firefox, 'audio/mp4' on Safari)
        :return: Transcribed text from the audio
        """
        try:
            cfg = request.env['cyllo.ai.config'].sudo()._get_config()
            agent_llm = cfg['provider']
            api_key = cfg['api_key']
            model_name = cfg['model_name']

            if agent_llm == 'ChatGoogleGenerativeAI':
                url = (
                    f'https://generativelanguage.googleapis.com/v1beta/models/'
                    f'{model_name}:generateContent?key={api_key}'
                )
                payload = {
                    'contents': [{
                        'parts': [
                            {'text': 'Transcribe the audio.'},
                            {
                                'inline_data': {
                                    # The client now sends WAV; honor the real
                                    # mime (fallback keeps older clients working).
                                    'mime_type': (mime or 'audio/mpeg').split(';')[0].strip(),
                                    'data': encoded_audio,
                                }
                            },
                        ]
                    }]
                }
                response = requests.post(url, json=payload, timeout=60)
                if response.status_code == 429:
                    _logger.warning("Quota exceeded for Gemini API in speech-to-text")
                    return "Quota limit exceeded. Please try again later."
                response.raise_for_status()
                data = response.json()
                transcript = data['candidates'][0]['content']['parts'][0]['text']
                _logger.info("[cyllo_ai] speech_to_text response provider=%s len=%d:\n%s",
                             agent_llm, len(transcript or ''), (transcript or '')[:2000])
                return transcript

            else:
                # OpenAI / OpenRouter — use Whisper transcription endpoint
                audio_bytes = base64.b64decode(encoded_audio)
                if agent_llm == 'OpenRouter':
                    base_url = 'https://openrouter.ai/api/v1'
                else:
                    base_url = 'https://api.openai.com/v1'
                # Label the upload with the format the browser actually recorded.
                # Whisper decodes by this hint — mislabeling (e.g. webm as mp3)
                # makes transcription fail. Falls back to webm (Chrome/Firefox).
                audio_mime = (mime or 'audio/webm').split(';')[0].strip()
                ext = audio_mime.rsplit('/', 1)[-1] or 'webm'
                response = requests.post(
                    f'{base_url}/audio/transcriptions',
                    headers={'Authorization': f'Bearer {api_key}'},
                    files={'file': (f'audio.{ext}', audio_bytes, audio_mime)},
                    # gpt-4o-transcribe: GPT-4o-based speech model — far better
                    # multilingual accuracy and language detection than whisper-1
                    # (which confused e.g. Malayalam with Tamil). Same endpoint,
                    # same key, no package.
                    data={'model': 'gpt-4o-transcribe'},
                    timeout=60,
                )
                if response.status_code >= 400:
                    # Surface the provider's exact reason — raise_for_status()
                    # drops the body, where the real 400 message lives.
                    _logger.error("[cyllo_ai] transcription HTTP %s: %s",
                                  response.status_code, (response.text or '')[:1000])
                response.raise_for_status()
                transcript = response.json().get('text', '')
                _logger.info("[cyllo_ai] speech_to_text response provider=%s len=%d:\n%s",
                             agent_llm, len(transcript or ''), (transcript or '')[:2000])
                return transcript

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                _logger.warning("Quota exceeded during speech-to-text: %s", str(e))
                return "Quota limit exceeded. Please try again later."
            _logger.exception("HTTP error during speech-to-text: %s", str(e))
            return "An error occurred while transcribing the audio. Please try again."
        except Exception as e:
            _logger.exception("Unexpected error during speech-to-text: %s", str(e))
            return "An error occurred while transcribing the audio. Please try again."

    @http.route('/chatbot/query', type='json', auth='user', csrf=False)
    def chatbot_query(self, **kwargs):
        """
        Process a user query through the chatbot agent.

        :param kwargs: Dictionary containing 'text', 'userId', 'interrupted', 'session_id', 'company_ids'
        :return: Dictionary with 'response' and 'last_message'
        """
        text = kwargs.get('text')
        interrupted = kwargs.get('interrupted')
        session_id = kwargs.get('session_id')
        company_ids = kwargs.get('company_ids')
        ui_context = kwargs.get('ui_context')

        agent_model = request.env['chatbot.agent']
        try:
            result = agent_model.process_query(text, session_id, company_ids, interrupted,
                                               ui_context=ui_context)
            return result
        except Exception as e:
            _logger.exception("Unexpected error during chatbot query")
            return {
                'response': 'none',
                'last_message': f'**An error occurred:** {str(e)}',
            }

    @http.route('/chatbot/query/stream', type='http', auth='user', csrf=False, methods=['POST'])
    def chatbot_query_stream(self, **kwargs):
        """
        Stream a chatbot response as Server-Sent Events.

        Emits typed JSON frames: delta (answer tokens), status, confirm
        (write awaiting confirmation), done, error.

        A dedicated cursor is opened inside the generator: Odoo commits the
        request cursor before the response body streams, so reusing it for
        mid-stream tool DB access would fail.
        """
        raw = request.httprequest.get_data(as_text=True)
        try:
            data = json.loads(raw) if raw else {}
        except (ValueError, TypeError):
            data = {}
        data.update(kwargs)

        text = data.get('text')
        session_id = data.get('session_id')
        interrupted = data.get('interrupted')
        company_ids = data.get('company_ids')
        ui_context = data.get('ui_context')

        dbname = request.env.cr.dbname
        uid = request.env.uid
        context = dict(request.env.context)

        def generate():
            registry = odoo.registry(dbname)
            with registry.cursor() as cr:
                env = api.Environment(cr, uid, context)
                try:
                    for event in env['chatbot.agent'].process_query_stream(
                        text, session_id, company_ids, interrupted,
                        ui_context=ui_context,
                    ):
                        yield f"data: {json.dumps(event)}\n\n"
                    cr.commit()
                except Exception as e:
                    _logger.exception("Streaming query failed")
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        # No 'Connection: keep-alive' here. Werkzeug's dev server closes every
        # connection and, after the body, drains the socket with a blocking
        # read; a client that reuses the connection wedges that read forever
        # (its next request is swallowed and the thread never exits).
        headers = [
            ('Content-Type', 'text/event-stream'),
            ('Cache-Control', 'no-cache'),
            ('X-Accel-Buffering', 'no'),
        ]
        return request.make_response(generate(), headers=headers)

    @http.route('/chatbot/set_conversation', type='json', auth='user')
    def set_conversation(self, user_id, session_id, user_message, response_message, chart_config, interrupted, company_ids, usage=None, thinking=None, user_chart_config=None):
        """
        Save a conversation entry to the chatbot history.

        :param user_id: ID of the user
        :param session_id: Session identifier
        :param user_message: Message sent by the user
        :param response_message: Response generated by the bot
        :param chart_config: Configuration for any generated charts
        :param interrupted: Boolean indicating if the response was interrupted
        :param usage: Optional {prompt, completion, total} token counts for the turn
        :param thinking: Optional {ms, steps} agent trajectory for the turn
        :param user_chart_config: Optional host chart attached to the user's own turn
        :return: Dictionary containing the ID of the created record
        """
        chart_config = json.dumps(chart_config)
        user_chart_config = json.dumps(user_chart_config) if user_chart_config else False
        usage = usage if isinstance(usage, dict) else {}
        thinking = thinking if isinstance(thinking, dict) else {}
        steps = thinking.get('steps')
        steps = steps if isinstance(steps, list) else []
        history_model = request.env['chatbot.history']
        is_first_turn = not history_model.sudo().search_count([('session_id', '=', session_id)])
        new_record = history_model.create({
            'user_id': user_id,
            'session_id': session_id,
            'user_message': user_message,
            'response_message': response_message,
            'chart_config': chart_config,
            'user_chart_config': user_chart_config,
            'interrupted': interrupted,
            'company_ids': [(6, 0, company_ids)],
            'thinking_ms': thinking.get('ms') or 0,
            'thinking_steps': json.dumps(steps) if steps else False,
            'prompt_tokens': usage.get('prompt') or 0,
            'completion_tokens': usage.get('completion') or 0,
            'total_tokens': usage.get('total') or 0,
            'create_date': fields.Datetime.now(),
        })
        title = None
        if is_first_turn:
            title = new_record.generate_title(user_message, response_message)
            if title:
                new_record.title = title
        return {'id': new_record.id, 'title': title}

    @http.route('/chatbot/get_conversation', type='json', auth='user')
    def get_conversation(self, session_id, company_id=None):
        """
        Retrieve the conversation history for a specific session.

        :param session_id: Session identifier
        :return: List of conversation dictionaries
        """
        if company_id and not isinstance(company_id, list):
            company_ids = [company_id]
        else:
            company_ids = company_id or []

        domain = [
            ('session_id', '=', session_id),
            ('user_id', '=', request.env.uid),
        ]
        if company_ids:
            domain.append(('company_ids', 'in', company_ids))

        records = request.env['chatbot.history'].sudo().search(
            domain,
            order='create_date asc, id asc'
        )

        history = []
        for rec in records:
            if rec.user_message:
                try:
                    user_chart = json.loads(rec.user_chart_config) if rec.user_chart_config else None
                except json.JSONDecodeError as e:
                    _logger.debug(
                        'Failed to parse user_chart_config as JSON for record %s: %s',
                        rec.id, str(e), exc_info=True
                    )
                    user_chart = None
                history.append({
                    "from": "user",
                    "text": rec.user_message,
                    "timestamp": rec.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "chart_config": None,
                    "chart": user_chart,
                })
            if rec.response_message:
                try:
                    chart_config = json.loads(rec.chart_config)
                except json.JSONDecodeError as e:
                    _logger.debug(
                        'Failed to parse chart_config as JSON for record %s: %s',
                        rec.id, str(e), exc_info=True
                    )
                    chart_config = None
                try:
                    steps = json.loads(rec.thinking_steps) if rec.thinking_steps else []
                except (TypeError, ValueError):
                    steps = []
                history.append({
                    "id": rec.id,
                    "from": "bot",
                    "thinking": {"ms": rec.thinking_ms, "steps": steps}
                                if (rec.thinking_ms or steps) else None,
                    "text": rec.response_message,
                    "timestamp": rec.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "chart_config": chart_config,
                    "interrupted": rec.interrupted,
                    "usage": {
                        "prompt": rec.prompt_tokens,
                        "completion": rec.completion_tokens,
                        "total": rec.total_tokens,
                    } if rec.total_tokens else None,
                })
        return history

    @http.route('/chatbot/set_interrupt', type='json', auth='user')
    def set_interrupt(self, record_id):
        """
        Reset the interrupted status of a conversation record.

        :param record_id: ID of the chatbot history record
        :return: Dictionary with status 'success' or 'error'
        """
        record_id = int(record_id)
        history = request.env['chatbot.history'].browse(record_id)
        if history.exists():
            history.write({'interrupted': False})
            return {'status': 'success'}
        return {'status': 'error', 'message': 'Record not found'}
