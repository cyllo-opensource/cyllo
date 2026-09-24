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

import re

from odoo import _, exceptions, fields, models

from .workflow_report_attachment import DATE_PRESETS, TARGET_MOVE_SELECTION


class NodeStruct(models.Model):
    _name = 'node.struct'

    name = fields.Char()
    work_auto_id = fields.Many2one('work.auto', ondelete='cascade')
    reused_work_auto_id = fields.Many2one('work.auto', string="Reusable Automation", ondelete='set null')
    reused_variable = fields.Json("Reusable Record Variable")
    code = fields.Text("Code")
    label = fields.Char()
    type = fields.Selection(selection=[
        ("trigger", "Trigger"),
        ("model", "Model"),
        ("node", "Node"),
        ("action", "Action"),
        ("action_to_do", "Action to do")
    ])
    trigger_type = fields.Char("Trigger Type")
    ttype = fields.Char("UI Trigger Label")
    model_id = fields.Many2one('ir.model')
    used_variables = fields.Json("Used Variables")
    condition_tree_value = fields.Json("condition_tree_value")
    else_setup_code = fields.Text(string="Else Setup Code")

    # warning block fields
    warning = fields.Selection(
        string="Warning",
        selection=[('UserError', 'User Error'),
                   ('AccessError', 'Access Error'),
                   ('AccessDenied', 'Access Denied'),
                   ('ValidationError', 'Validation Error'),
                   ('MissingError', 'Missing Error'),
        ])
    warning_text = fields.Char(string="Warning Text")
    model_name = fields.Char("Model Name", related="model_id.model")
    warning_type = fields.Char(string="Warning Type", default="error")
    notification_type = fields.Char(string="Notification Type")
    notification_title = fields.Char(string="Notification Title")
    notification_sticky = fields.Boolean(string="Sticky Notification", default=False)

    #search block fields
    search_domain = fields.Char()
    search_limit = fields.Integer()
    search_order = fields.Selection(
        selection=[('asc', 'ASC'), ('desc', 'DESC')])
    search_order_field = fields.Char()
    search_domain_tree = fields.Json("Tree")
    search_variable = fields.Json("Variable")

    # create block fields
    create_name = fields.Char()
    create_model_field_value = fields.Char(default="[]")
    create_req_fields_values = fields.Json("createFields")
    create_tree_fields_values = fields.Json("createTreeFields")
    create_required_field = fields.Json("createRequiredField")

    #Write block fields
    write_field_value = fields.Char(default="[]")
    write_selected_record = fields.Json("Record")

    #Function call block fields
    function_name = fields.Json("Function Name")
    function_type = fields.Char(string="Function Type", default="server_action")
    function_record = fields.Json()
    function_args = fields.Json("Function Arguments", default={})

    #Variables block fields
    variable_name = fields.Char("Variable Name")
    variable_type = fields.Selection(
        string="Variable Type",
        selection=[
            ('string', 'String'),
            ('number', 'Number'),
            ('date', 'Date'),
            ('datetime', 'DateTime'),
            ('boolean', 'Boolean'),
            ('dynamic', 'Dynamic Values'),
        ])
    variable_value = fields.Char(string="Variable Value")
    code_return_type = fields.Selection(
        string="Code Return Type",
        selection=[
            ('string', 'String'),
            ('number', 'Number'),
            ('date', 'Date'),
            ('datetime', 'DateTime'),
            ('boolean', 'Boolean'),
            ('record', 'Record'),
            ('recordset', 'RecordSet'),
        ])

    # loop block fields
    loop_source_type = fields.Selection(
        selection=[('field', 'Record Field'), ('variable', 'Variable')],
        string="Source Type", default='field')
    loop_collection = fields.Char(string="Collection")
    loop_variable_name = fields.Char(string="Loop Variable Name")

    #codeNode block fields
    code_code = fields.Char(string="Code")

    # mailNode block fields
    mailCustomData = fields.Json(string="Mail Custom Data")
    mail_record = fields.Json(string="MailRecord")
    mail_template = fields.Json(string="MailTemplate")
    mail_isTemplate = fields.Json(string="MailIsTemplate")
    mail_from = fields.Json(string="MailFrom")
    mail_to = fields.Json(string="MailTo")
    mail_cc = fields.Json(string="MailCc")
    mail_bcc = fields.Json(string="MailBcc")
    mail_subject = fields.Json(string="MailSubject")
    mail_body = fields.Json(string="MailBody")
    # Attachment fields for the Mail node's free-form/custom mode only.
    # Template mode is untouched: a mail.template already attaches its own
    # configured report, if any, when it sends.
    mail_attachment_mode = fields.Selection(
        [
            ('none', 'No Attachment'),
            ('static', 'Static File(s)'),
            ('auto', 'Auto-generate (Accounting Report)'),
        ],
        string="Mail Attachment Mode",
        default='none',
    )
    mail_static_attachment_ids = fields.Many2many(
        'ir.attachment',
        'node_struct_mail_attachment_rel',
        'node_struct_id',
        'attachment_id',
        string="Mail Static Attachments",
    )
    mail_auto_report_id = fields.Many2one(
        'ir.actions.report',
        string="Mail Auto Report",
        ondelete='set null',
    )
    mail_auto_report_date_preset = fields.Selection(
        DATE_PRESETS,
        string="Mail Report Date Range",
        default='last_month',
    )
    mail_auto_report_start_date = fields.Date(string="Mail Report Start Date")
    mail_auto_report_end_date = fields.Date(string="Mail Report End Date")
    mail_auto_report_journal_ids = fields.Json(string="Mail Report Journals")
    mail_auto_report_analytic_ids = fields.Json(string="Mail Report Analytic Accounts")
    mail_auto_report_target_move = fields.Selection(
        TARGET_MOVE_SELECTION,
        string="Mail Report Target Move",
        default='posted',
    )

    # smsNode block fields
    sms_record = fields.Json(string="sms record")
    sms_template = fields.Json(string="sms template")
    sms_partner_ids = fields.Json(string="Recipients")
    recipients = fields.Json(string='reciep')
    sms_isTemplate = fields.Boolean(string="SMSIsTemplate")
    sms_message = fields.Char(string="smsMessage")

    # WhatsApp node block fields
    wa_record = fields.Json(string="WA Record Variable")
    wa_is_template = fields.Boolean(string="Use WA Template", default=False)
    wa_template = fields.Json(string="WA Template")
    wa_partner_path = fields.Json(string="WA Partner Path")
    wa_partner_source = fields.Selection(
        [('customer', 'Customer'), ('other', 'Other')],
        string="WA Partner Source",
        default='customer',
    )
    wa_other_partner = fields.Json(string="WA Other Partner")
    wa_free_message = fields.Char(string="WA Free-form Message")
    wa_attachment_mode = fields.Selection(
        [
            ('none', 'No Attachment'),
            ('static', 'Static File(s)'),
            ('auto', 'Auto-generate from Record'),
        ],
        string="WA Attachment Mode",
        default='none',
    )
    wa_static_attachment_ids = fields.Many2many(
        'ir.attachment',
        'node_struct_wa_attachment_rel',
        'node_struct_id',
        'attachment_id',
        string="WA Static Attachments",
    )
    wa_auto_report_id = fields.Many2one(
        'ir.actions.report',
        string="WA Auto Report",
        ondelete='set null',
    )
    # Filters for reports that need more than a record id to render (e.g. the
    # cyllo_accounting financial reports: General Ledger, Trial Balance, ...).
    # Stored generically (Json for journals/analytics) rather than as real
    # Many2many fields to 'account.journal'/'account.analytic.account', since
    # this module has no hard dependency on the accounting module — the same
    # convention already used for wa_template/wa_other_partner above.
    wa_auto_report_date_preset = fields.Selection(
        DATE_PRESETS,
        string="WA Report Date Range",
        default='last_month',
    )
    wa_auto_report_start_date = fields.Date(string="WA Report Start Date")
    wa_auto_report_end_date = fields.Date(string="WA Report End Date")
    wa_auto_report_journal_ids = fields.Json(string="WA Report Journals")
    wa_auto_report_analytic_ids = fields.Json(string="WA Report Analytic Accounts")
    wa_auto_report_target_move = fields.Selection(
        TARGET_MOVE_SELECTION,
        string="WA Report Target Move",
        default='posted',
    )

    # Window node block fields
    window_action_id = fields.Many2one(
        'ir.actions.act_window',
        string="Window Action",
        ondelete='set null',
        help="The act_window action to open when this node executes.",
    )
    window_view_type = fields.Selection(
        selection=[
            ('list', 'List'),
            ('form', 'Form'),
            ('kanban', 'Kanban'),
            ('calendar', 'Calendar'),
            ('pivot', 'Pivot'),
            ('graph', 'Graph'),
            ('activity', 'Activity'),
        ],
        string="View Type",
        default='list',
    )
    window_target = fields.Selection(
        selection=[
            ('current', 'Current'),
            ('new', 'New Tab / Dialog'),
            ('fullscreen', 'Fullscreen'),
            ('inline', 'Inline'),
        ],
        string="Target",
        default='current',
    )
    window_domain = fields.Char(
        string="Domain Filter",
        help="Optional domain expression to restrict records, e.g. [('state','=','done')]",
    )
    window_domain_tree = fields.Json(
        string="Window Domain Tree",
        help="Internal tree representation of window_domain for the visual domain editor.",
    )
    window_context = fields.Char(
        string="Context",
        help="Optional context dict to pass to the window action, e.g. {'default_partner_id': 1}",
    )

    # Webhook block fields
    webhook_method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE')
    ], string="Webhook Method", default='POST')
    webhook_url = fields.Char(string="Webhook URL")
    webhook_headers = fields.Char(string="Headers (JSON)", default='{"Content-Type": "application/json"}')
    webhook_payload = fields.Text(string="Payload (JSON)")
    webhook_actions = fields.Json(string="Webhook Response Actions")
    webhook_secret_token = fields.Char(
        string="Webhook Secret Token",
        copy=False,
        help="Auto-generated secret token used to build the inbound Secret URL. "
             "Regenerating it immediately invalidates the old URL.",
    )

    # FollowersNode block fields
    isRemoveFollower = fields.Json()
    followers = fields.Json()
    follower_record = fields.Json()

    # DuplicateNode block fields
    duplicate_record = fields.Json(string="Duplicate Record Variable")
    duplicate_field_overrides = fields.Char(
        string="Field Overrides",
        default="[]",
        help="JSON list of {path, value, selectionType} to override on the copy"
    )
    duplicate_result_variable = fields.Char(
        string="Result Variable Name",
        help="Optional variable name to store the duplicated record(s) for use in downstream nodes"
    )

    # TryCatch block fields
    try_catch_error_variable = fields.Char(
        string="Error Variable Name",
        default="error",
        help="Python variable name that will hold the caught exception object.",
    )
    try_catch_error_types = fields.Char(
        string="Exception Types",
        default="Exception",
        help="Comma-separated exception class names to catch, e.g. 'UserError, ValidationError'.",
    )

    # ActivityNode block fields
    activity_record = fields.Json()
    activity_summary = fields.Char()
    activity_user = fields.Json()
    activity_deadline = fields.Json()
    activity_type = fields.Json()
    activity_is_google_meet = fields.Boolean(
        string="Create as Google Meet",
        default=False,
        help="When enabled and cyllo_google_meet is installed, a Google Meet "
             "calendar event is created automatically.",
    )
    activity_meet_offset_hours = fields.Float(
        string="Schedule After (hours)",
        default=1.0,
        help="Number of hours after the workflow trigger to schedule the meeting start.",
    )
    activity_meet_duration_hours = fields.Float(
        string="Meeting Duration (hours)",
        default=1.0,
        help="Duration of the meeting in hours.",
    )
    activity_meet_summary = fields.Char(
        string="Meeting Name",
        help="Meeting title for the calendar event. Defaults to the activity summary.",
    )
    activity_also_schedule_activity = fields.Boolean(
        string="Also Schedule Activity Reminder",
        default=True,
        help="When enabled, the workflow also creates the regular chatter activity reminder.",
    )
    activity_is_zoom_meet = fields.Boolean(
        string="Create as Zoom Meet",
        default=False,
        help="When enabled and cyllo_zoom is installed, a Zoom meeting calendar "
             "event is created automatically.",
    )
    activity_zoom_offset_hours = fields.Float(
        string="Schedule After (hours)",
        default=1.0,
        help="Number of hours after the workflow trigger to schedule the meeting start.",
    )
    activity_zoom_duration_hours = fields.Float(
        string="Meeting Duration (hours)",
        default=1.0,
        help="Duration of the Zoom meeting in hours.",
    )
    activity_zoom_summary = fields.Char(
        string="Meeting Name",
        help="Meeting title for the Zoom calendar event. Defaults to the activity summary.",
    )
    activity_also_schedule_activity_zoom = fields.Boolean(
        string="Also Schedule Activity Reminder",
        default=True,
        help="When enabled, the workflow also creates the regular chatter activity reminder.",
    )

    @staticmethod
    def _extract_attachment_ids(raw_attachments):
        """Normalize a list of static-attachment entries coming from the
        frontend (dicts, [id, name] pairs, or plain ids) into a flat list of
        ir.attachment ids."""
        attachment_ids = []
        for item in (raw_attachments or []):
            if isinstance(item, dict):
                attachment_id = item.get('id')
            elif isinstance(item, (list, tuple)):
                attachment_id = item[0] if item else False
            else:
                attachment_id = item
            if attachment_id:
                attachment_ids.append(attachment_id)
        return attachment_ids

    def save_data(self, data):
        """
        Create a new node.struct record with `data`, or update it if the record already exists.
        Returns the id of the saved or updated record.
        """
        struct_node_id = self or False
        if 'wa_static_attachment_ids' in data:
            data['wa_static_attachment_ids'] = [
                (6, 0, self._extract_attachment_ids(data.get('wa_static_attachment_ids')))
            ]

        if 'mail_static_attachment_ids' in data:
            data['mail_static_attachment_ids'] = [
                (6, 0, self._extract_attachment_ids(data.get('mail_static_attachment_ids')))
            ]

        if 'wa_auto_report_id' in data and isinstance(data['wa_auto_report_id'], dict):
            data['wa_auto_report_id'] = data['wa_auto_report_id'].get('id') or False

        if 'mail_auto_report_id' in data and isinstance(data['mail_auto_report_id'], dict):
            data['mail_auto_report_id'] = data['mail_auto_report_id'].get('id') or False

        if not self:
            struct_node_id = self.create(data)
        else:
            self.write(data)
        return struct_node_id.id

    def create_editable_reuse_copy(self):
        """
            Duplicate the node's reusable automation so it can be edited without affecting the original.
            Links the node to the copy and returns its id, name, label, and updated code.
            """
        self.ensure_one()
        if not self.reused_work_auto_id:
            raise exceptions.ValidationError(
                _("Please select a reusable automation before editing it.")
            )

        copied_automation = self.reused_work_auto_id.copy()
        copied_automation.write({
            'is_editable_copy': True,
        })

        updated_code = self.code or ''
        if updated_code:
            updated_code = re.sub(
                r'env\["work\.auto"\]\.browse\(\d+\)',
                f'env["work.auto"].browse({copied_automation.id})',
                updated_code,
                count=1,
            )

        self.write({
            'reused_work_auto_id': copied_automation.id,
            'label': copied_automation.name,
            'code': updated_code,
        })

        return {
            'id': copied_automation.id,
            'name': copied_automation.name,
            'label': copied_automation.name,
            'code': updated_code,
        }
