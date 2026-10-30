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
from unittest.mock import MagicMock, patch

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

MODULE = 'odoo.addons.cyllo_crm_google_form.models.google_form'
GET = MODULE + '.requests.get'
REFRESH = MODULE + '.GoogleForm.refresh_access_token'


def _response(payload, status=200):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    response.text = 'error'
    return response


def _submission(response_id, **answers):
    return {
        'responseId': response_id,
        'answers': {
            qid: {'textAnswers': {'answers': [{'value': val}]}}
            for qid, val in answers.items()
        },
    }


class TestGoogleFormFetch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.Lead = cls.env['crm.lead']
        cls.form = cls.env['google.form'].create({'name': 'Fetch Form'})
        cls.form.with_context(skip_google_form_url_reset=True).write(
            {'google_form_id': 'gf1', 'form_url': 'http://r.test'})
        cls.items = [
            {'title': 'Email',
             'questionItem': {'question': {'questionId': 'qe'}}},
            {'title': 'Company',
             'questionItem': {'question': {'questionId': 'qc'}}},
        ]

    def _field(self, name):
        return self.env['ir.model.fields']._get('crm.lead', name)

    def _fetch(self, pages):
        """Run a fetch where `pages` are the successive responses pages."""
        pages = list(pages)

        def side_effect(url, **kwargs):
            if url.endswith('/responses'):
                return _response(pages.pop(0))
            return _response({'items': self.items})

        with patch(GET, side_effect=side_effect), \
                patch(REFRESH, return_value='tok'):
            return self.form.fetch_responses_create_leads()

    def _leads(self):
        return self.Lead.search([('email_from', 'like', '%gform.test')])

    def test_linked_lead_does_not_block_import(self):
        self.form.lead_id = self.Lead.create({'name': 'Parent'})
        self._fetch([{'responses': [_submission('r1', qe='a@gform.test')]}])
        self.assertEqual(len(self._leads()), 1)

    def test_all_response_pages_are_fetched(self):
        self._fetch([
            {'responses': [_submission('r1', qe='a@gform.test')],
             'nextPageToken': 'p2'},
            {'responses': [_submission('r2', qe='b@gform.test')]},
        ])
        self.assertEqual(len(self._leads()), 2)

    def test_invalid_response_does_not_block_others(self):
        self.env['google.form.questions'].create({
            'name': 'Company', 'google_form_id': self.form.id,
            'lead_field_id': self._field('priority').id})
        self.form.with_context(skip_google_form_url_reset=True).write(
            {'form_url': 'http://r.test'})
        self._fetch([{'responses': [
            _submission('r1', qc='nonsense', qe='a@gform.test'),
            _submission('r2', qe='b@gform.test'),
        ]}])
        self.assertIn('b@gform.test', self._leads().mapped('email_from'))

    def test_selection_answer_matches_key_or_label(self):
        field = self._field('priority')
        key, label = self.Lead._fields['priority'].selection[-1]
        resolve = self.form._resolve_relational_value
        self.assertEqual(resolve(field, str(key)), key)
        self.assertEqual(resolve(field, label.upper()), key)
        self.assertFalse(resolve(field, 'nonsense'))

    def test_date_answers_are_validated(self):
        field = self._field('date_deadline')
        resolve = self.form._resolve_relational_value
        self.assertEqual(str(resolve(field, '2026-03-07')), '2026-03-07')
        self.assertFalse(resolve(field, 'tomorrow-ish'))

    def test_scope_error_is_shown_to_the_user(self):
        denied = _response({'error': {
            'code': 403, 'status': 'PERMISSION_DENIED',
            'message': 'Request had insufficient authentication scopes.'}}, 403)

        def side_effect(url, **kwargs):
            if url.endswith('/responses'):
                return denied
            return _response({'items': self.items})

        with patch(GET, side_effect=side_effect), \
                patch(REFRESH, return_value='tok'):
            with self.assertRaisesRegex(
                    ValidationError, 'insufficient authentication scopes'):
                self.form.fetch_responses_create_leads()

    def test_structure_error_is_shown_to_the_user(self):
        with patch(GET, return_value=_response({}, 500)), \
                patch(REFRESH, return_value='tok'):
            with self.assertRaises(ValidationError):
                self.form.fetch_responses_create_leads()
