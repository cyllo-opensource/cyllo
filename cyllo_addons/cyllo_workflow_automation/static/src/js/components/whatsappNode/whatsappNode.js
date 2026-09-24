/** @odoo-module */
const { useState, onWillStart, useRef } = owl;
import { _t } from "@web/core/l10n/translation";
import { ConfigurationBase } from "../configurationBase/configurationBase";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { TypeToggler } from "../Assists/typeToggler/TypeToggler";
import { CustomDropdown } from "../Assists/dropdown/CustomDropdown";
import { useService } from "@web/core/utils/hooks";
import { getValueEditorInfo } from "@web/core/tree_editor/tree_editor_value_editors";
import { VariableSelector } from "../Assists/variableSelector/variableSelector";
import { MailRecordPathSelector } from "../mailNode/subcomponents/mailRecordPathSelector";
import { FieldTypeDropdown } from "../Assists/fieldTypeDropdown/fieldTypeDropDown";

export class WhatsAppNode extends ConfigurationBase {
    static props = ['*'];

    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.waState = useState({
            isInstalled: false,
            checking: true,
            uploadingFile: false,
            autoReportRequiresFilters: false,
        });
        this.fileInputRef = useRef("wa_file_input");

        onWillStart(async () => {
            await this._checkWhatsAppInstalled();
        });
    }

    async fetchData() {
        await super.fetchData();
        await this._normalizeAttachmentState();
        this._normalizePartnerFieldState();
    }

    /**
     * wa_partner_path used to only ever hold the "Customer" shortcut shape
     * {record, path: 'partner_id', pathValue: 'partner_id.id'}, with a
     * separate wa_partner_source/wa_other_partner pair covering the "Other"
     * case. Both are now unified into a single Fixed/Variable/Record field
     * (matching the Mail node's recipient selector), stored as
     * {selectionType, value} directly on wa_partner_path. Migrate old shapes
     * once on load so previously configured nodes keep resolving the same
     * partner.
     */
    _normalizePartnerFieldState() {
        const raw = this.fieldState.wa_partner_path;
        if (raw && typeof raw === "object" && "selectionType" in raw) {
            return;
        }
        if (this.fieldState.wa_partner_source === "other" && this.fieldState.wa_other_partner?.id) {
            this.fieldState.wa_partner_path = { selectionType: "static", value: this.fieldState.wa_other_partner.id };
        } else if (raw && typeof raw === "object" && raw.record) {
            this.fieldState.wa_partner_path = { selectionType: "record", value: raw };
        } else {
            this.fieldState.wa_partner_path = { selectionType: "static", value: false };
        }
    }

    async _normalizeAttachmentState() {
        const attachmentIds = this.fieldState.wa_static_attachment_ids || [];
        if (attachmentIds.length && typeof attachmentIds[0] !== "object") {
            const attachments = await this.orm.read("ir.attachment", attachmentIds, ["name"]);
            this.fieldState.wa_static_attachment_ids = attachments.map((attachment) => ({
                id: attachment.id,
                name: attachment.name,
            }));
        }

        const reportId = this.fieldState.wa_auto_report_id;
        if (typeof reportId === "number") {
            const [report] = await this.orm.read("ir.actions.report", [reportId], ["name"]);
            this.fieldState.wa_auto_report_id = report ? { id: report.id, name: report.name } : null;
        }

        await this._refreshReportFilterRequirement();
    }

    async _refreshReportFilterRequirement() {
        const reportId = this.fieldState.wa_auto_report_id?.id;
        if (!reportId) {
            this.waState.autoReportRequiresFilters = false;
            return;
        }
        try {
            this.waState.autoReportRequiresFilters = await this.orm.call(
                'workflow.report.attachment.mixin', 'report_requires_filter_data', [reportId]
            );
        } catch {
            this.waState.autoReportRequiresFilters = false;
        }
    }

    async _checkWhatsAppInstalled() {
        try {
            const count = await this.orm.searchCount('ir.module.module', [
                ['name', '=', 'cyllo_whatsapp'],
                ['state', '=', 'installed'],
            ]);
            this.waState.isInstalled = count > 0;
        } catch {
            this.waState.isInstalled = false;
        } finally {
            this.waState.checking = false;
        }
    }

    get getLabel() {
        return this.fieldState.label || "";
    }

    setLabel(ev) {
        const label = ev.target ? ev.target.value : ev;
        this.fieldState.label = label;
        this.env.bus.trigger("CHANGE-LABEL", { label, nodeId: this.props.id });
    }

    get getTogglerOptions() {
        return [
            { label: "Template", value: true },
            { label: "Free-form", value: false },
        ];
    }

    get isTemplateMode() {
        return this.fieldState.wa_is_template === true;
    }

    updateMode(option) {
        this.fieldState.wa_is_template = option.value;
    }

    get getRecordVariables() {
        return (this.props.variables || [])
            .filter((v) => v.variable_type === 'record' && v.modelId)
            .map((v) => ({ value: v.id, label: v.variable_name }));
    }

    get getSelectedRecord() {
        return this.fieldState.wa_record?.value || "";
    }

    async updateRecord(variableId) {
        const previousRecordId = this.fieldState.wa_record?.value;
        this.fieldState.wa_record = { value: variableId };
        if (previousRecordId !== variableId) {
            this.fieldState.wa_auto_report_id = null;
        }
    }

    get getPartnerField() {
        return this.fieldState.wa_partner_path || {};
    }

    setPartnerFieldValue(value) {
        const field = this.fieldState.wa_partner_path || {};
        field.value = value;
        this.fieldState.wa_partner_path = field;
    }

    togglePartnerFieldType(type) {
        if (!this.fieldState.wa_partner_path || typeof this.fieldState.wa_partner_path !== "object") {
            this.fieldState.wa_partner_path = { value: false, selectionType: type };
        } else if (![type, undefined].includes(this.fieldState.wa_partner_path.selectionType)) {
            this.fieldState.wa_partner_path = { value: false, selectionType: type };
        } else {
            this.fieldState.wa_partner_path.selectionType = type;
        }
    }

    getPartnerFieldData() {
        return { fieldDef: { type: "many2one", relation: 'res.partner' }, operator: '=' };
    }

    getPartnerVariablesField(selectionType) {
        return selectionType === 'variable'
            ? {
                flVariables: (this.props.variables || []).filter(
                    (variable) => ['record', 'recordset'].includes(variable.variable_type)
                        && ["res.partner", "res.users", "hr.employee"].includes(variable.modelName)
                ),
            }
            : selectionType === 'record'
                ? {
                    flVariables: (this.props.variables || []).filter((variable) => variable.variable_type === "record"),
                    fieldInfo: {
                        resModel: this.modelState.model['model'],
                        fieldDef: { type: 'many2one', relation: ['res.partner', 'res.users'] },
                    },
                }
                : {};
    }

    getPartnerValueEditorInfo() {
        const field = this.getPartnerField;
        const selectionType = field.selectionType || '';
        const { fieldDef, operator } = this.getPartnerFieldData();
        const { flVariables, fieldInfo } = this.getPartnerVariablesField(selectionType);
        if (selectionType === "variable") {
            return {
                component: VariableSelector,
                extractProps: ({ value, update }) => ({
                    value, update, allVariable: true, variables: flVariables,
                }),
            };
        } else if (selectionType === "record") {
            return {
                component: MailRecordPathSelector,
                extractProps: ({ value, update }) => ({
                    value, update, variables: flVariables, fieldInfo,
                }),
            };
        }
        return getValueEditorInfo(fieldDef, operator);
    }

    getPartnerComponentProps(info) {
        return info.extractProps({
            value: this.getPartnerField.value,
            update: (value) => this.setPartnerFieldValue(value),
        });
    }

    getPartnerDropdownLabel() {
        const labels = { static: 'Fixed', variable: 'Variable', record: 'Record' };
        return labels[this.getPartnerField.selectionType] || 'Fixed';
    }

    get getTemplateName() {
        return this.fieldState.wa_template?.name || "";
    }

    getTemplateDomain() {
        return [['state', '=', 'approved']];
    }

    onSelectTemplate(selection) {
        this.fieldState.wa_template = {
            id: selection[0]?.id || false,
            name: selection[0]?.display_name || "",
        };
    }

    get getFreeMessage() {
        return this.fieldState.wa_free_message || "";
    }

    setFreeMessage(ev) {
        this.fieldState.wa_free_message = ev.target ? ev.target.value : ev;
    }

    get getAttachmentModeOptions() {
        return [
            { label: "No Attachment", value: 'none' },
            { label: "Static File(s)", value: 'static' },
            { label: "Auto-generate from Record", value: 'auto' },
        ];
    }

    get getAttachmentMode() {
        return this.fieldState.wa_attachment_mode || 'none';
    }

    updateAttachmentMode(value) {
        this.fieldState.wa_attachment_mode = value || 'none';
        if (value !== 'static') {
            this.fieldState.wa_static_attachment_ids = this.fieldState.wa_static_attachment_ids || [];
        }
        if (value !== 'auto') {
            this.fieldState.wa_auto_report_id = null;
        }
    }

    get getStaticAttachments() {
        return (this.fieldState.wa_static_attachment_ids || []).map((attachment) => {
            if (Array.isArray(attachment)) {
                return { id: attachment[0], name: attachment[1] };
            }
            if (typeof attachment === "number") {
                return { id: attachment, name: `Attachment ${attachment}` };
            }
            return attachment;
        });
    }

    async onFileInputChange(ev) {
        const file = ev.target.files?.[0];
        if (!file) {
            return;
        }

        this.waState.uploadingFile = true;
        const reader = new FileReader();
        reader.onload = async (loadEvent) => {
            const base64Data = loadEvent.target?.result?.split(",")[1];
            if (!base64Data) {
                this.waState.uploadingFile = false;
                return;
            }
            try {
                const result = await this.rpc("/cyllo_workflow/upload_wa_attachment", {
                    name: file.name,
                    data: base64Data,
                    mimetype: file.type || 'application/octet-stream',
                    node_struct_id: this.props.nodeId || null,
                });
                this.fieldState.wa_static_attachment_ids = [
                    ...(this.fieldState.wa_static_attachment_ids || []),
                    { id: result.id, name: result.name },
                ];
            } catch (error) {
                console.error("WA attachment upload failed", error);
            } finally {
                this.waState.uploadingFile = false;
                if (this.fileInputRef.el) {
                    this.fileInputRef.el.value = "";
                }
            }
        };
        reader.readAsDataURL(file);
    }

    openFilePicker() {
        this.fileInputRef.el?.click();
    }

    removeStaticAttachment(attachmentId) {
        this.fieldState.wa_static_attachment_ids = this.getStaticAttachments.filter(
            (attachment) => attachment.id !== attachmentId
        );
    }

    get getAutoReportName() {
        return this.fieldState.wa_auto_report_id?.name || "";
    }

    getAutoReportDomain() {
        const variableId = this.fieldState.wa_record?.value;
        if (!variableId) {
            return [];
        }
        const variable = (this.props.variables || []).find((item) => item.id === variableId);
        if (!variable?.modelName) {
            return [];
        }
        return [
            ['model', '=', variable.modelName],
            ['report_type', '=', 'qweb-pdf'],
        ];
    }

    onSelectAutoReport(selection) {
        this.fieldState.wa_auto_report_id = selection[0] ? {
            id: selection[0].id,
            name: selection[0].display_name || selection[0].name || "",
        } : null;
        this._refreshReportFilterRequirement();
    }

    get getDatePresetOptions() {
        return [
            { label: "Today", value: "today" },
            { label: "Yesterday", value: "yesterday" },
            { label: "Last 7 Days", value: "last_7_days" },
            { label: "This Week", value: "this_week" },
            { label: "Last Week", value: "last_week" },
            { label: "This Month", value: "this_month" },
            { label: "Last Month", value: "last_month" },
            { label: "This Quarter", value: "this_quarter" },
            { label: "Last Quarter", value: "last_quarter" },
            { label: "This Year", value: "this_year" },
            { label: "Last Year", value: "last_year" },
            { label: "Custom Range", value: "custom" },
        ];
    }

    get getDatePreset() {
        return this.fieldState.wa_auto_report_date_preset || 'last_month';
    }

    updateDatePreset(value) {
        this.fieldState.wa_auto_report_date_preset = value || 'last_month';
    }

    get getCustomStartDate() {
        return this.fieldState.wa_auto_report_start_date || "";
    }

    setCustomStartDate(ev) {
        this.fieldState.wa_auto_report_start_date = ev.target ? ev.target.value : ev;
    }

    get getCustomEndDate() {
        return this.fieldState.wa_auto_report_end_date || "";
    }

    setCustomEndDate(ev) {
        this.fieldState.wa_auto_report_end_date = ev.target ? ev.target.value : ev;
    }

    get getTargetMoveOptions() {
        return [
            { label: "Posted Only", value: "posted" },
            { label: "All Entries", value: "all" },
        ];
    }

    get getTargetMove() {
        return this.fieldState.wa_auto_report_target_move || 'posted';
    }

    updateTargetMove(value) {
        this.fieldState.wa_auto_report_target_move = value || 'posted';
    }

    get getReportJournals() {
        return this.fieldState.wa_auto_report_journal_ids || [];
    }

    getReportJournalDomain() {
        return [];
    }

    onAddReportJournal(selection) {
        const item = selection[0];
        if (!item) {
            return;
        }
        const existing = this.getReportJournals;
        if (existing.some((journal) => journal.id === item.id)) {
            return;
        }
        this.fieldState.wa_auto_report_journal_ids = [
            ...existing,
            { id: item.id, name: item.display_name || item.name || "" },
        ];
    }

    removeReportJournal(journalId) {
        this.fieldState.wa_auto_report_journal_ids = this.getReportJournals.filter(
            (journal) => journal.id !== journalId
        );
    }

    get getReportAnalytics() {
        return this.fieldState.wa_auto_report_analytic_ids || [];
    }

    getReportAnalyticDomain() {
        return [];
    }

    onAddReportAnalytic(selection) {
        const item = selection[0];
        if (!item) {
            return;
        }
        const existing = this.getReportAnalytics;
        if (existing.some((analytic) => analytic.id === item.id)) {
            return;
        }
        this.fieldState.wa_auto_report_analytic_ids = [
            ...existing,
            { id: item.id, name: item.display_name || item.name || "" },
        ];
    }

    removeReportAnalytic(analyticId) {
        this.fieldState.wa_auto_report_analytic_ids = this.getReportAnalytics.filter(
            (analytic) => analytic.id !== analyticId
        );
    }

    generateCode() {
        const {
            wa_record,
            wa_is_template,
            wa_template,
            wa_partner_path,
            wa_free_message,
            wa_attachment_mode,
            wa_static_attachment_ids,
            wa_auto_report_id,
        } = this.fieldState;

        if (!wa_record?.value) {
            return "# WhatsApp node: no record variable selected";
        }

        const variable = (this.props.variables || []).find((v) => v.id === wa_record.value);
        if (!variable) {
            return "# WhatsApp node: record variable not found";
        }

        this.updateUsedVariables(wa_record.value);
        const recordVarName = variable.variable_name;
        const templateId = wa_is_template === true && wa_template?.id ? wa_template.id : 'None';
        const freeMsg = JSON.stringify(wa_free_message || "");
        const partnerIdCode = this._buildPartnerIdCode(wa_partner_path);
        const attachmentMode = JSON.stringify(wa_attachment_mode || 'none');
        const staticAttachmentIds = (wa_static_attachment_ids || [])
            .map((attachment) => Array.isArray(attachment) ? attachment[0] : attachment?.id || attachment)
            .filter(Boolean);
        const staticAttachmentIdsCode = staticAttachmentIds.length
            ? JSON.stringify(staticAttachmentIds)
            : 'None';
        const autoReportId = wa_auto_report_id?.id || 'None';
        const reportFiltersCode = wa_attachment_mode === 'auto' && wa_auto_report_id?.id
            ? this._buildReportFiltersCode('wa_auto_report')
            : 'None';

        return [
            `env['wa.workflow.executor'].send_workflow_whatsapp(`,
            `    ${recordVarName},`,
            `    None,`,
            `    template_id=${templateId},`,
            `    free_message=${templateId === 'None' ? freeMsg : 'None'},`,
            `    partner_id=${partnerIdCode},`,
            `    attachment_mode=${attachmentMode},`,
            `    static_attachment_ids=${staticAttachmentIdsCode},`,
            `    auto_report_id=${autoReportId},`,
            `    report_filters=${reportFiltersCode},`,
            `)`,
        ].join('\n');
    }

    /**
     * Resolve the Fixed/Variable/Record partner field into a Python
     * expression that evaluates to a res.partner id (or None), mirroring
     * the Mail node's recipient code generation (getRecipientCode).
     */
    _buildPartnerIdCode(field) {
        if (!field || !field.selectionType) {
            return 'None';
        }
        if (field.selectionType === 'variable') {
            const rec = (this.props.variables || []).find((v) => v.id === field.value?.selectedVariable);
            if (!rec) return 'None';
            if (rec.modelName === 'res.users') {
                return rec.variable_type === 'recordset'
                    ? `(${rec.variable_name}[:1].partner_id.id if ${rec.variable_name} else None)`
                    : `(${rec.variable_name}.partner_id.id if ${rec.variable_name} else None)`;
            }
            if (rec.modelName === 'res.partner') {
                return rec.variable_type === 'recordset'
                    ? `(${rec.variable_name}[:1].id if ${rec.variable_name} else None)`
                    : `(${rec.variable_name}.id if ${rec.variable_name} else None)`;
            }
            if (rec.modelName === 'hr.employee') {
                return rec.variable_type === 'recordset'
                    ? `(${rec.variable_name}[:1].work_contact_id.id if ${rec.variable_name} else None)`
                    : `(${rec.variable_name}.work_contact_id.id if ${rec.variable_name} else None)`;
            }
            return 'None';
        }
        if (field.selectionType === 'record') {
            const rec = (this.props.variables || []).find((v) => v.id === field.value?.record);
            if (!rec || !field.value?.path) return 'None';
            const targetRelation = field.value.info?.fieldDef?.relation;
            const basePath = `${rec.variable_name}.${field.value.path}`;
            if (targetRelation === 'res.users') {
                return `(${basePath}.partner_id.id if ${basePath} else None)`;
            }
            if (targetRelation === 'hr.employee') {
                return `(${basePath}.work_contact_id.id if ${basePath} else None)`;
            }
            return `(${basePath}.id if ${basePath} else None)`;
        }
        // static / fixed: a single partner id from the many2one "=" editor
        const id = Array.isArray(field.value) ? field.value[0] : field.value;
        return id ? JSON.stringify(id) : 'None';
    }

    /**
     * Build a Python dict-literal string for the report_filters kwarg from
     * this.fieldState[`${prefix}_date_preset` | `_start_date` | ... ]. Built
     * by hand (not JSON.stringify) because JSON's null/true/false aren't
     * valid Python literals.
     */
    _buildReportFiltersCode(prefix) {
        const datePreset = this.fieldState[`${prefix}_date_preset`] || 'last_month';
        const startDate = this.fieldState[`${prefix}_start_date`];
        const endDate = this.fieldState[`${prefix}_end_date`];
        const journalIds = (this.fieldState[`${prefix}_journal_ids`] || []).map((j) => j.id);
        const analyticIds = (this.fieldState[`${prefix}_analytic_ids`] || []).map((a) => a.id);
        const targetMove = this.fieldState[`${prefix}_target_move`] || 'posted';

        const startDateCode = startDate ? JSON.stringify(startDate) : 'None';
        const endDateCode = endDate ? JSON.stringify(endDate) : 'None';

        return `{'date_preset': ${JSON.stringify(datePreset)}, 'start_date': ${startDateCode}, `
            + `'end_date': ${endDateCode}, 'journal_ids': ${JSON.stringify(journalIds)}, `
            + `'analytic_ids': ${JSON.stringify(analyticIds)}, 'target_move': ${JSON.stringify(targetMove)}}`;
    }

    _hasPartnerFieldValue(field) {
        if (!field || !field.selectionType) return false;
        const { value } = field;
        if (field.selectionType === 'variable') return !!value?.selectedVariable;
        if (field.selectionType === 'record') return !!(value?.record && value?.path);
        return !!value;
    }

    validateForm() {
        const {
            wa_record,
            wa_is_template,
            wa_partner_path,
            wa_free_message,
            wa_attachment_mode,
            wa_auto_report_id,
            label,
        } = this.fieldState;
        const errors = {};

        if (!label?.trim()) {
            errors.label = _t("Label is required.");
        }
        if (!wa_record?.value) {
            errors.wa_record = _t("Please select a record variable.");
        }
        if (!this._hasPartnerFieldValue(wa_partner_path)) {
            errors.wa_partner_path = _t("Please configure who the WhatsApp message is sent to.");
        }
        if (wa_is_template !== true && !wa_free_message?.trim()) {
            errors.wa_free_message = _t("Please enter a message text.");
        }
        if (wa_attachment_mode === 'auto') {
            if (!wa_record?.value) {
                errors.wa_auto_report_id = _t("Please select a record variable first.");
            } else if (!wa_auto_report_id?.id) {
                errors.wa_auto_report_id = _t("Please select a report to auto-generate.");
            } else if (
                this.waState.autoReportRequiresFilters &&
                this.getDatePreset === 'custom' &&
                (!this.getCustomStartDate || !this.getCustomEndDate)
            ) {
                errors.wa_auto_report_dates = _t("Please select a start and end date for the report.");
            }
        }
        if (wa_attachment_mode === 'static' && !(this.fieldState.wa_static_attachment_ids || []).length) {
            errors.wa_static_attachment_ids = _t("Please upload at least one attachment.");
        }

        return Object.keys(errors).length
            ? { isValid: false, errors }
            : { isValid: true };
    }
}

WhatsAppNode.template = "WhatsAppNode";
WhatsAppNode.components = {
    ...ConfigurationBase.components,
    Many2XAutocomplete,
    TypeToggler,
    CustomDropdown,
    FieldTypeDropdown,
};
