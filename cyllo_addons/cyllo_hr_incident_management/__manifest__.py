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
    'name': "Cyllo Employee Incident Management",
    'category': 'Human Resources',
    'summary': """Efficiently manage and track employee incidents with a comprehensive incident management solution.""",
    'description': 'Cyllo Employee Incident Management provides a streamlined approach to managing employee incidents '
                   'within your organization. From incident reporting to resolution, this module offers a '
                   'user-friendly interface for HR managers and employees alike. Key features include incident '
                   'categorization, incident tracking, email notifications, and customizable incident reports.',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_hr', 'cyllo_portal', 'cyllo_base', 'mail', 'cyllo_sales'],
    'demo': [
        'demo/hr_incident_category_demo.xml',
        'demo/hr_incident_demo.xml',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_incident_security.xml',
        'data/hr_incident_sequence_data.xml',
        'data/mail_template_data.xml',
        'views/hr_incident_views.xml',
        'views/hr_incident_category_views.xml',
        'views/incident_management_portal_view.xml',
        'views/incident_management_portal_templates.xml',
        'reports/report_hr_incident_templates.xml',
        'reports/reports.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_hr_incident_management/static/src/scss/incident_portal.scss',
            'cyllo_hr_incident_management/static/src/js/incident_request_form.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
