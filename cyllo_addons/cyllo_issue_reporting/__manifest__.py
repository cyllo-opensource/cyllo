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
#############################################################################

{
    'name': 'Cyllo Issue Reporting',
    'category': 'Technical',
    "summary": """Enables users to capture and report frontend or backend runtime errors directly from system dialogs into an internal issue-tracking system, with support for escalating tickets to Cyllo Support via API.""",
    'description': """The Cyllo Issue Reporting module enhances error handling and diagnostics within the platform. When an unexpected error occurs—such as a Python backend exception, JavaScript client failure, XML render issue, or user warning—the module patches the web client's error dialogs to present a direct reporting option to authorized users .""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base', 'web','mail'],
    'icon':'cyllo_issue_reporting/static/description/cyllo_issue_reporting.svg',
    'data': [
        # security
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        # data
        "data/issue_sequence_number.xml",
        "data/partner_api_data.xml",
        #view
        "views/res_config_settings_view.xml",
        "views/res_users_view.xml",
        "views/issue_report_view.xml",
        "views/issue_report_menu.xml",
        #wizards
        "wizards/error_report_wizard_views.xml",
        "wizards/partner_transfer_wizard_view.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_issue_reporting/static/src/js/error_dialogs.js',
            'cyllo_issue_reporting/static/src/xml/error_dialog.xml',
            'cyllo_issue_reporting/static/src/js/issue_report_notification.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}