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
import json
from odoo.tests.common import TransactionCase

class TestChatbotHistory(TransactionCase):
    """
    Test cases for 'chatbot.history' model, covering session management,
    renaming, and deletion.
    """

    def setUp(self):
        """
        Setup test data for chatbot history tests including multiple sessions.
        """
        super(TestChatbotHistory, self).setUp()
        self.ChatbotHistory = self.env['chatbot.history']
        self.user = self.env.user
        self.company = self.env.company
        
        # Create Dummy Histories
        self.history_1 = self.ChatbotHistory.create({
            'user_id': self.user.id,
            'session_id': 'session_1',
            'title': 'Chat 1',
            'user_message': json.dumps({'content': 'Hello'}),
            'response_message': 'Hi there',
            'company_ids': [(4, self.company.id)]
        })
        
        self.history_2 = self.ChatbotHistory.create({
            'user_id': self.user.id,
            'session_id': 'session_1',
            'user_message': 'How are you?',
            'company_ids': [(4, self.company.id)]
        })

        self.history_3 = self.ChatbotHistory.create({
            'user_id': self.user.id,
            'session_id': 'session_2',
            'user_message': 'New Topic',
            'company_ids': [(4, self.company.id)]
        })

    def test_get_user_sessions(self):
        """
        Test the retrieval of unique chatbot sessions for the current user.
        """
        sessions = self.ChatbotHistory.get_user_sessions([self.company.id])
        
        # Should have 2 distinct sessions
        self.assertEqual(len(sessions), 2)
        session_ids = [s['session_id'] for s in sessions]
        self.assertIn('session_1', session_ids)
        self.assertIn('session_2', session_ids)
        
        # Check title generation logic (history_1 has explicit title)
        session_1 = next(s for s in sessions if s['session_id'] == 'session_1')
        self.assertEqual(session_1['title'], 'Chat 1')

    def test_rename_session(self):
        """
        Test the functionality to rename an existing chatbot session.
        """
        self.ChatbotHistory.rename_session('session_1', 'Renamed Chat')
        # Verification: write should update the cache
        self.assertEqual(self.history_1.title, 'Renamed Chat')

    def test_delete_session(self):
        """
        Test the functionality to delete all history records associated with a session.
        """
        res = self.ChatbotHistory.delete_session('session_1', [self.company.id])
        self.assertTrue(res)
        
        # Verify records are gone
        remaining = self.ChatbotHistory.search([('session_id', '=', 'session_1')])
        self.assertFalse(remaining)
        
        # Session 2 should remain
        remaining_2 = self.ChatbotHistory.search([('session_id', '=', 'session_2')])
        self.assertTrue(remaining_2)
