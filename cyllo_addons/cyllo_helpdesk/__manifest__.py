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
    'name': 'Cyllo Help Desk',
    'category': 'Services/Helpdesk',
    'summary': """Help Desk Management""",
    'description': "Manage helpdesk tickets, SLAs, teams, reporting, dashboard, ratings, and daily targets.",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base', 'mail', 'rating', 'portal', 'resource'],
    'icon': '/cyllo_helpdesk/static/description/Help desk.svg',
    'data': [
        'security/cyllo_helpdesk_security_group.xml',
        'security/ir.model.access.csv',
        'data/helpdesk_stage_data.xml',
        'data/cyllo_helpdesk_mail_template.xml',
        'data/cyllo_helpdesk_rating_template.xml',
        'reports/helpdesk_ticket_report.xml',
        'reports/helpdesk_ticket_report_templates.xml',
        'reports/helpdesk_ticket_pdf_report.xml',
        'reports/helpdesk_ticket_pdf_report_templates.xml',
        'wizard/helpdesk_report_views.xml',
        'wizard/helpdesk_ticket_merge_wizard_views.xml',
        'data/helpdesk_ticket_cron.xml',
        'views/helpdesk_portal_templates.xml',
        'views/helpdesk_overview_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/helpdesk_my_ticket_views.xml',
        'views/helpdesk_analysis_views.xml',
        'views/helpdesk_category_views.xml',
        'views/helpdesk_tag_views.xml',
        'views/helpdesk_stage_views.xml',
        'views/helpdesk_team_views.xml',
        'views/helpdesk_sla_views.xml',
        'views/sla_status_views.xml',
        'views/helpdesk_canned_response_views.xml',
        'views/customer_rating_view.xml',
        'data/default_group_data.xml',
        'data/helpdesk_common_issue_data.xml',
        'views/helpdesk_common_issue_views.xml',
        'views/helpdesk_menu.xml',
    ],
    'demo': [
        'demo/demo_helpdesk.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_helpdesk/static/src/views/helpdesk_overview.xml',
            'cyllo_helpdesk/static/src/js/helpdesk_overview.js',
            'cyllo_helpdesk/static/src/views/helpdesk_team_kanbanview.xml',
            'cyllo_helpdesk/static/src/js/helpdesk_team_kanbanview.js',
            'cyllo_helpdesk/static/src/views/ticket_issue_suggestions.xml',
            'cyllo_helpdesk/static/src/js/ticket_issue_suggestions.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
