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
    'name': 'Cyllo Studio',
    'summary': 'No-code app builder for Cyllo',
    'description': 'Customize Cyllo without code: design models and fields, '
                   'adjust form, list and kanban layouts by drag-and-drop, '
                   'build report templates and manage access rights and '
                   'record rules.',
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['web', 'web_hierarchy', 'mail', 'cyllo_base', 'cyllo_web'],
    'post_init_hook': 'post_init_hook',
    'data': [
        'security/studio_group.xml',
        'security/ir.model.access.csv',
        'views/open_studio_action.xml',
        'views/ir_actions_report_views.xml',
        'views/ir_model_access_views.xml',
        'views/ir_rule_views.xml',
        'views/ir_model_fields.xml',
        'views/qr_analytics_views.xml',
        'views/report_template_library_views.xml',
    ],
    'assets': {
    'web_editor.backend_assets_wysiwyg': [
            'cyllo_studio/static/src/js/custom_report/studio_report.js',
        ],
        'web.assets_backend': [
            'cyllo_studio/static/src/js/report_view.js',
            'cyllo_studio/static/src/xml/report_view.xml',
            'cyllo_studio/static/src/js/systray/systray.css',
            'cyllo_studio/static/src/js/systray/systray_icon.js',
            'cyllo_studio/static/src/js/systray/systray_icon.xml',
            'cyllo_studio/static/src/js/views/cyllo_kanban/report_thumbnail_lazy.js',

            ('include', 'web_editor.backend_assets_wysiwyg'),
            ('include', 'cyllo_studio.assets_backend'),
        ],
        'cyllo_studio.assets_backend': [
            'cyllo_studio/static/src/lib/medium_editor/medium-editor.min.js',
            'cyllo_studio/static/src/lib/medium_editor/studio-editor-undo-redo-ext.js',
            'cyllo_studio/static/src/lib/medium_editor/medium-editor.min.css',
            'cyllo_studio/static/src/lib/medium_editor/default.min.css',
            'cyllo_studio/static/src/js/studio_field_selector_popover.js',

            'cyllo_studio/static/src/lib/dragula/dragula.min.js',
            'cyllo_studio/static/src/lib/dragula/dragula.min.css',
            'cyllo_studio/static/src/lib/sortablejs/Sortable.min.js',
            'cyllo_studio/static/src/lib/sortablejs/Sortable.js',
            'cyllo_studio/static/src/lib/auto_scroll/auto_scroll.min.js',
            'cyllo_studio/static/src/lib/jqueryui/jquery.min.js',
            'cyllo_studio/static/src/lib/flatted/min.js',
            'cyllo_studio/static/src/lib/html2canvas/html2canvas.min.js',

            'cyllo_studio/static/src/css/style.css',
            'cyllo_studio/static/src/css/theme_rtl.scss',
            'cyllo_studio/static/src/css/report_kanban.scss',

            'cyllo_studio/static/src/js/web_client.js',
            'cyllo_studio/static/src/js/web_client.xml',
            'cyllo_studio/static/src/js/menu_service.js',
            'cyllo_studio/static/src/js/layout.js',
            'cyllo_studio/static/src/js/layout.xml',
            'cyllo_studio/static/src/js/action_container.js',
            'cyllo_studio/static/src/js/action_container.xml',
            'cyllo_studio/static/src/js/select_create_dialog.js',

            'cyllo_studio/static/src/js/root/studio_wrapper_main.js',
            'cyllo_studio/static/src/js/root/studio_wrapper_main.xml',


            'cyllo_studio/static/src/js/actions/utils.js',
            'cyllo_studio/static/src/js/actions/view_reload.js',

            'cyllo_studio/static/src/js/root/studio_utils.js',
            'cyllo_studio/static/src/js/root/studio_wrapper.js',
            'cyllo_studio/static/src/js/root/studio_wrapper.xml',

            'cyllo_studio/static/src/js/studio_menu_sidebar/dialog/dialog.js',
            'cyllo_studio/static/src/js/studio_menu_sidebar/dialog/dialog.xml',
            'cyllo_studio/static/src/js/studio_menu_sidebar/dialog/dialog.scss',
            'cyllo_studio/static/src/js/studio_menu_sidebar/menu_sidebar.css',
            'cyllo_studio/static/src/js/studio_menu_sidebar/menu_sidebar.js',
            'cyllo_studio/static/src/js/studio_menu_sidebar/menu_sidebar.xml',
            'cyllo_studio/static/src/js/studio_menu_sidebar/studio_menu_sidebar.css',
            'cyllo_studio/static/src/js/studio_menu_sidebar/studio_menu_sidebar.js',
            'cyllo_studio/static/src/js/studio_menu_sidebar/studio_menu_sidebar.xml',


            'cyllo_studio/static/src/js/navbar/navbar.css',
            'cyllo_studio/static/src/js/navbar/navbar.js',
            'cyllo_studio/static/src/js/navbar/navbar.xml',
            'cyllo_studio/static/src/js/navbar/new_app_ai.scss',

            'cyllo_studio/static/src/js/navbar/view_selection_dropdown/*.js',
            'cyllo_studio/static/src/js/navbar/view_selection_dropdown/*.xml',
            'cyllo_studio/static/src/js/navbar/view_selection_dropdown/*.css',

            'cyllo_studio/static/src/js/navbar/custom_selection/*.js',
            'cyllo_studio/static/src/js/navbar/custom_selection/*.xml',
            'cyllo_studio/static/src/js/navbar/custom_selection/*.css',


            'cyllo_studio/static/src/js/view_editor/components/record_autocomplete/multi_record_autocomplete.js',
            'cyllo_studio/static/src/js/view_editor/components/record_autocomplete/record_autocomplete.js',


            'cyllo_studio/static/src/js/view_editor/components/expression_editor_dialog/expression_editor_dialog.js',

            'cyllo_studio/static/src/js/view_editor/dialog/form_tree_dialog.js',
            'cyllo_studio/static/src/js/view_editor/dialog/form_tree_dialog.xml',
            'cyllo_studio/static/src/js/view_editor/dialog/form_tree_dialog.scss',
            'cyllo_studio/static/src/js/view_editor/dialog/calendar_dialog.js',
            'cyllo_studio/static/src/js/view_editor/dialog/calendar_dialog.scss',
            'cyllo_studio/static/src/js/view_editor/dialog/calendar_dialog.xml',

            'cyllo_studio/static/src/js/view_editor/fields/field.css',
            'cyllo_studio/static/src/js/view_editor/fields/field.js',
            'cyllo_studio/static/src/js/view_editor/fields/field.xml',
            'cyllo_studio/static/src/js/view_editor/dropdown/multi_select_dropdown/multi_select_dropdown.js',
            'cyllo_studio/static/src/js/view_editor/dropdown/multi_select_dropdown/multi_select_dropdown.xml',
            'cyllo_studio/static/src/js/view_editor/dropdown/icon_picker/icon_picker.js',
            'cyllo_studio/static/src/js/view_editor/dropdown/icon_picker/icon_picker.xml',
            'cyllo_studio/static/src/js/view_editor/dropdown/icon_picker/icon_picker.scss',
            'cyllo_studio/static/src/js/view_editor/dropdown/multi_record_selector/*.js',
            'cyllo_studio/static/src/js/view_editor/dropdown/multi_record_selector/*.xml',
            'cyllo_studio/static/src/js/view_editor/components/selection_field_widget_values/*.js',
            'cyllo_studio/static/src/js/view_editor/components/selection_field_widget_values/*.xml',
            'cyllo_studio/static/src/js/view_editor/dropdown/record_selector/*.js',
            'cyllo_studio/static/src/js/view_editor/dropdown/record_selector/*.xml',

            'cyllo_studio/static/src/js/new_app/*.js',
            'cyllo_studio/static/src/js/new_app/*.xml',
            'cyllo_studio/static/src/js/new_app/*.scss',

            'cyllo_studio/static/src/js/control_panel/control_panel.js',
            'cyllo_studio/static/src/js/control_panel/control_panel.xml',
            'cyllo_studio/static/src/js/control_panel/cog_menu_list.xml',
            'cyllo_studio/static/src/js/control_panel/cog_menu_list.js',
            'cyllo_studio/static/src/js/control_panel/report_creation_dialog.js',
            'cyllo_studio/static/src/js/control_panel/report_creation_dialog.xml',

            'cyllo_studio/static/src/js/view_editor/widget.js',

            'cyllo_studio/static/src/js/view_editor/aside_bar/aside_bar.css',
            'cyllo_studio/static/src/js/view_editor/aside_bar/aside_bar.js',
            'cyllo_studio/static/src/js/view_editor/aside_bar/aside_bar.xml',

            'cyllo_studio/static/src/js/view_editor/aside_bar/properties/field_properties/*.js',
            'cyllo_studio/static/src/js/view_editor/aside_bar/properties/field_properties/*.xml',
            'cyllo_studio/static/src/js/view_editor/aside_bar/properties/field_properties/field_properties.css',

            'cyllo_studio/static/src/js/view_editor/aside_bar/properties/existing_field_properties/*.js',
            'cyllo_studio/static/src/js/view_editor/aside_bar/properties/existing_field_properties/*.xml',

            'cyllo_studio/static/src/js/view_editor/aside_bar/properties/button_properties/*.js',
            'cyllo_studio/static/src/js/view_editor/aside_bar/properties/button_properties/*.xml',
            'cyllo_studio/static/src/js/view_editor/aside_bar/properties/button_properties/*.scss',

            'cyllo_studio/static/src/js/view_editor/aside_bar/properties/smart_button/*.js',
            'cyllo_studio/static/src/js/view_editor/aside_bar/properties/smart_button/*.xml',
            'cyllo_studio/static/src/js/view_editor/aside_bar/properties/smart_button/*.scss',

            'cyllo_studio/static/src/js/view_editor/dropdown/*.js',
            'cyllo_studio/static/src/js/view_editor/dropdown/*.xml',
            'cyllo_studio/static/src/js/view_editor/dropdown/*.scss',

            'cyllo_studio/static/src/js/view_editor/search/search_arch_parser.js',
            'cyllo_studio/static/src/js/view_editor/search/search_model.js',

            'cyllo_studio/static/src/js/views/**/*.scss',

            'cyllo_studio/static/src/js/view_editor/aside_bar/overall_view/overall_view.js',
            'cyllo_studio/static/src/js/view_editor/aside_bar/overall_view/overall_view.xml',
            'cyllo_studio/static/src/js/view_editor/aside_bar/overall_view/overall_view.css',
            'cyllo_studio/static/src/js/view_editor/aside_bar/overall_view/form_overall.css',
            'cyllo_studio/static/src/js/view_editor/aside_bar/dialog/*.js',
            'cyllo_studio/static/src/js/view_editor/aside_bar/dialog/*.xml',
            'cyllo_studio/static/src/js/view_editor/aside_bar/dialog/*.css',
            'cyllo_studio/static/src/js/views/cyllo_list/*.js',
            'cyllo_studio/static/src/js/views/cyllo_list/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_list/*.scss',

            'cyllo_studio/static/src/js/views/cyllo_search/*.js',
            'cyllo_studio/static/src/js/views/cyllo_search/*.xml',

            'cyllo_studio/static/src/js/views/cyllo_search/dialog/*.js',
            'cyllo_studio/static/src/js/views/cyllo_search/dialog/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_search/dialog/search_field_dialog.scss',
            'cyllo_studio/static/src/js/views/cyllo_search/dialog/search_panel_value_dialog.scss',
            'cyllo_studio/static/src/js/views/cyllo_search/dialog/search_panel_dialog.scss',

            'cyllo_studio/static/src/js/views/cyllo_form/button_box/*.js',
            'cyllo_studio/static/src/js/views/cyllo_form/button_box/*.xml',

            'cyllo_studio/static/src/js/views/cyllo_form/view_compiler.js',
            'cyllo_studio/static/src/js/views/cyllo_form/*.js',
            'cyllo_studio/static/src/js/views/cyllo_form/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_form/cyllo_form_controller.scss',
            'cyllo_studio/static/src/js/views/cyllo_form/status_bar/*.js',
            'cyllo_studio/static/src/js/views/cyllo_form/status_bar/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_form/status_bar/*.scss',
            'cyllo_studio/static/src/js/views/cyllo_form/chatter/*.js',
            'cyllo_studio/static/src/js/views/cyllo_form/chatter/chatter.scss',
            'cyllo_studio/static/src/js/views/cyllo_form/chatter/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_form/form_group/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_form/form_group/*.js',
            'cyllo_studio/static/src/js/views/cyllo_form/form_group/*.css',
            'cyllo_studio/static/src/js/views/cyllo_form/notebook/*.js',
            'cyllo_studio/static/src/js/views/cyllo_form/notebook/*.xml',
            '/cyllo_studio/static/src/js/views/cyllo_form/notebook/notebook.css',
            'cyllo_studio/static/src/js/views/cyllo_form/form_label/*.js',
            'cyllo_studio/static/src/js/views/cyllo_form/form_label/*.css',
            'cyllo_studio/static/src/js/views/cyllo_form/page/*.js',
            'cyllo_studio/static/src/js/views/cyllo_form/page/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_form/page/*.scss',
            'cyllo_studio/static/src/js/views/cyllo_form/avatar_dailog/*.js',
            'cyllo_studio/static/src/js/views/cyllo_form/avatar_dailog/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_form/avatar_dailog/*.scss',
            'cyllo_studio/static/src/js/views/cyllo_form/avatar/*.js',
            'cyllo_studio/static/src/js/views/cyllo_form/avatar/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_form/form_label/*.js',
            'cyllo_studio/static/src/js/views/cyllo_form/form_label/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_form/form_label/*.css',

            'cyllo_studio/static/src/js/button/*.xml',
            'cyllo_studio/static/src/js/button/*.js',
            'cyllo_studio/static/src/js/views/cyllo_pivot/*.xml',

            'cyllo_studio/static/src/js/views/cyllo_pivot/*.js',
            'cyllo_studio/static/src/js/views/cyllo_pivot/*.scss',

            'cyllo_studio/static/src/js/view_editor/kanban/ribbon_properties.js',
            'cyllo_studio/static/src/js/view_editor/kanban/ribbon_properties.xml',
            'cyllo_studio/static/src/js/view_editor/kanban/ribbon_properties.scss',
            'cyllo_studio/static/src/js/view_editor/kanban/progressbar_dialog.xml',
            'cyllo_studio/static/src/js/view_editor/kanban/progressbar_dialog.js',
            'cyllo_studio/static/src/js/view_editor/kanban/progressbar_dialog.scss',
            'cyllo_studio/static/src/js/view_editor/kanban/text_properties.js',
            'cyllo_studio/static/src/js/view_editor/kanban/text_properties.xml',
            'cyllo_studio/static/src/js/view_editor/kanban/text_properties.scss',
            'cyllo_studio/static/src/js/views/cyllo_kanban/*.js',
            'cyllo_studio/static/src/js/views/cyllo_kanban/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_kanban/*.scss',
            'cyllo_studio/static/src/js/view_editor/aside_bar/properties/field_properties/kanban_field_details.js',
            'cyllo_studio/static/src/js/view_editor/aside_bar/properties/field_properties/kanban_field_details.xml',
            'cyllo_studio/static/src/js/views/cyllo_kanban/kanban_components.js',
            'cyllo_studio/static/src/js/views/cyllo_kanban/kanban_components.xml',
            'cyllo_studio/static/src/js/views/cyllo_kanban/kanban_component.scss',
            'cyllo_studio/static/src/js/views/cyllo_kanban/kanban _field_dialog.js',
            'cyllo_studio/static/src/js/views/cyllo_kanban/kanban _field_dialog.xml',
            'cyllo_studio/static/src/js/views/cyllo_kanban/kanban_field_dialog.scss',
            'cyllo_studio/static/src/js/view_editor/kanban/ribbon_dialog.js',
            'cyllo_studio/static/src/js/view_editor/kanban/ribbon_dialog.xml',
            'cyllo_studio/static/src/js/view_editor/kanban/ribbon_dialog.scss',
            'cyllo_studio/static/src/js/view_editor/kanban/div_properties.js',
            'cyllo_studio/static/src/js/view_editor/kanban/div_properties.scss',
            'cyllo_studio/static/src/js/view_editor/kanban/div_properties.xml',


            'cyllo_studio/static/src/js/views/cyllo_calendar/*.js',
            'cyllo_studio/static/src/js/views/cyllo_calendar/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_calendar/*.scss',
            'cyllo_studio/static/src/js/views/cyllo_calendar/calendar_field_node_dialog/calendar_field_nodes_dialog.js',
            'cyllo_studio/static/src/js/views/cyllo_calendar/calendar_field_node_dialog/calendar_field_nodes_dialog.xml',
            'cyllo_studio/static/src/js/views/cyllo_calendar/calendar_dialog/*.js',
            'cyllo_studio/static/src/js/views/cyllo_calendar/calendar_dialog/*.xml',

            'cyllo_studio/static/src/js/views/cyllo_graph/*.js',
            'cyllo_studio/static/src/js/views/cyllo_graph/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_graph/*.scss',
            'cyllo_studio/static/src/js/views/cyllo_graph/cyllo_graph_controller.js',
            'cyllo_studio/static/src/js/views/cyllo_graph/cyllo_graph_controller.xml',

            'cyllo_studio/static/src/js/views/cyllo_activity/cyllo_activity_view.js',
            'cyllo_studio/static/src/js/views/cyllo_activity/*.js',
            'cyllo_studio/static/src/js/views/cyllo_activity/*.xml',
            'cyllo_studio/static/src/js/views/cyllo_activity/*.scss',
            'cyllo_studio/static/src/js/views/cyllo_activity/cyllo_activity_renderer.js',
            'cyllo_studio/static/src/js/views/cyllo_activity/cyllo_activity_renderer.xml',

            'cyllo_studio/static/src/js/preview/*.js',
            'cyllo_studio/static/src/js/preview/*.xml',

            # 'cyllo_studio/static/src/js/control_panel/UndoRedo/UndoRedo.js',
            # 'cyllo_studio/static/src/js/control_panel/UndoRedo/UndoRedo.xml',
            'cyllo_studio/static/src/js/utils/undo_redo_utils.js',
            'cyllo_studio/static/src/js/utils/display_notification.js',
            'cyllo_studio/static/src/js/utils/client_action.js',

            'cyllo_studio/static/src/js/custom_report/studio_report_qr.js',
            'cyllo_studio/static/src/js/custom_report/studio_report_box.js',
            'cyllo_studio/static/src/js/custom_report/studio_report_sign.js',
            'cyllo_studio/static/src/js/custom_report/studio_report.js',
            'cyllo_studio/static/src/js/custom_report/studio_report_setup_sidebar.xml',
            'cyllo_studio/static/src/js/custom_report/studio_report_qr_wizard.xml',
            'cyllo_studio/static/src/js/custom_report/studio_report.xml',
            'cyllo_studio/static/src/js/custom_report/studio_report.css'
        ]
    },
    'license': 'LGPL-3',
    'icon': '/cyllo_studio/static/description/icon.svg',
    'installable': True,
    'auto_install': False,
    'application': True,
}
