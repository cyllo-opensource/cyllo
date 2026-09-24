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
    'name': "Cyllo Employee Service/Custody Management",
    'category': 'Human Resources',
    'summary': """A Module to handle employee service and custody""",
    'description': 'module is designed to streamline the management of employee services and custody within an '
                   'organization. It provides a comprehensive solution for tracking various aspects related to '
                   'employee services',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_hr', 'cyllo_portal', 'hr_maintenance', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'views/hr_service_views.xml',
        'views/hr_service_category_views.xml',
        'views/maintenance_request_views.xml',
        'views/service_management_portal_templates.xml',
        'views/service_portal_views.xml',
        'reports/hr_service_report_template.xml',
        'reports/reports.xml',
        'wizards/late_return_reason.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_hr_service_management/static/src/scss/service_portal.scss',
            'cyllo_hr_service_management/static/src/js/ServicePortal.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
