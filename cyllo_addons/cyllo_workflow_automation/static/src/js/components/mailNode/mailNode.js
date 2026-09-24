/** @odoo-module */
const {useState, onWillStart, onMounted, onWillUnmount, useEffect} = owl;
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {Record} from "@web/model/record";
import {Many2OneField} from "@web/views/fields/many2one/many2one_field";
import {ModelFieldSelector} from "@web/core/model_field_selector/model_field_selector";
import {Select, Input} from "@web/core/tree_editor/tree_editor_components";
import {ConfigurationBase} from "../configurationBase/configurationBase";
import {Many2XAutocomplete} from "@web/views/fields/relational_utils";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {VariableSelector} from "../Assists/variableSelector/variableSelector";
import {getValueEditorInfo} from "@web/core/tree_editor/tree_editor_value_editors";
import {RecordPathSelector} from "../Assists/recordPathSelector/recordPathSelector";
import {TypeToggler} from "../Assists/typeToggler/TypeToggler";
import {FieldTypeDropdown} from "../Assists/fieldTypeDropdown/fieldTypeDropDown";
import {CustomDropdown} from "../Assists/dropdown/CustomDropdown";
import {MailRecordPathSelector} from "./subcomponents/mailRecordPathSelector";
import {MultiDataSelector} from "../FollowerNode/subComponents/multiDataSelector";
import {VariablePickerDialog} from "../Assists/variablePickerDialog/variablePickerDialog";

export class MailNode extends ConfigurationBase {
    static props = ['*'];
    setup() {
        super.setup();
        this.messageEditorRef = owl.useRef("messageEditor");
        this.mailFileInputRef = owl.useRef("mail_file_input");
        this.dialogService = useService("dialog");
        this.emailState = useState({
            mailTemp: ""
        })
        this.state = useState({
            templateId: false,
            applyModel: false,
            isTemplate: true
        })
        this.mailAttachState = useState({
            uploadingFile: false,
            financialReports: [],
        });
        // Tracks which formats are active at the current caret position, so the
        // toolbar buttons can show enabled/disabled the way Gmail/Word do.
        this.toolbarState = useState({
            bold: false,
            italic: false,
            underline: false,
            insertUnorderedList: false,
            insertOrderedList: false,
        });

        onWillStart(async () => {
            this.mailAttachState.financialReports = await this.orm.call(
                'workflow.report.attachment.mixin', 'get_financial_reports', []
            );
        });

        this.handleToolbarSelectionChange = () => this._syncToolbarState();

        // The message editor is a contenteditable surface, filled in imperatively
        // once on mount (like the old textarea's value binding, but for innerHTML).
        // It is deliberately NOT re-rendered reactively afterwards -- OWL would
        // otherwise reset the DOM content (and the caret) on every unrelated
        // fieldState change while the user is mid-edit.
        onMounted(() => {
            const editor = this.messageEditorRef.el;
            if (!editor) {
                return;
            }
            const raw = this.fieldState.mail_body || "";
            const html = this._isLegacyPlainTextBody(raw) ? this._legacyPlainTextToHtml(raw) : raw;
            editor.innerHTML = html;
            // Keep fieldState in sync with what is actually shown so a legacy
            // plain-text body is treated as HTML from here on (by generateCode
            // too) even if the user confirms without touching the message.
            if (html !== raw) {
                this.fieldState.mail_body = html;
            }
            // selectionchange is the only event that reliably fires for every
            // caret move (arrow keys, clicks, selection) inside contenteditable.
            document.addEventListener("selectionchange", this.handleToolbarSelectionChange);
        });

        onWillUnmount(() => {
            document.removeEventListener("selectionchange", this.handleToolbarSelectionChange);
        });
    }

    /**
     * Reflects the current caret's formatting onto toolbarState, so the
     * toolbar buttons highlight to show what's active where you're typing.
     * Ignored when the selection isn't inside this node's message editor.
     */
    _syncToolbarState() {
        const editor = this.messageEditorRef.el;
        if (!editor) {
            return;
        }
        const selection = document.getSelection();
        const isInEditor = selection && selection.anchorNode && editor.contains(selection.anchorNode);
        if (!isInEditor) {
            for (const command of Object.keys(this.toolbarState)) {
                this.toolbarState[command] = false;
            }
            return;
        }
        for (const command of Object.keys(this.toolbarState)) {
            try {
                this.toolbarState[command] = document.queryCommandState(command);
            } catch {
                this.toolbarState[command] = false;
            }
        }
    }

    /**
     * Mail nodes saved before the rich-text editor stored mail_body as plain
     * text (raw "\n" line breaks, no markup). Detect that shape so it can be
     * upgraded to HTML for display instead of collapsing onto a single line.
     */
    _isLegacyPlainTextBody(text) {
        return !!text && !/<[a-z][\s\S]*>/i.test(text);
    }

    _legacyPlainTextToHtml(text) {
        const escapeHtml = (line) => line
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        return text
            .replace(/\r\n|\r/g, '\n')
            .split('\n')
            .map((line) => `<div>${line ? escapeHtml(line) : '<br>'}</div>`)
            .join('');
    }

    _isMailBodyFilled(html) {
        return !!(html || "").replace(/<[^>]*>/g, '').trim().length;
    }

    applyFormat(command) {
        const editor = this.messageEditorRef.el;
        if (!editor) {
            return;
        }
        editor.focus();
        document.execCommand(command, false, null);
        this.setMessageValue(editor.innerHTML);
        this._syncToolbarState();
    }

    onMessageBlur(ev) {
        this.setMessageValue(ev.target.innerHTML);
    }

    async fetchData() {
        await super.fetchData();
        await this._normalizeMailAttachmentState();
    }

    async _normalizeMailAttachmentState() {
        const attachmentIds = this.fieldState.mail_static_attachment_ids || [];
        if (attachmentIds.length && typeof attachmentIds[0] !== "object") {
            const attachments = await this.orm.read("ir.attachment", attachmentIds, ["name"]);
            this.fieldState.mail_static_attachment_ids = attachments.map((attachment) => ({
                id: attachment.id,
                name: attachment.name,
            }));
        }

        const reportId = this.fieldState.mail_auto_report_id;
        if (typeof reportId === "number") {
            const [report] = await this.orm.read("ir.actions.report", [reportId], ["name"]);
            this.fieldState.mail_auto_report_id = report ? { id: report.id, name: report.name } : null;
        }
    }

    get getTogglerOptions() {
        return [
            {label: "custom", value: false},
            {label: "Template", value: true},
        ]
    }

    get getType() {
        return this.fieldState.mail_isTemplate || false
    }

    updateType(value) {
        this.fieldState.mail_isTemplate = value.value
    }

    get getSubject() {
        return this.fieldState.mail_subject || {}
    }

    setSubject(ev) {
        const mail_sub = this.fieldState.mail_subject || {}
        mail_sub.value = ev
        this.fieldState.mail_subject = mail_sub
    }

    setLabel(label) {
        this.fieldState.label = label
        const nodeId = this.props.id
        this.env.bus.trigger("CHANGE-LABEL", {label, nodeId});
    }

    get getLabel() {
        return this.fieldState.label || ""
    }

    get getMessage() {
        return this.fieldState.mail_body || ""
    }

    setMessageValue(ev) {
        this.fieldState.mail_body = ev;
    }

    openVariablePicker() {
        // The dialog steals focus from the contenteditable, so the caret
        // position has to be captured up-front -- a Range stays a valid
        // reference to that spot in the document even once focus moves away.
        const editor = this.messageEditorRef.el;
        let savedRange = null;
        const selection = window.getSelection();
        if (editor && selection && selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            if (editor.contains(range.commonAncestorContainer)) {
                savedRange = range.cloneRange();
            }
        }
        this.dialogService.add(VariablePickerDialog, {
            variables: this.props.variables,
            modelState: this.modelState,
            onInsert: (expression) => {
                if (editor) {
                    const range = savedRange || (() => {
                        const r = document.createRange();
                        r.selectNodeContents(editor);
                        r.collapse(false);
                        return r;
                    })();
                    selection.removeAllRanges();
                    selection.addRange(range);
                    range.deleteContents();
                    const textNode = document.createTextNode(expression);
                    range.insertNode(textNode);
                    range.setStartAfter(textNode);
                    range.collapse(true);
                    selection.removeAllRanges();
                    selection.addRange(range);
                    editor.focus();
                    this.setMessageValue(editor.innerHTML);
                } else {
                    this.setMessageValue(this.getMessage + expression);
                }
            }
        });
    }

    getDomain() {
        return [["model_id", "=", this.getModelId]]
    }

    get getModelId() {
        const modelId = this.variables.find(variable => variable.id === this.fieldState.mail_record.value)
        return modelId?.modelId || false
    }

    get getModel() {
        return this.fieldState.mail_record?.value || ""
    }

    get getTemplate() {
        return this.fieldState.mail_template.name || ''
    }

    getRecipient() {
        !this.fieldState.mail_to ? this.fieldState.mail_to = [{value: []}] : false
        return this.fieldState.mail_to
    }

    get getRecipientField() {
        return {type: "many2many",}
    }

    // Cc/Bcc are optional -- unlike "To" they are never auto-populated with a
    // default row, so the fields stay collapsed until the user opts in.
    _mailListFieldName(field) {
        return field === 'recipient' ? 'mail_to' : field === 'cc' ? 'mail_cc' : field === 'bcc' ? 'mail_bcc' : null;
    }

    getCc() {
        return this.fieldState.mail_cc || [];
    }

    getBcc() {
        return this.fieldState.mail_bcc || [];
    }

    clearMailList(field) {
        const listField = this._mailListFieldName(field);
        if (listField && field !== 'recipient') {
            this.fieldState[listField] = [];
        }
    }

    get getRecords() {
        let variables = []
        this.variables.forEach(variable => {
            variable.variable_type === 'record' && variable.modelId ? variables.push({
                value: variable.id,
                label: variable.variable_name
            }) : null
        })
        return variables
    }

    setData(value, index, field) {
        const listField = this._mailListFieldName(field);
        if (listField) {
            if (!this.fieldState[listField]) this.fieldState[listField] = [];
            const actualIndex = index ? index : 0
            this.fieldState[listField][actualIndex] = this.fieldState[listField][actualIndex] ? this.fieldState[listField][actualIndex] : {}
            this.fieldState[listField][actualIndex].value = value
        }
    }

    insertData(index, field) {
        const listField = this._mailListFieldName(field);
        if (listField) {
            if (!this.fieldState[listField]) this.fieldState[listField] = [];
            index !== false ? this.fieldState[listField].splice(index + 1, 0, {value: []}) : this.fieldState[listField].push({value: []})
        }
    }

    removeData(indexToRemove, field) {
        const listField = this._mailListFieldName(field);
        if (listField) {
            const filteredData = (this.fieldState[listField] || []).filter((_, index) => index !== indexToRemove)
            this.fieldState[listField] = filteredData
        }
    }

    onUpdateRecipients(ev) {
        let mail_to = this.fieldState.mail_to || {}
        mail_to.value = ev
        this.fieldState.mail_to = mail_to
    }

    getResDomain() {
        return []
    }

    updateObject(record) {
        this.fieldState.mail_record = this.getRecords.find((item) => item.value === record)
        if (!this.fieldState.mail_template) {
            this.fieldState.mail_template = {}
        }
        this.fieldState.mail_template.name = ""
        this.fieldState.mail_template.id = false
        this.getDomain()
    }

    getDropdownLabel(selectionType) {
        const labels = {
            static: 'Fixed',
            variable: 'Variable',
            record: 'Record',
        };
        return labels[selectionType] || 'Fixed';
    }

    getComponentProps(info) {
        const {value, update} = info.type === 'recipient'
            ? {value: this.getRecipient.value, update: (value) => this.onUpdateRecipients(value)}
            : info.type === 'subject'
                ? {value: this.getSubject.value || '', update: (value) => this.setSubject(value)}
                : false
        return info.extractProps({value, update})
    }

    getFieldData(type) {
        return ['recipient', 'cc', 'bcc'].includes(type)
            ? {fieldDef: {type: "many2one", relation: 'res.partner',}, operator: 'in'}
            : type === 'subject'
                ? {fieldDef: {type: "char"}, operator: '='}
                : false
    }

    getVariablesField(type, selectionType) {
        let flVariables;
        let fieldInfo;
        if (['recipient', 'cc', 'bcc'].includes(type)) {
            return selectionType === 'variable'
                ? {flVariables: (this.props.variables || []).filter(variable => ['record', 'recordset'].includes(variable.variable_type) && ["res.partner", "res.users", "hr.employee"].includes(variable.modelName))}
                : selectionType === 'record'
                    ? {
                        flVariables: (this.props.variables || []).filter(variable => variable.variable_type === "record"),
                        fieldInfo: {
                            resModel: this.modelState.model['model'],
                            fieldDef: {type: 'many2one', relation: ['res.partner', 'res.users']},
                        }
                    }
                    : false
        }
        if (type === 'subject') {
            return selectionType === 'variable'
                ? {flVariables: (this.props.variables || []).filter(variable => variable.variable_type === "string")}
                : selectionType === 'record'
                    ? {
                        flVariables: (this.props.variables || []).filter(variable => variable.variable_type === "record"),
                        fieldInfo: {resModel: this.modelState.model['model'], fieldDef: {type: 'char'},}
                    }
                    : false
        }

    }

    getValueEditorInfo(field, type) {
        const selectionType = field.selectionType ? field.selectionType : ''
        const {fieldDef, operator} = this.getFieldData(type)
        const {flVariables, fieldInfo} = this.getVariablesField(type, selectionType)
        let editorValue = getValueEditorInfo(fieldDef, operator);
        editorValue.type = type;
        if (selectionType === "variable") {
            return {
                component: VariableSelector,
                type,
                extractProps: ({value, update}) => {
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
                component: MailRecordPathSelector,
                type,
                extractProps: ({value, update}) => {
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
    toggleIncludeVariable(value, field, index) {
        const listField = this._mailListFieldName(field);
        if (listField) {
            if (!this.fieldState[listField]) this.fieldState[listField] = [];
            if (!this.fieldState[listField][index] || typeof this.fieldState[listField][index] !== 'object') {
                this.fieldState[listField][index] = {value: [], selectionType: value};
            } else if (![value, undefined].includes(this.fieldState[listField][index].selectionType)) {
                this.fieldState[listField][index] = {value: [], selectionType: value}
            }else this.fieldState[listField][index].selectionType = value
        } else if (field === 'subject') {
            if (!this.fieldState.mail_subject || typeof this.fieldState.mail_subject !== 'object') {
                this.fieldState.mail_subject = {value: '', selectionType: value};
            } else if (![value, undefined].includes(this.fieldState.mail_subject.selectionType)) {
                this.fieldState.mail_subject = {value: '', selectionType: value}
            }else this.fieldState.mail_subject.selectionType = value
        }
    }

    onSelectMail(ev) {
        if (!this.fieldState.mail_template) {
            this.fieldState.mail_template = {}
        }
        this.fieldState.mail_template.name = ev[0]?.display_name
        this.fieldState.mail_template.id = ev[0]?.id
    }

    getRecipientCode(mail_to) {
        let email_to = []
        let mail_rec;
        mail_to ? mail_to.forEach(field => {
            if (field.selectionType === 'variable') {
                mail_rec = (this.props.variables || []).filter((variable) => variable.id === field.value.selectedVariable)[0]
                // Skip: no variable selected yet. Can legitimately happen for the
                // optional Cc/Bcc rows, which are not required to be complete.
                if (!mail_rec) return;
                if (mail_rec.modelName === 'res.users') {
                    if (mail_rec.variable_type === 'recordset') {
                        email_to.push(`current_record.partner_id.id`)
                    } else {
                        email_to.push(`${mail_rec.variable_name}.partner_id.id`)
                    }
                } else if (mail_rec.modelName === "res.partner") {
                    if (mail_rec.variable_type === 'recordset') {
                        email_to.push(`current_record.id`)
                    } else {
                        email_to.push('*' + mail_rec.variable_name + '.ids')
                    }
                } else if (mail_rec.modelName === "hr.employee") {
                    if (mail_rec.variable_type === 'recordset') {
                        email_to.push(`current_record.work_contact_id.id`)
                    } else {
                        email_to.push(`${mail_rec.variable_name}.work_contact_id.id`)
                    }
                }
            } else if (field.selectionType === 'record') {
                mail_rec = (this.props.variables || []).filter((variable) => variable.id === field.value.record)[0]
                // Skip: no record selected yet (optional Cc/Bcc row left incomplete).
                if (!mail_rec) return;
                const targetRelation = field.value.info?.fieldDef?.relation
                const basePath = mail_rec.variable_name + '.' + field.value.path
                if (targetRelation === 'res.users') {
                    email_to.push(`${basePath}.partner_id.id`)
                } else if (targetRelation === 'hr.employee') {
                    email_to.push(`${basePath}.work_contact_id.id`)
                } else {
                    email_to.push(`${basePath}.id`)
                }
            } else {
                email_to.push(field.value)
            }
        }) : false
        return email_to
    }

    get getMailAttachmentModeOptions() {
        return [
            { label: "No Attachment", value: 'none' },
            { label: "Static File(s)", value: 'static' },
            { label: "Auto-generate (Accounting Report)", value: 'auto' },
        ];
    }

    get getMailAttachmentMode() {
        return this.fieldState.mail_attachment_mode || 'none';
    }

    updateMailAttachmentMode(value) {
        this.fieldState.mail_attachment_mode = value || 'none';
        if (value !== 'auto') {
            this.fieldState.mail_auto_report_id = null;
        }
    }

    get getMailStaticAttachments() {
        return (this.fieldState.mail_static_attachment_ids || []).map((attachment) => {
            if (Array.isArray(attachment)) {
                return { id: attachment[0], name: attachment[1] };
            }
            if (typeof attachment === "number") {
                return { id: attachment, name: `Attachment ${attachment}` };
            }
            return attachment;
        });
    }

    async onMailFileInputChange(ev) {
        const file = ev.target.files?.[0];
        if (!file) {
            return;
        }

        this.mailAttachState.uploadingFile = true;
        const reader = new FileReader();
        reader.onload = async (loadEvent) => {
            const base64Data = loadEvent.target?.result?.split(",")[1];
            if (!base64Data) {
                this.mailAttachState.uploadingFile = false;
                return;
            }
            try {
                const result = await this.rpc("/cyllo_workflow/upload_mail_attachment", {
                    name: file.name,
                    data: base64Data,
                    mimetype: file.type || 'application/octet-stream',
                    node_struct_id: this.props.nodeId || null,
                });
                this.fieldState.mail_static_attachment_ids = [
                    ...(this.fieldState.mail_static_attachment_ids || []),
                    { id: result.id, name: result.name },
                ];
            } catch (error) {
                console.error("Mail attachment upload failed", error);
            } finally {
                this.mailAttachState.uploadingFile = false;
                if (this.mailFileInputRef.el) {
                    this.mailFileInputRef.el.value = "";
                }
            }
        };
        reader.readAsDataURL(file);
    }

    openMailFilePicker() {
        this.mailFileInputRef.el?.click();
    }

    removeMailStaticAttachment(attachmentId) {
        this.fieldState.mail_static_attachment_ids = this.getMailStaticAttachments.filter(
            (attachment) => attachment.id !== attachmentId
        );
    }

    get getMailAutoReportOptions() {
        return (this.mailAttachState.financialReports || []).map((report) => ({
            label: report.name,
            value: report.id,
        }));
    }

    get getMailAutoReportValue() {
        return this.fieldState.mail_auto_report_id?.id || "";
    }

    updateMailAutoReport(reportId) {
        const report = (this.mailAttachState.financialReports || []).find((r) => r.id === reportId);
        this.fieldState.mail_auto_report_id = report ? { id: report.id, name: report.name } : null;
    }

    get getMailDatePresetOptions() {
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

    get getMailDatePreset() {
        return this.fieldState.mail_auto_report_date_preset || 'last_month';
    }

    updateMailDatePreset(value) {
        this.fieldState.mail_auto_report_date_preset = value || 'last_month';
    }

    get getMailCustomStartDate() {
        return this.fieldState.mail_auto_report_start_date || "";
    }

    setMailCustomStartDate(ev) {
        this.fieldState.mail_auto_report_start_date = ev.target ? ev.target.value : ev;
    }

    get getMailCustomEndDate() {
        return this.fieldState.mail_auto_report_end_date || "";
    }

    setMailCustomEndDate(ev) {
        this.fieldState.mail_auto_report_end_date = ev.target ? ev.target.value : ev;
    }

    get getMailTargetMoveOptions() {
        return [
            { label: "Posted Only", value: "posted" },
            { label: "All Entries", value: "all" },
        ];
    }

    get getMailTargetMove() {
        return this.fieldState.mail_auto_report_target_move || 'posted';
    }

    updateMailTargetMove(value) {
        this.fieldState.mail_auto_report_target_move = value || 'posted';
    }

    get getMailReportJournals() {
        return this.fieldState.mail_auto_report_journal_ids || [];
    }

    getMailReportJournalDomain() {
        return [];
    }

    onAddMailReportJournal(selection) {
        const item = selection[0];
        if (!item) {
            return;
        }
        const existing = this.getMailReportJournals;
        if (existing.some((journal) => journal.id === item.id)) {
            return;
        }
        this.fieldState.mail_auto_report_journal_ids = [
            ...existing,
            { id: item.id, name: item.display_name || item.name || "" },
        ];
    }

    removeMailReportJournal(journalId) {
        this.fieldState.mail_auto_report_journal_ids = this.getMailReportJournals.filter(
            (journal) => journal.id !== journalId
        );
    }

    get getMailReportAnalytics() {
        return this.fieldState.mail_auto_report_analytic_ids || [];
    }

    getMailReportAnalyticDomain() {
        return [];
    }

    onAddMailReportAnalytic(selection) {
        const item = selection[0];
        if (!item) {
            return;
        }
        const existing = this.getMailReportAnalytics;
        if (existing.some((analytic) => analytic.id === item.id)) {
            return;
        }
        this.fieldState.mail_auto_report_analytic_ids = [
            ...existing,
            { id: item.id, name: item.display_name || item.name || "" },
        ];
    }

    removeMailReportAnalytic(analyticId) {
        this.fieldState.mail_auto_report_analytic_ids = this.getMailReportAnalytics.filter(
            (analytic) => analytic.id !== analyticId
        );
    }

    /**
     * Build a Python dict-literal string for the report_filters kwarg (see
     * the equivalent helper in whatsappNode.js). Built by hand, not
     * JSON.stringify, since JSON's null/true/false aren't valid Python.
     */
    _buildMailReportFiltersCode() {
        const datePreset = this.fieldState.mail_auto_report_date_preset || 'last_month';
        const startDate = this.fieldState.mail_auto_report_start_date;
        const endDate = this.fieldState.mail_auto_report_end_date;
        const journalIds = (this.fieldState.mail_auto_report_journal_ids || []).map((j) => j.id);
        const analyticIds = (this.fieldState.mail_auto_report_analytic_ids || []).map((a) => a.id);
        const targetMove = this.fieldState.mail_auto_report_target_move || 'posted';

        const startDateCode = startDate ? JSON.stringify(startDate) : 'None';
        const endDateCode = endDate ? JSON.stringify(endDate) : 'None';

        return `{'date_preset': ${JSON.stringify(datePreset)}, 'start_date': ${startDateCode}, `
            + `'end_date': ${endDateCode}, 'journal_ids': ${JSON.stringify(journalIds)}, `
            + `'analytic_ids': ${JSON.stringify(analyticIds)}, 'target_move': ${JSON.stringify(targetMove)}}`;
    }

    /**
     * Python code that resolves the configured mail attachment (if any) into
     * a `mail_attachment_id` variable, for the free-form/custom send path
     * only. Template mode is untouched.
     */
    _buildMailAttachmentCode() {
        const mode = this.fieldState.mail_attachment_mode || 'none';
        if (mode === 'static') {
            const staticIds = (this.fieldState.mail_static_attachment_ids || [])
                .map((attachment) => Array.isArray(attachment) ? attachment[0] : attachment?.id || attachment)
                .filter(Boolean);
            if (!staticIds.length) {
                return '';
            }
            return `mail_attachment_id = env['ir.attachment'].sudo().browse(${staticIds[0]}).exists()\n`;
        }
        if (mode === 'auto' && this.fieldState.mail_auto_report_id?.id) {
            const reportFiltersCode = this._buildMailReportFiltersCode();
            return (
                `mail_report = env['ir.actions.report'].sudo().browse(${this.fieldState.mail_auto_report_id.id})\n`
                + `mail_attachment_id = env['workflow.report.attachment.mixin'].generate_report_attachment(`
                + `mail_report, None, ${reportFiltersCode})\n`
            );
        }
        return '';
    }

    generateCode() {
        const {mail_record, mail_template, mail_isTemplate, mail_to, mail_cc, mail_bcc, mail_body, mail_subject} = this.fieldState
        // const mail_selectionType = mail_to.selectionType || false
        const Record = this.variables.find(variable => variable.id === mail_record.value)
        let email_to = mail_to ? this.getRecipientCode(mail_to) : []
        let email_cc = mail_cc && mail_cc.length ? this.getRecipientCode(mail_cc) : []
        let email_bcc = mail_bcc && mail_bcc.length ? this.getRecipientCode(mail_bcc) : []
        let email_subject;
        let subject_rec;
        const subject_selectionType = mail_subject.selectionType
        if (subject_selectionType === 'variable') {
            subject_rec = (this.props.variables || []).filter((variable) => variable.id === mail_subject.value.selectedVariable)
            email_subject = subject_rec[0].variable_name
        } else if (subject_selectionType === 'record') {
            subject_rec = (this.props.variables || []).filter((variable) => variable.id === mail_subject.value.record)
            email_subject = subject_rec[0].variable_name + '.' + mail_subject.value.pathValue
        } else {
            email_subject = JSON.stringify(mail_subject.value)
        }
        let code = ``
        if (mail_isTemplate) {
            code = `template = env["mail.template"].browse(${mail_template.id})\nmail_id = template.send_mail(${Record?.variable_name}.id, force_send=False)\nenv['mail.mail'].sudo().browse(mail_id).send()`
        } else {
            const escapeLiteralBraces = (text) => text.replace(/\{/g, '{{').replace(/\}/g, '}}');
            const renderExpressions = (text) => (text || "")
                .split(/(\{\{\s*[^{}]+?\s*\}\})/g)
                .map(part => {
                    const match = part.match(/^\{\{\s*([^{}]+?)\s*\}\}$/);
                    return match ? `{${match[1]}}` : escapeLiteralBraces(part);
                })
                .join('');
            const rawBody = mail_body || "";
            const htmlBody = this._isLegacyPlainTextBody(rawBody) ? this._legacyPlainTextToHtml(rawBody) : rawBody;
            const processed_mail_body = renderExpressions(htmlBody)
            const attachmentMode = this.fieldState.mail_attachment_mode || 'none';
            const attachmentCode = this._buildMailAttachmentCode();
            const attachToMailVals = attachmentMode !== 'none'
                ? `\nif mail_attachment_id:\n    mail_vals['attachment_ids'] = [(6, 0, [mail_attachment_id.id])]`
                : '';

            // Cc maps directly onto mail.mail's own email_cc field.
            const ccPrelude = email_cc.length
                ? `cc_ids = [i for i in [${email_cc}] if i]\ncc = env["res.partner"].browse(cc_ids).mapped('email')\n`
                : '';
            const ccToMailVals = email_cc.length
                ? `\ncc_addresses = ','.join([e for e in set(cc) if e])\nif cc_addresses:\n    mail_vals['email_cc'] = cc_addresses`
                : '';

            // mail.mail has no native Bcc field/support, so Bcc is delivered as a
            // second, independent mail.mail addressed only to the bcc recipients --
            // this keeps them invisible to the To/Cc recipients, like a real Bcc.
            const bccPrelude = email_bcc.length
                ? `bcc_ids = [i for i in [${email_bcc}] if i]\nbcc = env["res.partner"].browse(bcc_ids).mapped('email')\n`
                : '';
            const attachToBccVals = attachmentMode !== 'none'
                ? `\n    if mail_attachment_id:\n        bcc_vals['attachment_ids'] = [(6, 0, [mail_attachment_id.id])]`
                : '';
            const bccSendCode = email_bcc.length
                ? `\nbcc_addresses = ','.join([e for e in set(bcc) if e])\nif bcc_addresses:\n    bcc_vals = {'subject': ${email_subject}, 'body_html': f"""${processed_mail_body}""", 'email_to': bcc_addresses}\n    if email_from:\n        bcc_vals['email_from'] = email_from${attachToBccVals}\n    env['mail.mail'].sudo().create(bcc_vals).send()`
                : '';

            code = `${attachmentCode}${ccPrelude}${bccPrelude}to_ids = [i for i in [${email_to}] if i]\nto = env["res.partner"].browse(to_ids).mapped('email')\nif not to and env.user.email:\n    to = [env.user.email]\nmail_vals = {'subject': ${email_subject}, 'body_html': f"""${processed_mail_body}""", 'email_to': ','.join([e for e in set(to) if e])}\nemail_from = env.user.email or env.company.email\nif email_from:\n    mail_vals['email_from'] = email_from${attachToMailVals}${ccToMailVals}\nemail_record = env['mail.mail'].sudo().create(mail_vals)\nemail_record.send()${bccSendCode}`
        }
        return code || "";
    }

    getValidateRecipient(fields, single) {
        let isField = true
        if (single) {
            if (['variable', 'record'].includes(fields.selectionType)) {
                if (!fields.value?.pathValue) {
                    isField = false
                }
            } else isField = fields.value?.length
        } else {
            fields.forEach(field => {
                if (['variable', 'record'].includes(field.selectionType)) {
                    if (!field.value?.pathValue) isField = false
                } else isField = field.value?.length
            })
        }
        return isField
    }

    validateForm() {
        const {mail_record, mail_template, mail_isTemplate, mail_to, mail_body, mail_subject, label} = this.fieldState;
        // Validation rules
        const errors = {};
        const recipients = this.getValidateRecipient(mail_to, false)
        const subject = this.getValidateRecipient(mail_subject, true)
        // Validate label: must be a non-empty
        !label ? errors.label = "Label field must be a non-empty." : false
        // Validate mail_record: must be a non-empty string
        if (mail_isTemplate && !mail_record) {
            errors.mail_record = "Record must be a non-empty.";
        }
        // Validate mail_template: must not be a non empty
        if (mail_isTemplate && !mail_template.id) {
            errors.mail_template = "Template must be a non-empty.";
        }
        // Validate mail_template: must not be a non empty
        !mail_isTemplate && !recipients ? errors.mail_to = "Mail to  must be a non-empty." : false

        // Validate mail_subject: must not be a non-empty
        !mail_isTemplate && !subject ? errors.mail_subject = "Mail subject  must be a non-empty." : false

        !mail_isTemplate && !this._isMailBodyFilled(mail_body) ? errors.mail_body = "Mail Message  must be a non-empty." : false

        // Validate attachment configuration (custom/free-form mode only;
        // Template mode keeps using the mail.template's own attachments).
        if (!mail_isTemplate) {
            const attachmentMode = this.fieldState.mail_attachment_mode || 'none';
            if (attachmentMode === 'static' && !(this.fieldState.mail_static_attachment_ids || []).length) {
                errors.mail_static_attachment_ids = "Please upload at least one attachment.";
            }
            if (attachmentMode === 'auto') {
                if (!this.fieldState.mail_auto_report_id?.id) {
                    errors.mail_auto_report_id = "Please select a report to auto-generate.";
                } else if (
                    this.getMailDatePreset === 'custom' &&
                    (!this.getMailCustomStartDate || !this.getMailCustomEndDate)
                ) {
                    errors.mail_auto_report_dates = "Please select a start and end date for the report.";
                }
            }
        }
        // If there are errors, return or log them
        if (Object.keys(errors).length > 0) {
            return {isValid: false, errors};
        }
        // If no errors, form is valid
        return {isValid: true};
    }
}

MailNode.template = "MailNode";
MailNode.components = {
    ...ConfigurationBase.components,
    Many2OneField,
    Record,
    Select,
    Input,
    Many2XAutocomplete,
    Dropdown,
    DropdownItem,
    TypeToggler,
    FieldTypeDropdown,
    CustomDropdown,
    MultiDataSelector,
};
