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
"""
Agent working state (Postgres-backed).

Distinct from ``chatbot.history`` (the user-facing display transcript): this
holds the *engine's* working state — LLM-format messages, context baseline,
token counts, pending confirmation — one row per session, rewritten each turn.
Ephemeral by design and garbage-collected by cron.
"""
from datetime import timedelta

from odoo import api, fields, models


class ChatbotSession(models.Model):
    _name = 'chatbot.session'
    _description = 'Chatbot Agent Working State'

    session_id = fields.Char(required=True, index=True)
    user_id = fields.Many2one(
        'res.users', required=True, index=True,
        default=lambda self: self.env.user,
    )
    state = fields.Json(help="Serialized engine working state (SessionState).")
    last_active = fields.Datetime(default=fields.Datetime.now, index=True)
    status = fields.Selection(
        [('active', 'Active'), ('closed', 'Closed')],
        default='active',
    )

    @api.model
    def get_or_create(self, session_id):
        """Return the working-state row for ``session_id`` (current user)."""
        record = self.search([
            ('session_id', '=', session_id),
            ('user_id', '=', self.env.uid),
        ], limit=1)
        if not record:
            record = self.create({'session_id': session_id})
        return record

    def save_state(self, state_dict):
        """Persist the serialized state blob and bump activity timestamp."""
        self.ensure_one()
        self.write({'state': state_dict, 'last_active': fields.Datetime.now()})

    @api.model
    def _gc_sessions(self, max_idle_days=7):
        """Cron: delete sessions idle beyond ``max_idle_days``."""
        cutoff = fields.Datetime.now() - timedelta(days=max_idle_days)
        stale = self.search([('last_active', '<', cutoff)])
        count = len(stale)
        stale.unlink()
        return count
