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

from odoo import api, fields, models
from odoo.tools import json

from odoo.addons.cyllo_ai.core.llm_client import LLMClient

_logger = logging.getLogger(__name__)


class ChatbotHistory(models.Model):
    _name = 'chatbot.history'
    _description = 'Chatbot Conversation History'

    user_id = fields.Many2one('res.users', required=True)
    session_id = fields.Char()
    title = fields.Char()
    user_message = fields.Text()  # store as JSON string
    response_message = fields.Text()
    chart_config = fields.Text()
    # A host chart the user attached to their own turn (e.g. "explain this
    # chart" from a dashboard widget) — distinct from chart_config, which is
    # a chart the BOT generated in its reply.
    user_chart_config = fields.Text()
    interrupted = fields.Boolean(string='interrupted', default=False)
    # Agent trajectory for this answer: how long the tool phase ran, and which
    # tools it used. Persisted (not just held in the live view) because in
    # business software the provenance of a figure is auditable information —
    # "which engine produced this number?" must survive a page reload.
    thinking_ms = fields.Integer(
        default=0, help='Milliseconds spent working before the answer began.')
    thinking_steps = fields.Text(
        help='JSON list of the tools used, as [{"name","label","ok"}, ...].')
    prompt_tokens = fields.Integer(default=0)
    completion_tokens = fields.Integer(default=0)
    total_tokens = fields.Integer(default=0)
    create_date = fields.Datetime(readonly=True, default=fields.Datetime.now())
    company_ids = fields.Many2many('res.company', default=lambda self: self.env.company, index=True)

    @staticmethod
    def _extract_text(raw):
        """Pull plain text out of a message that may be a JSON envelope."""
        if not raw:
            return ''
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data.get('content') or data.get('text') or raw
        except (json.JSONDecodeError, TypeError):
            pass
        return raw

    def generate_title(self, user_message, response_message):
        """Ask the LLM for a short title summarizing this exchange.

        Uses the assistant's response, not just the user's message, since a
        terse or incomplete question ("Hi") tells you nothing about what the
        chat ended up being about. Returns False on any failure so callers
        fall back to the plain truncation behavior in get_user_sessions.
        """
        question = self._extract_text(user_message).strip()
        answer = self._extract_text(response_message).strip()
        if not question and not answer:
            return False

        prompt = (
            "Summarize this chat exchange as a short title (3-6 words). "
            "Plain text only, no quotes, no trailing punctuation.\n\n"
            f"User: {question[:500]}\n"
            f"Assistant: {answer[:500]}"
        )
        try:
            title = LLMClient(self.env).complete(prompt, timeout=20)
        except Exception:
            _logger.warning('Title generation failed, falling back to truncation', exc_info=True)
            return False

        title = title.strip().strip('"\'').strip()
        return title[:60] or False

    @api.model
    def get_user_sessions(self, company_ids=None):
        """Get distinct sessions with first message as title"""
        user_id = self.env.user.id
        if not company_ids:
            company_ids = [self.env.company.id]

        company_ids_sorted = sorted(company_ids)

        # SQL to find records with EXACT company match
        query = """
            WITH record_companies AS (
                SELECT
                    chatbot_history_id,
                    array_agg(res_company_id ORDER BY res_company_id) as company_array
                FROM {rel_table}
                GROUP BY chatbot_history_id
            ),
            session_last_activity AS (
                SELECT session_id, MAX(create_date) AS last_activity
                FROM chatbot_history
                WHERE session_id IS NOT NULL AND session_id != ''
                GROUP BY session_id
            )
            SELECT DISTINCT ON (ch.session_id)
                ch.session_id, ch.user_message, ch.title, ch.id, sla.last_activity
            FROM chatbot_history ch
            INNER JOIN record_companies rc ON rc.chatbot_history_id = ch.id
            INNER JOIN session_last_activity sla ON sla.session_id = ch.session_id
            WHERE ch.user_id = %s
              AND rc.company_array = %s
              AND ch.session_id IS NOT NULL
              AND ch.session_id != ''
            ORDER BY ch.session_id, ch.create_date ASC
        """.format(rel_table='chatbot_history_res_company_rel')

        self.env.cr.execute(query, (user_id, company_ids_sorted))
        results = self.env.cr.dictfetchall()

        sessions = []
        for row in results:
            # Parse message if JSON
            if row['title']:
                display_title = row['title']
            else:
                message = row['user_message'] or ''
                try:
                    msg_data = json.loads(message)
                    if isinstance(msg_data, dict):
                        message = msg_data.get('content', '') or msg_data.get('text', '') or message
                except (json.JSONDecodeError, TypeError) as e:
                    _logger.debug('Failed to parse message as JSON, using raw message: %s', str(e), exc_info=True)

                # Generate clean title
                display_title = message.strip()[:60] or 'New chat'
                if len(message) > 60:
                    display_title += '...'
                self.env.cr.execute(
                    "UPDATE chatbot_history SET title = %s WHERE id = %s",
                    (display_title, row['id'])
                )

            sessions.append({
                'session_id': row['session_id'],
                'title': display_title,
                'timestamp': row['last_activity'].isoformat() if row['last_activity'] else None,
                'id': row['id']
            })

        # Sort by most recent first
        sessions.sort(key=lambda x: x['timestamp'] or '', reverse=True)

        return sessions

    @api.model
    def get_session_title(self, session_id):
        """Title of a session, for the header of a chat restored on mount."""
        if not session_id:
            return False
        record = self.search([('session_id', '=', session_id), ('title', '!=', False)], limit=1)
        return record.title if record else False

    @api.model
    def rename_session(self,session_id, new_title):
        current_record = self.search([('session_id','=',session_id),('title', '!=', False)],limit=1)
        if current_record:
            current_record.title = new_title

    @api.model
    def delete_session(self, session_id, companyIds):
        """
        Delete a full chat session by its session_id.
        Removes ALL chatbot_history rows belonging to that session.
        """
        if not session_id:
            return False

        # Delete all records with this session_id
        records = self.search([('session_id', '=', session_id)])
        if records:
            records.unlink()
            records = self.search([('session_id', '=', session_id)])
            return True
        return False
