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
    'name': 'Cyllo Support Service',
    'category': 'Support Service',
    'summary': 'Support Service management',
    'description': """This module provide support to the end users 
     and troubleshoot issues""",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['sale_management', 'hr_timesheet', 'cyllo_portal',
                'cyllo_web', 'repair', 'cyllo_facebook', 'sale_timesheet'],
    'icon': '/cyllo_support_service/static/description/support-service.svg',
    'data': [
        'security/support_service_ticket_security.xml',
        'security/ir.model.access.csv',

        'data/ir_cron_data.xml',
        'data/support_service_stage_data.xml',
        'data/support_service_ticket_templates_data.xml',
        'data/support_service_ticket_data.xml',

        'views/support_service_overview_action.xml',
        'views/sale_order_views.xml',
        'views/support_service_analysis_views.xml',
        'views/support_service_inactivity_views.xml',
        'views/support_service_ticket_views.xml',
        'views/support_service_my_ticket_action.xml',
        'views/support_service_category_views.xml',
        'views/support_service_tag_views.xml',
        'views/support_service_stage_views.xml',
        'views/support_service_team_views.xml',
        'views/support_service_portal_templates.xml',
        'views/cyllo_support_service_menu.xml',

        'wizards/account_move_reversal.xml',
        'wizards/support_ticket_timesheet.xml',
        'wizards/repair_order_wizard.xml',

        'reports/cyllo_support_service_reports.xml',
        'reports/support_service_ticket_templates.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'cyllo_support_service/static/src/scss/support_service.scss',
            'cyllo_support_service/static/src/views/support_service_overview.xml',
            'cyllo_support_service/static/src/views/support_service_team_kanbanview.xml',
            'cyllo_support_service/static/src/js/support_service_overview.js',
            'cyllo_support_service/static/src/js/support_service_team_kanbanview.js',
            'cyllo_support_service/static/src/js/support_service_timer.js',
            '/cyllo_support_service/static/src/js/chatter_action.js',
            '/cyllo_support_service/static/src/js/chatter_container.js'
        ],
        'web.assets_frontend': [
            'cyllo_support_service/static/src/scss/support_service_portal.scss',
            'cyllo_support_service/static/src/js/support_service_ticket.js',
            'cyllo_support_service/static/src/js/support_service_ticket_form.js',
        ],
    },
}
