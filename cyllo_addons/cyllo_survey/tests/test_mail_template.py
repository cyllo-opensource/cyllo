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
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestSurveyInviteBranding(TransactionCase):

    def test_invite_button_colour_all_languages(self):
        """The invite email button turns Cyllo green in every installed
        language, the translated text is kept, and a second run changes nothing."""
        self.env['res.lang']._activate_lang('fr_FR')
        template = self.env.ref('survey.mail_template_user_input_invite')
        template.with_context(lang='en_US').body_html = '<p>Hello <a style="background-color: #875A7B">Start</a></p>'
        template.with_context(lang='fr_FR').body_html = '<p>Bonjour <a style="background-color: #875a7b">Commencer</a></p>'

        self.env['mail.template']._cyllo_brand_survey_invite_template()
        en_body = template.with_context(lang='en_US').body_html
        fr_body = template.with_context(lang='fr_FR').body_html
        for body in (en_body, fr_body):
            self.assertIn('#9ea700', body)
            self.assertNotIn('#875a7b', body.lower())
        self.assertIn('Hello', en_body)
        self.assertIn('Bonjour', fr_body)
        self.assertIn('Commencer', fr_body)

        self.env['mail.template']._cyllo_brand_survey_invite_template()
        self.assertEqual(template.with_context(lang='fr_FR').body_html, fr_body)
        self.assertEqual(template.with_context(lang='en_US').body_html, en_body)
