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
    'name': 'Cyllo Analytics',
    'category': 'Extra Tools',
    'summary': """This module helps businesses with the ability to transform raw data into actionable insights""",
    'description': 'Cyllo Dashboard is a robust module amplifying data analytics and reporting in cyllo ERP. It '
                   'converts raw data into actionable insights, empowering informed decisions and strategic planning.',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_base', 'web', 'base_automation', 'mail'],
    'icon': '/cyllo_analytics/static/description/analytics.svg',
    'data': [
        'security/dashboard_config_security.xml',
        'security/ir.model.access.csv',
        'data/banner/dashboard_banner.xml',
        'data/dashboard_sheet_type_data.xml',
        'data/calculation_preset_data.xml',
        'data/dashboard_global_filter_data.xml',
        'data/theme/dashboard_theme_cyllo.xml',
        'data/theme/dashboard_theme_walden.xml',
        'data/theme/dashboard_theme_infographic.xml',
        'data/theme/dashboard_theme_roma.xml',
        'data/theme/dashboard_theme_chalk.xml',
        'data/theme/dashboard_theme_essos.xml',
        'data/theme/dashboard_theme_macarons.xml',
        'data/theme/dashboard_theme_vintage.xml',
        'data/theme/dashboard_theme_wonderland.xml',
        'data/theme/dashboard_theme_westeros.xml',
        'data/theme/dashboard_theme_purple_passion.xml',
        'data/theme/dashboard_theme_shine.xml',
        'data/sheet/dashboard_line_sheet_data.xml',
        'wizard/import_xlsx_wizard_views.xml',
        'views/dashboard_config_views.xml',
        'views/custom_imported_table_views.xml',
        'views/calculation_preset_views.xml',
        'views/dashboard_sheet.xml',
        'views/cyllo_dashboard_templates.xml',
        'views/res_config_settings_views.xml',
        'data/ir_cron_data.xml',
    ],
    'uninstall_hook': 'cyllo_d_uninstall_hook',
    'post_init_hook': 'cyllo_d_post_init_hook',
    "external_dependencies": {
        'python': ['openai', 'tiktoken', 'openpyxl']
    },
    'assets': {
        'web.assets_backend': [
            'cyllo_analytics/static/src/lib/codeMirror/*',
            'cyllo_analytics/static/src/lib/gridStack/*',
            'https://cdn.jsdelivr.net/npm/reveal.js@4.1.0/dist/reveal.js',
            'https://cdn.jsdelivr.net/npm/reveal.js@4.1.0/dist/reveal.css',
            'https://cdn.jsdelivr.net/npm/reveal.js@4.1.0/dist/theme/white.css',
            'https://unpkg.com/markdown-it@12.2.0/dist/markdown-it.min.js',
            'cyllo_analytics/static/src/lib/*',
            'https://cdn.jsdelivr.net/npm/echarts-stat@1.2.0/dist/ecStat.min.js',
            'cyllo_analytics/static/src/lib/eChart/*',
            # CSS load order is explicit (was a css/* glob) to preserve the cascade
            # after splitting style.css per-template: base scss, then the common
            # style.css, then per-template files (which may override the common base).
            'cyllo_analytics/static/src/css/ai.scss',
            'cyllo_analytics/static/src/css/kpi.scss',
            'cyllo_analytics/static/src/css/style.css',
            'cyllo_analytics/static/src/css/FieldTraversalDialog.css',
            'cyllo_analytics/static/src/css/alert_configuration_dialog.css',
            'cyllo_analytics/static/src/css/cyllo_dashboard.css',
            'cyllo_analytics/static/src/css/cyllo_sheet.css',
            'cyllo_analytics/static/src/css/drag_n_drop.css',
            'cyllo_analytics/static/src/css/edit_dashboard.css',
            'cyllo_analytics/static/src/css/explain_with_ai_modal.css',
            'cyllo_analytics/static/src/css/fieldAutoComplete.css',
            'cyllo_analytics/static/src/css/filter_dropdown.css',
            'cyllo_analytics/static/src/css/graph_tile.css',
            'cyllo_analytics/static/src/css/kpi_sheet.css',
            'cyllo_analytics/static/src/css/menu_dialog_templates.css',
            'cyllo_analytics/static/src/css/presentation.css',
            'cyllo_analytics/static/src/css/presentation_maker.css',
            'cyllo_analytics/static/src/css/preset_apply_dialog.css',
            'cyllo_analytics/static/src/css/select_user.css',
            'cyllo_analytics/static/src/css/sheetDomainSelector.css',
            'cyllo_analytics/static/src/css/sheetFilterDomain.css',
            'cyllo_analytics/static/src/css/tile_card.css',
            'cyllo_analytics/static/src/css/tile_controller.css',
            'cyllo_analytics/static/src/css/tree_editor.css',
            'cyllo_analytics/static/src/views/tile/*',
            'cyllo_analytics/static/src/views/tile/components/*',
            'cyllo_analytics/static/src/views/tile/tile_searchbar/*',
            'cyllo_analytics/static/src/xml/cyllo_dashboard.xml',
            'cyllo_analytics/static/src/xml/configuration_dialog.xml',
            'cyllo_analytics/static/src/xml/menu_dialog_templates.xml',
            'cyllo_analytics/static/src/xml/delete_dialog_templates.xml',
            'cyllo_analytics/static/src/xml/edit_dashboard.xml',
            'cyllo_analytics/static/src/xml/presentation_maker.xml',
            'cyllo_analytics/static/src/xml/cyllo_sheet.xml',
            'cyllo_analytics/static/src/xml/import_dialog.xml',
            'cyllo_analytics/static/src/xml/drag_n_drop.xml',
            'cyllo_analytics/static/src/xml/FieldTraversalDialog.xml',
            'cyllo_analytics/static/src/xml/kpi_sheet.xml',
            'cyllo_analytics/static/src/xml/filter_dropdown.xml',
            'cyllo_analytics/static/src/js/cyllo_dashboard.js',
            'cyllo_analytics/static/src/js/query/query_manager.js',
            'cyllo_analytics/static/src/js/mixin/*',
            'cyllo_analytics/static/src/js/*',
            'cyllo_analytics/static/src/js/table/*',
            'cyllo_analytics/static/src/js/presentation/*',
            'cyllo_analytics/static/src/js/charts/*',
            'cyllo_analytics/static/src/js/explain_with_ai/components/*',
            'cyllo_analytics/static/src/js/explain_with_ai/*',
            'cyllo_analytics/static/src/js/presentation/components/*',
            'cyllo_analytics/static/src/js/sheet_filter/*',
            'cyllo_analytics/static/src/js/editor/*',
            'cyllo_analytics/static/src/js/fields/*',
            'cyllo_analytics/static/src/js/presets/preset_apply_dialog.js',
            'cyllo_analytics/static/src/xml/presets/preset_apply_dialog.xml',
            'cyllo_analytics/static/src/js/imported_table_list_view.js',
            'cyllo_analytics/static/src/xml/imported_table_list_view.xml',
            'cyllo_analytics/static/src/js/alert_configuration_dialog.js',
            'cyllo_analytics/static/src/xml/alert_configuration_dialog.xml',
            'cyllo_analytics/static/src/js/cyllo_analytics_notifications.js',
            'cyllo_analytics/static/src/tests/tours/dashboard_onboarding.js',
        ],
        "web.qunit_suite_tests": [
            'cyllo_analytics/static/src/tests/*',
        ]
    },
    'images': [
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}