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
from odoo import fields
from odoo.tests import common


class TestConversationHistory(common.TransactionCase):
    """Tests for the Studio AI conversation history."""

    def test_create_defaults(self):
        """A new conversation defaults to the current user and creation time."""
        before = fields.Datetime.now()
        history = self.env['conversation.history'].create({
            'name': 'Build a sales dashboard',
        })
        self.assertEqual(history.user_id, self.env.user)
        self.assertTrue(history.created_at)
        self.assertGreaterEqual(history.created_at, before)

    def test_prompts_and_responses_are_stored(self):
        """The prompt/response transcript round-trips through the record."""
        history = self.env['conversation.history'].create({
            'name': 'Add a field',
            'prompts': 'Add a customer rating field',
            'responses': 'Created field x_rating on res.partner',
        })
        self.assertEqual(history.prompts, 'Add a customer rating field')
        self.assertEqual(history.responses,
                         'Created field x_rating on res.partner')

    def test_conversation_belongs_to_its_author(self):
        """Conversations created by another user are attributed to them."""
        user = self.env['res.users'].create({
            'name': 'Studio AI Tester',
            'login': 'studio_ai_tester',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        history = self.env['conversation.history'].with_user(user).create({
            'name': 'User owned conversation',
        })
        self.assertEqual(history.user_id, user)

    def test_history_is_searchable_by_user(self):
        """Conversations can be filtered per user."""
        history = self.env['conversation.history'].create({'name': 'Mine'})
        found = self.env['conversation.history'].search([
            ('user_id', '=', self.env.user.id),
            ('name', '=', 'Mine'),
        ])
        self.assertIn(history, found)
