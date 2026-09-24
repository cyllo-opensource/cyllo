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
    'name': 'Cyllo Document Management',
    'summary': 'The Document Management module to access document tools',
    'description': 'The Document Management module provide a quick access'
                   ' to create, share and delete.',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'category': 'Document Management',
    'depends': ['mail', 'hr', 'cyllo_base', 'cyllo_portal', 'website', 'cyllo_spreadsheet'],
    'external_dependencies': {'python': ['linkpreview']},
    'icon': '/cyllo_documents/static/description/documents.svg',
    'data': [
        'data/ir_cron_data.xml',
        'data/ir_sequence_data.xml',
        'data/document_workspace_data.xml',

        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',

        'views/document_tag_views.xml',
        'views/document_template_request_views.xml',
        'views/document_request_template_views.xml',
        'views/google_drive_connector_views.xml',
        'views/one_drive_connector_views.xml',
        'views/document_delete_trash_views.xml',
        'views/document_lock_views.xml',
        'views/document_workspace_views.xml',
        'views/document_file_views.xml',
        'views/res_config_settings_views.xml',
        'wizards/document_request_accept_views.xml',
        'wizards/document_request_reject_views.xml',
        'views/request_document_views.xml',
        'views/document_trash_views.xml',
        'views/cyllo_documents_menu.xml',

        'templates/document_request_portal_templates.xml',
        'templates/document_request_portal_form.xml',
        'templates/document_share_preview.xml',
        'templates/document_template_request_portal_templates.xml',
        'templates/document_portal_templates.xml',
        'templates/portal_document_templates.xml',
        'reports/report_document_download.xml',
        'reports/reports.xml',

        'wizards/document_share_views.xml',
        'wizards/document_url_views.xml',
        'wizards/work_space_views.xml',
        'wizards/mail_compose_message_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://cdn.jsdelivr.net/npm/pdfjs-dist/build/pdf.min.js',
            'cyllo_documents/static/src/css/kanban.css',
            'cyllo_documents/static/src/css/style.css',
            'cyllo_documents/static/src/js/document_preview_action.js',
            'cyllo_documents/static/src/xml/document_preview_template.xml',
            'cyllo_documents/static/src/js/widget/*',
            'cyllo_documents/static/src/view/doc_view/*',
            'cyllo_documents/static/src/view/calender_view/*',
            'cyllo_documents/static/src/view/list_view/*',
        ],
        'web.assets_frontend': [
            'https://cdn.jsdelivr.net/npm/pdfjs-dist/build/pdf.min.js',
            'cyllo_documents/static/src/js/my_portal.js',
            'cyllo_documents/static/src/js/portal_document_request.js',
            'cyllo_documents/static/src/js/document_request_portal.js',
            'cyllo_documents/static/src/css/document_portal.css',
            'cyllo_documents/static/src/scss/document_request_portal.scss'
        ],
        'web.qunit_suite_tests': [
            'cyllo_documents/static/src/tests/cyllo_documents_delete_trash_test.js',
            'cyllo_documents/static/src/tests/cyllo_documents_file_test.js',
            'cyllo_documents/static/src/tests/cyllo_documents_template_test.js',
            'cyllo_documents/static/src/tests/cyllo_documents_workspace_test.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
