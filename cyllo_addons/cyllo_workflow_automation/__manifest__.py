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
    'name': 'Cyllo Workflow Automation',
    'summary': "Automate workflows and streamline processes with Cyllo Workflow Automation.",
    'description': """The Cyllo Workflow Automation module empowers users to create, manage, and automate complex workflows across different modules within the Cyllo ecosystem. Designed to enhance productivity, this module allowing users to define custom triggers, automate actions such as record creation, updates, deletions, and handle on-change events effortlessly. """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['base', 'cyllo_base', 'web'],
    'icon': '/cyllo_workflow_automation/static/description/workflow-icon.svg',
    'data': [
        'security/workflow_group.xml',
        'security/ir.model.access.csv',
        'data/create.xml',
        'data/write.xml',
        'data/unlink.xml',
        'data/schedule.xml',
        'data/onchange.xml',
        'data/loop.xml',
        'views/views.xml',
        'views/cyllo_base_automation_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.9.6/lottie.min.js',
            'https://unpkg.com/blockly/blockly.min.js',
            'cyllo_workflow_automation/static/src/xml/*.xml',
            'cyllo_workflow_automation/static/src/css/style.scss',
            'cyllo_workflow_automation/static/src/css/condition.scss',
            'cyllo_workflow_automation/static/src/css/work_auto.scss',
            'cyllo_workflow_automation/static/src/js/utils/*',
            'cyllo_workflow_automation/static/src/js/cache.js',
            'cyllo_workflow_automation/static/src/js/components/configurationBase/configurationBase.xml',
            'cyllo_workflow_automation/static/src/js/automationComponents/**/*',
            'cyllo_workflow_automation/static/src/js/*.js',
            'cyllo_workflow_automation/static/src/js/components/**/*.*',
            'cyllo_workflow_automation/static/src/lib/*',
            'cyllo_workflow_automation/static/src/views/workflowCardView/**/*',
            'cyllo_workflow_automation/static/src/js/field/**/*',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_post_init_hook',
}
