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
    'name': 'Cyllo Audit Log System',
    'summary': """Track create, update, delete, and read activities with company-wise audit visibility.""",
    'description': """
        Audit Log System helps administrators monitor business operations with configurable audit rules.
        It records create, write, unlink, and optional read actions, captures field-level changes, and
        links events with user sessions and HTTP requests for better traceability.
        Key features:
        - Rule-based auditing per model
        - Field-level tracking (track selected fields or exclude fields)
        - User/group-based tracking filters
        - Session and HTTP request logging
        - Retention policy with manual cleanup support
        - Reporting view
        - Multi-company visibility control using company-specific rules
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'icon': '/cyllo_auditlog/static/description/audit-log-system.svg',
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/audit_log_views.xml',
        'views/audit_rule_views.xml',
        'views/auditlog_http_request_views.xml',
        'views/audit_menus.xml'
    ],
    'demo': [
        'demo/audit_rule_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_auditlog/static/src/scss/audit_log.scss',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
