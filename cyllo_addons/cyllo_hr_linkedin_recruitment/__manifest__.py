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
{
    'name': 'Cyllo Advanced HR-LinkedIn Integration',
    'summary': "Basic module for LnkedIn-HR Recruitment connector",
    'description': """The LinkedIn-HR Recruitment Connector Basic Module is
    designed to optimize your recruitment workflow, offering a comprehensive 
    suite of features to enhance candidate sourcing and selection.""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'category': 'Generic Modules/Human Resources',
    'depends': ['hr_recruitment', 'auth_oauth'],
    'data': [
        'data/auth_linkedin_data.xml',
        'security/ir.model.access.csv',
        'views/recruitment_config_settings.xml',
        'views/hr_job_linkedin_likes_comments_views.xml',
        'views/linkedin_comments_views.xml',
    ],
    'external_dependencies':
        {
        'python': ['mechanize', 'python-linkedin'],
        },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
