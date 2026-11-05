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
##############################################################################

{
    'name': 'Cyllo Survey',
    'category': 'Marketing/Surveys',
    'summary': "File upload question type for surveys",
    'description': """Adds an Upload File question type to surveys so participants
    can answer by uploading a file of up to 100 KB.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['survey'],
    'data': [
        'views/survey_question_views.xml',
        'views/survey_user_views.xml',
        'views/survey_templates.xml',
    ],
    'assets': {
        'survey.survey_assets': [
            'cyllo_survey/static/src/js/survey_form_upload.js',
            'cyllo_survey/static/src/js/survey_form_layout.js',
            'cyllo_survey/static/src/js/survey_form_navigation.js',
            'cyllo_survey/static/src/scss/survey_form.scss',
        ],
        'web.assets_tests': [
            'cyllo_survey/static/tests/tours/*.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': True,
    'application': False,
}
