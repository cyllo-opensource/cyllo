/** @odoo-module */

export const conditionFields = [{ name: 'model_id', type: "many2One" }, { name: "condition_tree_value", type: "json" }, { name: 'label', type: "char" }, { name: 'else_setup_code', type: "char" }];

export const warningFields = [{ name: 'model_id', type: "many2One" }, { name: 'warning', type: 'selection' }, { name: 'warning_text', type: 'text' }, { name: 'used_variables', type: 'json' }, { name: 'label', type: "char" }, { name: 'warning_type', type: "char" }, { name: 'notification_type', type: "char" }, { name: 'notification_title', type: "char" }, { name: 'notification_sticky', type: "boolean" }];

export const searchFields = [{ name: 'model_id', type: "many2One" }, { name: 'search_domain', type: 'char' }, { name: 'search_limit', type: 'integer' }, { name: 'search_order', type: "selection" }, { name: 'search_order_field', type: "char" }, { name: 'search_domain_tree', type: "json" }, { name: 'search_variable', type: "json" }, { name: 'used_variables', type: 'json' }, { name: 'label', type: "char" }];

export const createFields = [{ name: 'model_id', type: 'many2One' }, { name: 'create_name', type: 'char' }, { name: 'create_model_field_value', type: 'char' }, { name: 'create_req_fields_values', type: 'json' }, { name: 'create_tree_fields_values', type: 'json' }, { name: 'create_required_field', type: 'json' }, { name: 'search_variable', type: "json" }, { name: 'used_variables', type: 'json' }, { name: 'label', type: "char" }]

export const writeFields = [{ name: 'write_field_value', type: 'char' }, { name: 'write_selected_record', type: 'json' }, { name: 'used_variables', type: 'json' }, { name: 'label', type: "char" }]

export const functionCallFields = [{ name: 'model_id', type: "many2One" }, { name: 'function_name', type: 'json' }, { name: 'function_args', type: 'json' }, { name: 'used_variables', type: 'json' }, { name: 'label', type: "char" }, { name: 'function_record', type: "json" }, { name: 'function_type', type: "char" }]

export const variableFields = [{ name: 'variable_name', type: 'char' }, { name: 'variable_type', type: 'selection' }, { name: 'variable_value', type: 'char' }, { name: 'used_variables', type: 'json' }, { name: 'label', type: "char" }, { name: 'code_return_type', type: 'selection' }]

export const codeFields = [{ name: 'model_id', type: "many2One" }, { name: 'code_code', type: 'char' }, { name: 'used_variables', type: 'json' }, { name: 'label', type: "char" }]

export const mailFields = [{ name: 'model_id', type: "many2One" }, { name: 'mail_record', type: 'json' }, { name: 'mail_from', type: 'char' }, { name: 'mail_to', type: 'json' }, { name: 'mail_cc', type: 'json' }, { name: 'mail_bcc', type: 'json' }, { name: 'mail_subject', type: 'char' }, { name: 'mail_body', type: 'char' }, { name: 'mail_template', type: 'json' }, { name: 'mail_isTemplate', type: 'json' }, { name: 'label', type: "char" }, { name: 'mail_attachment_mode', type: 'selection' }, { name: 'mail_static_attachment_ids', type: 'many2many' }, { name: 'mail_auto_report_id', type: 'many2One' }, { name: 'mail_auto_report_date_preset', type: 'selection' }, { name: 'mail_auto_report_start_date', type: 'date' }, { name: 'mail_auto_report_end_date', type: 'date' }, { name: 'mail_auto_report_journal_ids', type: 'json' }, { name: 'mail_auto_report_analytic_ids', type: 'json' }, { name: 'mail_auto_report_target_move', type: 'selection' }]

export const smsFields = [{ name: 'model_id', type: "many2One" }, { name: 'sms_record', type: 'json' }, { name: 'sms_template', type: 'json' }, { name: 'sms_partner_ids', type: 'json' }, { name: 'sms_isTemplate', type: 'boolean' }, { name: 'sms_message', type: 'char' }, { name: 'label', type: "char" }]

export const whatsappFields = [{ name: 'model_id', type: 'many2One' }, { name: 'wa_record', type: 'json' }, { name: 'wa_is_template', type: 'boolean' }, { name: 'wa_template', type: 'json' }, { name: 'wa_partner_path', type: 'json' }, { name: 'wa_partner_source', type: 'selection' }, { name: 'wa_other_partner', type: 'json' }, { name: 'wa_free_message', type: 'char' }, { name: 'wa_attachment_mode', type: 'selection' }, { name: 'wa_static_attachment_ids', type: 'many2many' }, { name: 'wa_auto_report_id', type: 'many2One' }, { name: 'wa_auto_report_date_preset', type: 'selection' }, { name: 'wa_auto_report_start_date', type: 'date' }, { name: 'wa_auto_report_end_date', type: 'date' }, { name: 'wa_auto_report_journal_ids', type: 'json' }, { name: 'wa_auto_report_analytic_ids', type: 'json' }, { name: 'wa_auto_report_target_move', type: 'selection' }, { name: 'label', type: 'char' }, { name: 'used_variables', type: 'json' }]

export const FollowerFields = [{ name: 'model_id', type: "many2One" }, { name: 'followers', type: "json" }, { name: 'follower_record', type: 'char' }, { name: 'label', type: "char" }, { name: 'label', type: "char" }, { name: 'isRemoveFollower', type: "json" }]

export const ActivityFields = [
    { name: 'model_id', type: "many2One" },
    { name: 'activity_summary', type: "char" },
    { name: 'activity_user', type: "json" },
    { name: 'activity_deadline', type: "json" },
    { name: 'activity_type', type: "json" },
    { name: 'activity_record', type: "json" },
    { name: 'label', type: "char" },
    // Google Meet
    { name: 'activity_is_google_meet', type: "boolean" },
    { name: 'activity_meet_offset_hours', type: "float" },
    { name: 'activity_meet_duration_hours', type: "float" },
    { name: 'activity_meet_summary', type: "char" },
    { name: 'activity_also_schedule_activity', type: "boolean" },
    // Zoom Meet
    { name: 'activity_is_zoom_meet', type: "boolean" },
    { name: 'activity_zoom_offset_hours', type: "float" },
    { name: 'activity_zoom_duration_hours', type: "float" },
    { name: 'activity_zoom_summary', type: "char" },
    { name: 'activity_also_schedule_activity_zoom', type: "boolean" },
]

export const loopFields = [
    { name: 'loop_source_type', type: 'selection' },
    { name: 'loop_collection', type: 'char' },
    { name: 'loop_variable_name', type: 'char' },
    { name: 'used_variables', type: 'json' },
    { name: 'label', type: 'char' },
];

export const MappedFields = [];
export const AssignmentFields = [];

export const reusableAutomationFields = [
    { name: 'reused_work_auto_id', type: 'many2One' },
    { name: 'reused_variable', type: 'json' },
    { name: 'label', type: 'char' },
];

export const windowFields = [
    { name: 'label', type: 'char' },
    { name: 'window_action_id', type: 'many2One' },
    { name: 'window_view_type', type: 'selection' },
    { name: 'window_target', type: 'selection' },
    { name: 'window_domain', type: 'char' },
    { name: 'window_domain_tree', type: 'json' },
    { name: 'window_context', type: 'char' },
];

export const duplicateFields = [
    { name: 'model_id', type: 'many2One' },
    { name: 'label', type: 'char' },
    { name: 'duplicate_record', type: 'char' },
    { name: 'duplicate_field_overrides', type: 'char' },
    { name: 'duplicate_result_variable', type: 'char' },
    { name: 'used_variables', type: 'json' },
];

export const tryCatchFields = [
    { name: 'label', type: 'char' },
    { name: 'try_catch_error_variable', type: 'char' },
    { name: 'try_catch_error_types', type: 'char' },
];

export const webhookFields = [
    { name: 'label', type: 'char' },
    { name: 'webhook_method', type: 'selection' },
    { name: 'webhook_url', type: 'char' },
    { name: 'webhook_headers', type: 'char' },
    { name: 'webhook_payload', type: 'text' },
    { name: 'webhook_actions', type: 'json' },
];
