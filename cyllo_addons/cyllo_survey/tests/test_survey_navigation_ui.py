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
##############################################################################
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestSurveyNavigationUi(HttpCase):

    def test_navigation_after_finish(self):
        """A double click on finish and the arrow-left key on the finished
        screen must not resubmit the completed survey (no error banner)."""
        survey = self.env['survey.survey'].create({
            'title': 'Navigation Survey',
            'access_mode': 'public',
            'users_login_required': False,
            'users_can_go_back': True,
            'questions_layout': 'page_per_question',
        })
        self.env['survey.question'].create({
            'survey_id': survey.id,
            'title': 'Your name',
            'question_type': 'char_box',
            'constr_mandatory': True,
        })
        self.start_tour('/survey/start/%s' % survey.access_token, 'cyllo_survey_navigation_after_finish')
        answer = self.env['survey.user_input'].search([('survey_id', '=', survey.id)])
        self.assertEqual(len(answer), 1)
        self.assertEqual(answer.state, 'done')
        self.assertEqual(answer.user_input_line_ids.value_char_box, 'Alice')
