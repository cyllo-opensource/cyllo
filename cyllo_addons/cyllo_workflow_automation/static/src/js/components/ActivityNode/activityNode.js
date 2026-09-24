/** @odoo-module */
import { ConfigurationBase } from "../configurationBase/configurationBase";
import { CustomDropdown } from "../Assists/dropdown/CustomDropdown";
import { getValueEditorInfo } from "@web/core/tree_editor/tree_editor_value_editors";
import { VariableSelector } from "../Assists/variableSelector/variableSelector"
import { FieldTypeDropdown } from "../Assists/fieldTypeDropdown/fieldTypeDropDown";
import { RecordPathSelector } from "../Assists/recordPathSelector/recordPathSelector";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { jsonrpc } from "@web/core/network/rpc_service";
const { DateTime } = luxon;

export class ActivityNode extends ConfigurationBase {
    /**
     * ActivityNode class for handling configuration and logic related to activity nodes
     * in a workflow. It extends the ConfigurationBase class.
     */
    setup() {
        super.setup();
        this.googleMeetState = owl.useState({
            installed: false,
            configured: false,
            activityTypeCategory: null,
        });
        this.zoomMeetState = owl.useState({
            installed: false,
            configured: false,
        });
    }

    async fetchData() {
        await super.fetchData();
        this._ensureSelectionFieldShape('activity_user', '');
        this._ensureSelectionFieldShape('activity_deadline', false);
        await this._checkGoogleMeetInstalled();
        if (this.fieldState.activity_is_google_meet === null || this.fieldState.activity_is_google_meet === undefined) {
            this.fieldState.activity_is_google_meet = false;
        }
        if (this.fieldState.activity_meet_offset_hours === null || this.fieldState.activity_meet_offset_hours === undefined) {
            this.fieldState.activity_meet_offset_hours = 1.0;
        }
        if (this.fieldState.activity_meet_duration_hours === null || this.fieldState.activity_meet_duration_hours === undefined) {
            this.fieldState.activity_meet_duration_hours = 1.0;
        }
        if (this.fieldState.activity_also_schedule_activity === null || this.fieldState.activity_also_schedule_activity === undefined) {
            this.fieldState.activity_also_schedule_activity = true;
        }
        await this._checkZoomInstalled();
        if (this.fieldState.activity_is_zoom_meet === null || this.fieldState.activity_is_zoom_meet === undefined) {
            this.fieldState.activity_is_zoom_meet = false;
        }
        if (this.fieldState.activity_zoom_offset_hours === null || this.fieldState.activity_zoom_offset_hours === undefined) {
            this.fieldState.activity_zoom_offset_hours = 1.0;
        }
        if (this.fieldState.activity_zoom_duration_hours === null || this.fieldState.activity_zoom_duration_hours === undefined) {
            this.fieldState.activity_zoom_duration_hours = 1.0;
        }
        if (this.fieldState.activity_also_schedule_activity_zoom === null || this.fieldState.activity_also_schedule_activity_zoom === undefined) {
            this.fieldState.activity_also_schedule_activity_zoom = true;
        }
        await this._syncActivityTypeCategory();
    }

    async _checkGoogleMeetInstalled() {
        try {
            const result = await jsonrpc('/cyllo_workflow/check_google_meet_installed', {});
            this.googleMeetState.installed = !!result?.installed;
            this.googleMeetState.configured = !!result?.configured;
        } catch {
            this.googleMeetState.installed = false;
            this.googleMeetState.configured = false;
        }
    }

    async _checkZoomInstalled() {
        try {
            const result = await jsonrpc('/cyllo_workflow/check_zoom_installed', {});
            this.zoomMeetState.installed = !!result?.installed;
            this.zoomMeetState.configured = !!result?.configured;
        } catch {
            this.zoomMeetState.installed = false;
            this.zoomMeetState.configured = false;
        }
    }

    async _syncActivityTypeCategory() {
        const activityTypeId = this.fieldState.activity_type?.id;
        if (!activityTypeId) {
            this.googleMeetState.activityTypeCategory = null;
            this.fieldState.activity_is_google_meet = false;
            this.fieldState.activity_is_zoom_meet = false;
            return;
        }

        if (this.fieldState.activity_type?.category) {
            this.googleMeetState.activityTypeCategory = this.fieldState.activity_type.category;
            if (this.fieldState.activity_type.category !== 'meeting') {
                this.fieldState.activity_is_google_meet = false;
                this.fieldState.activity_is_zoom_meet = false;
            }
            return;
        }

        const [activityTypeData] = await this.orm.read(
            'mail.activity.type',
            [activityTypeId],
            ['category']
        );
        const category = activityTypeData?.category || null;
        this.googleMeetState.activityTypeCategory = category;
        this.fieldState.activity_type = {
            ...(this.fieldState.activity_type || {}),
            category,
        };
        if (category !== 'meeting') {
            this.fieldState.activity_is_google_meet = false;
            this.fieldState.activity_is_zoom_meet = false;
        }
    }

    get showGoogleMeetOptions() {
        return this.googleMeetState.installed && this.googleMeetState.activityTypeCategory === 'meeting';
    }

    get showZoomMeetOptions() {
        return this.zoomMeetState.installed && this.googleMeetState.activityTypeCategory === 'meeting';
    }

    get getLabel() {
        return this.fieldState.label || ""
    }

    setLabel(ev) {
        this.fieldState.label = ev
        const label = ev
        const nodeId = this.props.id
        this.env.bus.trigger("CHANGE-LABEL", { label, nodeId });
    }

    get getRecords() {
        let variables = []
        this.variables.forEach(variable => {
            ['record', 'recordset'].includes(variable.variable_type) && variable.modelId ? variables.push({
                value: variable.id,
                label: variable.variable_name
            }) : null
        })
        return variables
    }

    get getModel() {
        return this.fieldState.activity_record?.value || ""
    }

    updateObject(record) {
        this.fieldState.activity_record = this.getRecords.find((item) => item.value === record)
    }

    updateAssignee(value) {
        let mail_to = this.fieldState.activity_user || {}
        mail_to.value = value
        this.fieldState.activity_user = mail_to
    }
    /**
    * Retrieves component properties for specific fields like assignee or deadline.
    * @param {Object} info - Information object to extract properties from.
    * @param {String} field - The field type ('assignee' or 'deadline').
    * @returns {Object} - Extracted properties for the component.
    */

    getComponentProps(info, field) {
        const { value, update } = field === "assignee" ? {
            value: this.fieldState.activity_user?.value || false,
            update: (value) => this.updateAssignee(value)
        } : {
            value: this.getDeadline.value || false,
            update: (value) => this.updateDeadline(value)
        }
        return info.extractProps({ value, update })
    }

    /**
     * Retrieves variables for the given selection type and field type.
     * @param {String} selectionType - The selection type (e.g., 'variable', 'record').
     * @param {String} field - The field name ('assignee' or other).
     * @returns {Object} - Object containing variables and field information.
     */
    getVariablesField(selectionType, field) {
        let result;
        if (selectionType === 'variable') {
            result = {
                flVariables: field === "assignee" ? (this.props.variables || []).filter(variable => variable.variable_type === 'record' && variable.modelName === "res.users") :
                    (this.props.variables || []).filter(variable => variable.variable_type === 'date'),
                fieldInfo: field === "assignee" ? {
                    fieldDef: {
                        type: "many2one",
                        relation: "res.users",
                    }
                } : { fieldDef: { type: 'date' } }
            };
        } else if (selectionType === 'record') {
            result = {
                flVariables: (this.props.variables || []).filter(variable => variable.variable_type === "record"),
                fieldInfo: field === "assignee" ? {
                    resModel: this.modelState.model['model'],
                    fieldDef: {
                        type: 'many2one',
                        relation: 'res.users',
                    }
                } : { fieldDef: { type: 'date' } }
            };
        } else {
            result = {
                fieldInfo: {
                    fieldDef: field === "assignee" ? {
                        type: "many2one",
                        relation: "res.users",
                    } : { type: 'date' }
                }
            };
        }
        return result
    }

    /**
     * Retrieves editor information based on the field type and selection type.
     * @param {Object} field - The field object.
     * @param {String} type - The field type ('assignee' or other).
     * @returns {Object} - Editor information for rendering the field.
     */
    getValueEditorInfo(field, type) {
        const selectionType = field.selectionType ? field.selectionType : ''
        const operator = '='
        const { flVariables, fieldInfo } = this.getVariablesField(selectionType, type)
        let editorValue = getValueEditorInfo(fieldInfo.fieldDef, operator);
        if (selectionType === "variable") {
            return {
                component: VariableSelector,
                extractProps: ({ value, update }) => {
                    return {
                        value,
                        update,
                        allVariable: true,
                        variables: flVariables
                    }
                }
            }
        } else if (selectionType === "record") {
            return {
                component: RecordPathSelector,
                extractProps: ({ value, update }) => {
                    return {
                        value,
                        update,
                        variables: flVariables,
                        fieldInfo,
                    }
                }
            }
        }
        return editorValue
    }

    getDropdownLabel(selectionType) {
        const labels = {
            static: 'Fixed',
            variable: 'Variable',
            record: 'Record',
        };
        return labels[selectionType] || 'Fixed';
    }

    _ensureSelectionFieldShape(fieldName, defaultValue) {
        const currentValue = this.fieldState[fieldName];
        if (!currentValue || typeof currentValue !== 'object' || Array.isArray(currentValue)) {
            this.fieldState[fieldName] = {
                value: defaultValue,
                selectionType: 'static',
            };
            return this.fieldState[fieldName];
        }
        if (!Object.prototype.hasOwnProperty.call(currentValue, 'selectionType')) {
            currentValue.selectionType = 'static';
        }
        if (!Object.prototype.hasOwnProperty.call(currentValue, 'value')) {
            currentValue.value = defaultValue;
        }
        return currentValue;
    }

    toggleIncludeVariable(value, field) {
        if (field === 'user') {
            const activityUser = this._ensureSelectionFieldShape('activity_user', '');
            if (![value, undefined].includes(activityUser.selectionType)) {
                this.fieldState.activity_user = { value: '', selectionType: value }
            } else {
                activityUser.selectionType = value;
            }
        } else {
            const activityDeadline = this._ensureSelectionFieldShape('activity_deadline', false);
            if (![value, undefined].includes(activityDeadline.selectionType)) {
                this.fieldState.activity_deadline = { value: false, selectionType: value }
            } else {
                activityDeadline.selectionType = value;
            }
        }
    }

    get getDeadline() {
        return this._ensureSelectionFieldShape('activity_deadline', false)
    }

    updateDeadline(value) {
        this.fieldState.activity_deadline.value = value
    }

    async updateActivityType(ev) {
        this.fieldState.activity_type = ev[0];
        await this._syncActivityTypeCategory();
    }

    setSummary(value) {
        this.fieldState.activity_summary = value
    }

    toggleGoogleMeet(ev) {
        this.fieldState.activity_is_google_meet = !!ev.target.checked;
    }

    toggleAlsoScheduleActivity(ev) {
        this.fieldState.activity_also_schedule_activity = !!ev.target.checked;
    }

    updateOffsetHours(ev) {
        const value = parseFloat(ev.target.value);
        this.fieldState.activity_meet_offset_hours = Number.isNaN(value) ? 1.0 : Math.max(0, value);
    }

    updateDurationHours(ev) {
        const value = parseFloat(ev.target.value);
        this.fieldState.activity_meet_duration_hours = Number.isNaN(value) ? 1.0 : Math.max(0.25, value);
    }

    updateMeetSummary(ev) {
        this.fieldState.activity_meet_summary = ev.target.value;
    }

    toggleZoomMeet(ev) {
        this.fieldState.activity_is_zoom_meet = !!ev.target.checked;
    }

    toggleAlsoScheduleActivityZoom(ev) {
        this.fieldState.activity_also_schedule_activity_zoom = !!ev.target.checked;
    }

    updateZoomOffsetHours(ev) {
        const value = parseFloat(ev.target.value);
        this.fieldState.activity_zoom_offset_hours = Number.isNaN(value) ? 1.0 : Math.max(0, value);
    }

    updateZoomDurationHours(ev) {
        const value = parseFloat(ev.target.value);
        this.fieldState.activity_zoom_duration_hours = Number.isNaN(value) ? 1.0 : Math.max(0.25, value);
    }

    updateZoomMeetSummary(ev) {
        this.fieldState.activity_zoom_summary = ev.target.value;
    }

    getUserId(activity_user) {
        if (activity_user.selectionType === "variable") {
            return `${activity_user.value.pathValue}.id`
        } else if (activity_user.selectionType === "record") {
            const record = this.props.variables.find((item) => item.id === activity_user.value.record)
            return `${record.variable_name}.${activity_user.value.pathValue}`
        }
        return `${activity_user.value}`
    }

    getDeadLineValue(activity_deadline) {
        if (activity_deadline.selectionType === "variable") {
            return `${activity_deadline.value.pathValue}`
        } else if (activity_deadline.selectionType === "record") {
            const record = this.props.variables.find((item) => item.id === activity_deadline.value.record)
            return `${record.variable_name}.${activity_deadline.value.pathValue}`
        }
        return `"${activity_deadline.value}"`
    }

    generateCode() {
        const {
            activity_type,
            activity_summary,
            activity_deadline,
            activity_user,
            activity_record,
            activity_is_google_meet,
            activity_meet_offset_hours,
            activity_meet_duration_hours,
            activity_meet_summary,
            activity_also_schedule_activity,
            activity_is_zoom_meet,
            activity_zoom_offset_hours,
            activity_zoom_duration_hours,
            activity_zoom_summary,
            activity_also_schedule_activity_zoom,
        } = this.fieldState;
        const user_id = this.getUserId(activity_user);
        const deadline = this.getDeadLineValue(activity_deadline);
        const record = this.props.variables.find((variable) => variable.id === activity_record.value);
        const recordExpr = activity_record.label;
        // isRecordset: true when selected variable is a recordset (Search Node result).
        // buildFlowLines wraps subsequent nodes in "for current_record in <var>:",
        // so we use current_record here instead of the full recordset expression.
        const isRecordset = record ? record.variable_type !== 'record' : false;
        const escapedSummary = (activity_summary || '').replace(/\\/g, '\\\\').replace(/"""/g, '\\"\\"\\"');
        const scheduleArgs = `date_deadline=${deadline}, activity_type_id=${activity_type.id}, summary="""${escapedSummary}""", user_id=${user_id}`;
        const logCall = `_logger.warning('Activity node skipped: %s', exc)`;
        const shouldScheduleActivity = !activity_is_google_meet || activity_also_schedule_activity;
        const offsetHours = Number.parseFloat(activity_meet_offset_hours) || 1.0;
        const durationHours = Number.parseFloat(activity_meet_duration_hours) || 1.0;
        const meetingName = (activity_meet_summary || activity_summary || 'Meeting')
            .replace(/\\/g, '\\\\')
            .replace(/"/g, '\\"');
        const shouldScheduleActivityZoom = !activity_is_zoom_meet || activity_also_schedule_activity_zoom;
        const zoomOffsetHours = Number.parseFloat(activity_zoom_offset_hours) || 1.0;
        const zoomDurationHours = Number.parseFloat(activity_zoom_duration_hours) || 1.0;
        const zoomMeetingName = (activity_zoom_summary || activity_summary || 'Meeting')
            .replace(/\\/g, '\\\\')
            .replace(/"/g, '\\"');

        const actTarget = isRecordset ? 'current_record' : recordExpr;

        const scheduleCall = `_safe_schedule_activity(${actTarget}, ${scheduleArgs})`;
        const gmTarget = isRecordset ? 'current_record' : recordExpr;
        const zmTarget = isRecordset ? 'current_record' : recordExpr;

        let googleMeetBlock = "";
        if (activity_is_google_meet) {
            googleMeetBlock = `
    _gm_installed = env['ir.module.module'].sudo().search_count([
        ('name', '=', 'cyllo_google_meet'),
        ('state', '=', 'installed')
    ]) > 0
    if _gm_installed:
        _gm_params = env['ir.config_parameter'].sudo()
        _gm_configured = all([
            _gm_params.get_param('cyllo_google.client_id'),
            _gm_params.get_param('cyllo_google.client_secret'),
            _gm_params.get_param('cyllo_google.refresh_token'),
        ])
        if not _gm_configured:
            _logger.warning('Google Meet Activity node skipped: Google Meet credentials are not configured.')
        else:
            _ctx_rec = ${gmTarget}
            if _ctx_rec and getattr(_ctx_rec, 'id', False):
                _meet_start = fields.Datetime.now() + relativedelta(hours=${offsetHours})
                _meet_stop = _meet_start + relativedelta(hours=${durationHours})
                _partner_ids = []
                if hasattr(_ctx_rec, 'partner_id') and _ctx_rec.partner_id:
                    _partner_ids = _ctx_rec.partner_id.ids
                elif hasattr(_ctx_rec, 'partner_ids') and _ctx_rec.partner_ids:
                    _partner_ids = _ctx_rec.partner_ids.ids
                _cal_vals = {
                    'name': "${meetingName}",
                    'start': _meet_start,
                    'stop': _meet_stop,
                    'is_google_meet': True,
                    'partner_ids': [(6, 0, _partner_ids)],
                    'user_id': ${user_id},
                    'res_model_id': env['ir.model']._get_id(_ctx_rec._name),
                    'res_id': _ctx_rec.id,
                }
                try:
                    env['calendar.event'].sudo().create(_cal_vals)
                    _logger.info('Google Meet calendar event created for workflow activity node.')
                except Exception as _gm_exc:
                    _logger.error('Failed to create Google Meet calendar event: %s', _gm_exc)
            else:
                _logger.warning('Google Meet Activity node skipped: no valid record was available for event creation.')
    else:
        _logger.warning('Google Meet Activity node: cyllo_google_meet is not installed. Skipping Meet creation.')`;
        }

        let zoomMeetBlock = "";
        if (activity_is_zoom_meet) {
            zoomMeetBlock = `
    _zm_installed = env['ir.module.module'].sudo().search_count([
        ('name', '=', 'cyllo_zoom'),
        ('state', '=', 'installed')
    ]) > 0
    if _zm_installed:
        _zm_token = env['ir.config_parameter'].sudo().get_param('cyllo_zoom.zoom_token')
        if not _zm_token:
            _logger.warning('Zoom Activity node skipped: Zoom access token is not configured.')
        else:
            _zm_rec = ${zmTarget}
            if _zm_rec and getattr(_zm_rec, 'id', False):
                _zm_start = fields.Datetime.now() + relativedelta(hours=${zoomOffsetHours})
                _zm_stop = _zm_start + relativedelta(hours=${zoomDurationHours})
                _zm_partner_ids = []
                if hasattr(_zm_rec, 'partner_id') and _zm_rec.partner_id:
                    _zm_partner_ids = _zm_rec.partner_id.ids
                elif hasattr(_zm_rec, 'partner_ids') and _zm_rec.partner_ids:
                    _zm_partner_ids = _zm_rec.partner_ids.ids
                _zm_vals = {
                    'name': "${zoomMeetingName}",
                    'start': _zm_start,
                    'stop': _zm_stop,
                    'is_zoom_meet': True,
                    'partner_ids': [(6, 0, _zm_partner_ids)],
                    'user_id': ${user_id},
                    'res_model_id': env['ir.model']._get_id(_zm_rec._name),
                    'res_id': _zm_rec.id,
                }
                try:
                    env['calendar.event'].sudo().create(_zm_vals)
                    _logger.info('Zoom Meet calendar event created for workflow activity node.')
                except Exception as _zm_exc:
                    _logger.error('Failed to create Zoom Meet calendar event: %s', _zm_exc)
            else:
                _logger.warning('Zoom Activity node skipped: no valid record for Zoom event creation.')
    else:
        _logger.warning('Zoom Activity node: cyllo_zoom is not installed. Skipping Zoom creation.')`;
        }

        // Build body — buildFlowLines handles the outer recordset loop via auto-loop.
        // This node just needs try/except around the schedule call.
        let code = `\ntry:\n`;
        if (shouldScheduleActivity || shouldScheduleActivityZoom) {
            code += `    ${scheduleCall}\n`;
        }
        if (googleMeetBlock) code += `${googleMeetBlock}\n`;
        if (zoomMeetBlock)   code += `${zoomMeetBlock}\n`;
        code += `except Exception as exc:\n    ${logCall}\n`;
        return code;
    }

    getValidationValue(field) {
        if (['variable', 'record'].includes(field.selectionType)) return field.value?.pathValue
        return field.value
    }

    validateForm() {
        const {
            activity_type,
            activity_summary,
            activity_deadline,
            activity_user,
            activity_record,
            label,
            activity_is_google_meet,
            activity_meet_offset_hours,
            activity_meet_duration_hours,
            activity_is_zoom_meet,
            activity_zoom_offset_hours,
            activity_zoom_duration_hours,
        } = this.fieldState;
        // Validation rules
        const errors = {};
        const date = this.getValidationValue(activity_deadline)
        const user = this.getValidationValue(activity_user)
        // Validate label: must be a non-empty
        !label ? errors.label = "Label field must be a non-empty." : false
        //  Validate activity_record: must be a non-empty string
        !activity_record ? errors.activity_record = "Record must be a non-empty." : false
        // Validate activity_type: must not be a non-empty
        !activity_type ? errors.activity_type = "Activity Type must be a non-empty." : false
        // Validate activity_summary: must not be a non-empty
        !activity_summary ? errors.activity_summary = "Activity Summary must be a non-empty." : false
        // Validate activity_deadline: must not be a non-empty
        !date ? errors.activity_deadline = "Activity Deadline must be a non-empty." : false
        // Validate activity_user: must not be a non-empty
        !user ? errors.activity_user = "Activity User must be a non-empty." : false
        if (activity_is_google_meet) {
            const offset = parseFloat(activity_meet_offset_hours);
            const duration = parseFloat(activity_meet_duration_hours);
            if (!this.googleMeetState.configured) {
                errors.activity_is_google_meet = "Google Meet credentials are not configured. Please configure Client ID, Client Secret, and Refresh Token before creating a meeting activity.";
            }
            if (Number.isNaN(offset) || offset < 0) {
                errors.activity_meet_offset_hours = "Schedule After must be a number ≥ 0.";
            }
            if (Number.isNaN(duration) || duration < 0.25) {
                errors.activity_meet_duration_hours = "Meeting Duration must be at least 0.25 hours (15 minutes).";
            }
        }
        if (activity_is_zoom_meet) {
            const offset = parseFloat(activity_zoom_offset_hours);
            const duration = parseFloat(activity_zoom_duration_hours);
            if (!this.zoomMeetState.configured) {
                errors.activity_is_zoom_meet = "Zoom access token is not configured. Please go to Settings → Zoom Integration and connect your account.";
            }
            if (Number.isNaN(offset) || offset < 0) {
                errors.activity_zoom_offset_hours = "Zoom Schedule After must be a number >= 0.";
            }
            if (Number.isNaN(duration) || duration < 0.25) {
                errors.activity_zoom_duration_hours = "Zoom Meeting Duration must be at least 0.25 hours (15 minutes).";
            }
        }
        // If there are errors, return or log them
        if (Object.keys(errors).length > 0) {
            return { isValid: false, errors };
        }
        // If no errors, form is valid
        return { isValid: true };
    }
}

ActivityNode.template = "ActivityNode"
ActivityNode.components = { ...ConfigurationBase.components, CustomDropdown, FieldTypeDropdown, Many2XAutocomplete }
