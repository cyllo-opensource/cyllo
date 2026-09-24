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
    'name': 'Cyllo Field Service',
    'category': 'Sales/CRM',
    'summary': """Efficiently manage field service requests with Cyllo Field Service""",
    'description': "Cyllo Field Service is a comprehensive solution for managing field service requests. Streamline "
                   "your operations, track service requests, assign tasks, and enhance customer satisfaction. "
                   "With features such as skill-based assignment, service templates, and detailed reporting, Cyllo "
                   "Field Service is designed to meet the needs of modern service-oriented businesses.",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['sale_management', 'hr_skills', 'cyllo_base', 'cyllo_portal'],
    'icon': '/cyllo_field_service/static/description/field-services.svg',
    'data': [
        'security/field_service_request_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/ir_sequence_data.xml',
        'data/product_data.xml',
        'views/field_service_skill_category_views.xml',
        'views/field_service_request_views.xml',
        'views/field_service_request_form_template.xml',
        'views/fs_service_request_portal_template.xml',
        'views/res_config_settings_views.xml',
        'wizards/field_service_report_views.xml',
        'wizards/field_service_employee_suggestion.xml',
        'reports/field_service_reports_templates.xml',
        'reports/field_service_reports.xml',
        'data/mail_template_data.xml',
        'views/res_partner_views.xml',
        'views/field_service_menus.xml',

    ],
    'assets': {
        'web.assets_frontend': [
            'cyllo_field_service/static/src/scss/service_request_portal.scss',
            'cyllo_field_service/static/src/js/fieldServicePublicWidget.js',
            'cyllo_field_service/static/src/js/fieldServiceRequest.js'
        ],
        'web.qunit_suite_tests': [
            'cyllo_field_service/static/src/tests/field_service_create_request_tests.js',
            'cyllo_field_service/static/src/tests/field_service_form_tests.js',
        ],
        'web.assets_backend':[
            'cyllo_field_service/static/src/js/availability_status_widget.js',
            'cyllo_field_service/static/src/xml/availability_status_widget.xml',
            'cyllo_field_service/static/src/scss/is_available_worker.scss'
        ]
    },

    'demo': [
        'demo/demo_field_service.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
