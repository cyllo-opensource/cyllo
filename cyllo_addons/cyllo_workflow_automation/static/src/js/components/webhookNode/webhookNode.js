/** @odoo-module */
const { useState } = owl;
import { ConfigurationBase } from "../configurationBase/configurationBase";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";

export class WebhookNode extends ConfigurationBase {
    static props = ['*'];

    setup() {
        super.setup();

        this.uiState = useState({
            // Header builder rows — purely visual, syncs TO fieldState.webhook_headers
            headerRows: [], // Initialised properly in fetchData()
            headerBuilderOpen: false,

            // Custom payload form state
            // Custom payload form state
            payloadMode: 'fields',
            payloadFieldPath: '',
            customPayloadKey: '',
            customPayloadValue: '',

            // Copy-to-clipboard feedback
            urlCopied: false,

            // Secret URL state
            secretUrl: '',
            secretUrlCopied: false,
            regenerating: false,

            // Response Actions panel
            responseActionsOpen: true,
            showAddActionForm: false,
            newActionExtractPath: '',
            newActionType: 'chatter_link',
            newActionLabel: '',
            newActionFieldToWrite: '',
            newActionVariableName: '',
            newActionEmailRecipients: '',
            newActionTarget: 'new',
            editingActionIndex: null,
        });

        // Ensure webhook_actions is always an array
        if (!Array.isArray(this.fieldState.webhook_actions)) {
            this.fieldState.webhook_actions = [];
        }
    }

    async fetchData() {
        await super.fetchData();

        // ── Ensure sane defaults AFTER fetching from database ──────────
        // (If it's a new node, the DB returns false/null for empty fields)
        if (!this.fieldState.webhook_method || typeof this.fieldState.webhook_method === 'object') {
            this.fieldState.webhook_method = 'POST';
        }
        if (!this.fieldState.webhook_headers || typeof this.fieldState.webhook_headers === 'object') {
            this.fieldState.webhook_headers = '{"Content-Type": "application/json"}';
        }

        // Ensure actions is always a clean array, even if DB returned a string or false
        let actions = this.fieldState.webhook_actions;
        if (typeof actions === 'string') {
            try { actions = JSON.parse(actions); } catch (e) { actions = []; }
        }
        if (!Array.isArray(actions)) {
            actions = [];
        }
        this.fieldState.webhook_actions = actions;

        // Sync header rows using the actual DB value / defaults
        this.uiState.headerRows = this._parseHeadersToRows(this.fieldState.webhook_headers);

        // ── Fetch the Secret URL from the controller (assembles live base URL) ──────
        const nodeId = this.props.id || this.props.nodeId;
        if (nodeId) {
            try {
                const result = await this.env.services.rpc(
                    `/cyllo_workflow/webhook_secret_url/${nodeId}`, {}
                );
                if (result && result.url) {
                    this.uiState.secretUrl = result.url;
                    // Also keep the raw token in fieldState so save_data persists it
                    if (result.token) {
                        this.fieldState.webhook_secret_token = result.token;
                    }
                }
            } catch (err) {
                console.warn('WebhookNode: could not fetch secret URL:', err);
            }
        }
    }

    // ════════════════════════════════════════════════════════════════════════
    // ORIGINAL METHODS — UNTOUCHED
    // ════════════════════════════════════════════════════════════════════════

    get getMethodOptions() {
        return [
            { label: 'POST',   value: 'POST'   },
            { label: 'GET',    value: 'GET'    },
            { label: 'PUT',    value: 'PUT'    },
            { label: 'DELETE', value: 'DELETE' },
        ];
    }

    get currentRecordModelName() {
        if (this.modelState.model && this.modelState.model.model) {
            return this.modelState.model.model;
        }
        const recordVar = this.props.variables?.find(v => v.variable_name === 'current_record' || v.variable_type === 'record');
        return recordVar?.modelName || recordVar?.model_name || "";
    }

    get getLabel() {
        return this.fieldState.label || "";
    }

    setLabel(label) {
        this.fieldState.label = label;
        const nodeId = this.props.id;
        this.env.bus.trigger("CHANGE-LABEL", { label, nodeId });
    }

    /**
     * generateCode() — COMPLETELY UNCHANGED FROM ORIGINAL.
     * Reads webhook_url, webhook_method, webhook_headers, webhook_payload
     * from fieldState exactly as before.
     */
    generateCode() {
        const url = this.fieldState.webhook_url || "";
        const method = this.fieldState.webhook_method || "POST";
        const headers = this.fieldState.webhook_headers || '{"Content-Type": "application/json"}';
        const payload = this.fieldState.webhook_payload || "";

        // Escape JSON curly braces for Python's f-string parsing,
        // while preserving dynamic placeholders.
        let escapedPayload = payload.replace(/\{/g, '{{').replace(/\}/g, '}}');
        
        // The user writes {{ expression }}, which became {{{{ expression }}}}.
        // We revert the outer 4 braces to 1 brace so Python's f-string evaluates it.
        // We safely escape the evaluated string using chr() to prevent double-quote and newline syntax errors inside JSON strings.
        escapedPayload = escapedPayload.replace(/\{\{\{\{(.+?)\}\}\}\}/g, (match, expression) => {
            const exp = expression.replace(/current_record\./g, 'record.');
            return `{str(${exp}).replace(chr(92), chr(92)+chr(92)).replace(chr(34), chr(92)+chr(34)).replace(chr(10), chr(92)+'n').replace(chr(13), chr(92)+'r').replace(chr(9), chr(92)+'t') if ${exp} else ""}`;
        });

        // Serialise the response actions config (may be empty list / null)
        const rawActions = this.fieldState.webhook_actions;
        const actionsJson = (rawActions && Array.isArray(rawActions) && rawActions.length > 0)
            ? JSON.stringify(rawActions)
            : '[]';

        let code = ``;
        code += `url = f"${url}"\n`;
        code += `headers = ${headers}\n`;
        code += `payload = f"""${escapedPayload}"""\n`;
        code += `_webhook_response_actions = ${actionsJson}\n`;
        code += `\n`;
        code += `try:\n`;
        code += `    if "${method}" == "GET":\n`;
        code += `        response = requests.get(url, headers=headers)\n`;
        code += `    elif "${method}" == "POST":\n`;
        code += `        response = requests.post(url, headers=headers, data=payload.encode('utf-8'))\n`;
        code += `    elif "${method}" == "PUT":\n`;
        code += `        response = requests.put(url, headers=headers, data=payload.encode('utf-8'))\n`;
        code += `    elif "${method}" == "DELETE":\n`;
        code += `        response = requests.delete(url, headers=headers)\n`;
        code += `    if not response.ok:\n`;
        code += `        err_msg = f"HTTP {response.status_code} Error: {response.text}"\n`;
        code += `        _logger.error("Webhook HTTP failure: %s -> %s", url, err_msg)\n`;
        code += `        raise UserError(f"Webhook Execution Failed: {err_msg}")\n`;
        code += `    _logger.info("Webhook success: %s %s -> %s", "", url, response.status_code)\n`;
        code += `    # ── Generic response action processing ──────────────────────\n`;
        code += `    if _webhook_response_actions:\n`;
        code += `        try:\n`;
        code += `            _resp_json = response.json()\n`;
        code += `        except Exception:\n`;
        code += `            _resp_json = {"_raw": response.text}\n`;
        code += `        _resp_action = env['webhook.response.processor'].process_response_actions(\n`;
        code += `            response_data=_resp_json,\n`;
        code += `            actions=_webhook_response_actions,\n`;
        code += `            record=current_record,\n`;
        code += `            context_vars=globals(),\n`;
        code += `        )\n`;
        code += `        if _resp_action:\n`;
        code += `            action = _resp_action\n`;
        code += `        # -- Inject store_variable values into shared execution context --\n`;
        code += `        for _wh_sv in [a for a in _webhook_response_actions if a.get('action_type') == 'store_variable']:\n`;
        code += `            _wh_vn = (_wh_sv.get('variable_name') or '').strip()\n`;
        code += `            if not _wh_vn: continue\n`;
        code += `            _wh_vv = _resp_json\n`;
        code += `            for _wh_k in (_wh_sv.get('extract_path') or '').split('.'):\n`;
        code += `                if not _wh_k: break\n`;
        code += `                if isinstance(_wh_vv, dict): _wh_vv = _wh_vv.get(_wh_k)\n`;
        code += `                elif isinstance(_wh_vv, list):\n`;
        code += `                    try: _wh_vv = _wh_vv[int(_wh_k)]\n`;
        code += `                    except: _wh_vv = None; break\n`;
        code += `                else: _wh_vv = None; break\n`;
        code += `            globals()[_wh_vn] = _wh_vv\n`;
        code += `            _logger.info('Webhook variable injected: %s = %r', _wh_vn, _wh_vv)\n`;
        code += `except Exception as e:\n`;
        code += `    _logger.error("Webhook execution error: %s", str(e))\n`;
        code += `    if isinstance(e, UserError):\n`;
        code += `        raise e\n`;
        code += `    raise UserError(f"Webhook Execution Error: {str(e)}")\n`;

        return code;
    }

    /**
     * validateForm() — COMPLETELY UNCHANGED FROM ORIGINAL.
     */
    validateForm() {
        const { webhook_url, webhook_method, label } = this.fieldState;
        const errors = {};
        if (!label)         errors.label         = "Label must be non-empty.";
        if (!webhook_url)   errors.webhook_url   = "URL is required.";
        if (!webhook_method) errors.webhook_method = "Method is required.";
        if (Object.keys(errors).length > 0) {
            return { isValid: false, errors };
        }
        return { isValid: true };
    }

    // ════════════════════════════════════════════════════════════════════════
    // UI-ONLY HELPERS  —  read/write fieldState.webhook_headers and
    //                      fieldState.webhook_payload only through the
    //                      same string format the original code always used.
    //                      generateCode() still sees identical strings.
    // ════════════════════════════════════════════════════════════════════════

    // ── Method badge colour ──────────────────────────────────────────────
    get methodBadgeStyle() {
        const colours = {
            POST:   'background:#198754;color:#fff',
            GET:    'background:#0d6efd;color:#fff',
            PUT:    'background:#fd7e14;color:#fff',
            DELETE: 'background:#dc3545;color:#fff',
        };
        return colours[this.fieldState.webhook_method] || 'background:#6c757d;color:#fff';
    }

    // ── URL copy helper ──────────────────────────────────────────────────
    copyUrl() {
        const url = this.fieldState.webhook_url || '';
        if (!url) return;
        navigator.clipboard.writeText(url).then(() => {
            this.uiState.urlCopied = true;
            setTimeout(() => { this.uiState.urlCopied = false; }, 1800);
        });
    }

    // ── Secret URL helpers ─────────────────────────────────────────

    /**
     * Copy the read-only Secret URL to the system clipboard and briefly show
     * a ✓ confirmation indicator on the copy button.
     */
    copySecretUrl() {
        const url = this.uiState.secretUrl || '';
        if (!url) return;
        navigator.clipboard.writeText(url).then(() => {
            this.uiState.secretUrlCopied = true;
            setTimeout(() => { this.uiState.secretUrlCopied = false; }, 1800);
        });
    }

    /**
     * Ask the user to confirm, then call the regenerate RPC endpoint to issue
     * a new secret token.  The old Secret URL stops working immediately.
     *
     * Confirmation is handled via a native browser ``window.confirm()`` dialog
     * so no additional Odoo dialog dependency is required.
     */
    async regenerateSecretUrl() {
        const confirmed = window.confirm(
            'Regenerating will permanently invalidate the current Secret URL.\n' +
            'Any external systems using it must be updated to the new URL.\n\n' +
            'Continue?'
        );
        if (!confirmed) return;

        const nodeId = this.props.id || this.props.nodeId;
        if (!nodeId) {
            console.warn('WebhookNode.regenerateSecretUrl: no nodeId available.');
            return;
        }

        this.uiState.regenerating = true;
        try {
            const result = await this.env.services.rpc(
                '/cyllo_workflow/regenerate_webhook_token',
                { node_struct_id: nodeId }
            );
            if (result && result.ok && result.url) {
                this.uiState.secretUrl = result.url;
                this.fieldState.webhook_secret_token = result.token || '';
            } else {
                console.error('WebhookNode: regenerate failed:', result && result.error);
            }
        } catch (err) {
            console.error('WebhookNode: regenerate RPC error:', err);
        } finally {
            this.uiState.regenerating = false;
        }
    }

    // ── Header key/value builder ─────────────────────────────────────────
    /**
     * Parse the raw JSON header string into [{key, value}] rows for the
     * visual builder. If parsing fails, returns empty rows — the raw
     * string in fieldState is always preserved as-is.
     */
    _parseHeadersToRows(raw) {
        try {
            const obj = JSON.parse(raw || '{}');
            return Object.entries(obj).map(([key, value]) => ({ key, value }));
        } catch {
            return [];
        }
    }

    /**
     * Serialise the header rows back into a JSON string and write it
     * into fieldState.webhook_headers — the same field generateCode()
     * already reads. No new field, no schema change.
     */
    _syncHeadersToFieldState() {
        const obj = {};
        for (const row of this.uiState.headerRows) {
            if (row.key.trim()) obj[row.key.trim()] = row.value;
        }
        this.fieldState.webhook_headers = JSON.stringify(obj, null, 2);
    }

    toggleHeaderBuilder() {
        this.uiState.headerBuilderOpen = !this.uiState.headerBuilderOpen;
        if (this.uiState.headerBuilderOpen) {
            // Refresh rows from current fieldState each time panel opens
            this.uiState.headerRows = this._parseHeadersToRows(
                this.fieldState.webhook_headers
            );
        }
    }

    addHeaderRow() {
        this.uiState.headerRows = [...this.uiState.headerRows, { key: '', value: '' }];
    }

    removeHeaderRow(idx) {
        this.uiState.headerRows = this.uiState.headerRows.filter((_, i) => i !== idx);
        this._syncHeadersToFieldState();
    }

    onHeaderKeyChange(idx, ev) {
        this.uiState.headerRows[idx].key = ev.target.value;
        this._syncHeadersToFieldState();
    }

    onHeaderValueChange(idx, ev) {
        this.uiState.headerRows[idx].value = ev.target.value;
        this._syncHeadersToFieldState();
    }

    /**
     * Tags currently found in the payload JSON.
     */
    get selectedPayloadTags() {
        const payloadStr = this.fieldState.webhook_payload || "";
        let payloadObj = {};
        try {
            payloadObj = JSON.parse(payloadStr);
        } catch(e) {
            return [];
        }
        
        const tags = [];
        for (const [key, value] of Object.entries(payloadObj)) {
            tags.push({ label: key, token: value, key: key, isCustom: true });
        }
        return tags;
    }

    /**
     * Remove a tag from the payload JSON.
     */
    removePayloadTag(key) {
        let currentText = (this.fieldState.webhook_payload || '').trim();
        try {
            let payloadObj = JSON.parse(currentText);
            if (payloadObj.hasOwnProperty(key)) {
                delete payloadObj[key];
                this.fieldState.webhook_payload = JSON.stringify(payloadObj, null, 2);
            }
        } catch(e) {
            const escaped = key.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
            const regex = new RegExp(`.*"${escaped}".*\\n?`, 'g');
            this.fieldState.webhook_payload = currentText.replace(regex, '').trim();
        }
    }

    /**
     * Add a custom key/value pair to the payload JSON.
     */
    addCustomPayload() {
        const key = (this.uiState.customPayloadKey || '').trim();
        const value = (this.uiState.customPayloadValue || '').trim();
        if (!key) return;
        
        this._injectToPayload(key, value);
        
        this.uiState.customPayloadKey = '';
        this.uiState.customPayloadValue = '';
    }

    updatePayloadFieldPath(path) {
        this.uiState.payloadFieldPath = path;
    }

    addFieldPathToPayload() {
        if (!this.uiState.payloadFieldPath) return;
        const path = this.uiState.payloadFieldPath;
        const key = path.replace(/\./g, '_');
        const token = `{{current_record.${path}}}`;
        this._injectToPayload(key, token);
        this.uiState.payloadFieldPath = '';
    }

    /**
     * Helper to safely append a key/value to the JSON payload.
     */
    _injectToPayload(key, value) {
        let payloadObj = null;
        let currentText = (this.fieldState.webhook_payload || '').trim();
        
        if (currentText) {
            try {
                payloadObj = JSON.parse(currentText);
            } catch (e) {
                // Not valid JSON
            }
        } else {
            payloadObj = {};
        }
        
        if (payloadObj !== null && typeof payloadObj === 'object' && !Array.isArray(payloadObj)) {
            // Try to parse number or boolean if value is not a token and looks like one
            if (!value.includes('{{') && !isNaN(value) && value !== '') {
                payloadObj[key] = Number(value);
            } else if (value === 'true') {
                payloadObj[key] = true;
            } else if (value === 'false') {
                payloadObj[key] = false;
            } else {
                try {
                    if (/^\s*[{[]/.test(value)) {
                        payloadObj[key] = JSON.parse(value);
                    } else {
                        payloadObj[key] = value;
                    }
                } catch(e) {
                    payloadObj[key] = value;
                }
            }
            this.fieldState.webhook_payload = JSON.stringify(payloadObj, null, 2);
        } else {
            // String append fallback if they typed invalid JSON
            if (currentText && !currentText.endsWith('\n')) {
                currentText += '\n';
            }
            let safeValue = value.replace(/"/g, '\\"');
            this.fieldState.webhook_payload = currentText + `"${key}": "${safeValue}"`;
        }
    }

    // ════════════════════════════════════════════════════════════════════════
    // RESPONSE ACTIONS PANEL
    // Stores configuration in fieldState.webhook_actions (JSON array).
    // generateCode() serialises it into the emitted Python so the backend
    // WebhookResponseProcessor can execute it without any hardcoded logic.
    // ════════════════════════════════════════════════════════════════════════

    get actionTypeOptions() {
        return [
            { value: 'chatter_link',    label: '💬 Post Link in Chatter' },
            { value: 'chatter_message', label: '📝 Post Message in Chatter' },
            { value: 'write_field',     label: '✏️ Write to Record Field' },
            { value: 'send_email',      label: '📧 Send Email Notification' },
            { value: 'redirect_url',    label: '🔗 Redirect User to URL' },
            { value: 'store_variable',  label: '📦 Store in Variable' },
            { value: 'log_info',        label: '🪵 Log to Server Log' },
        ];
    }

    get responseActions() {
        return Array.isArray(this.fieldState.webhook_actions)
            ? this.fieldState.webhook_actions
            : [];
    }

    /** Human-readable label for a saved action type. */
    actionTypeLabel(type) {
        const opt = this.actionTypeOptions.find(o => o.value === type);
        return opt ? opt.label : type;
    }

    /** Brief summary shown in the saved-action chip. */
    actionSummary(action) {
        const parts = [];
        if (action.extract_path) parts.push(`path: ${action.extract_path}`);
        if (action.field_to_write) parts.push(`→ ${action.field_to_write}`);
        if (action.variable_name) parts.push(`var: ${action.variable_name}`);
        if (action.label) parts.push(`"${action.label}"`);
        return parts.join(' · ') || '(no details)';
    }

    toggleResponseActions() {
        this.uiState.responseActionsOpen = !this.uiState.responseActionsOpen;
    }

    openAddActionForm() {
        this.uiState.showAddActionForm = true;
        this.uiState.editingActionIndex = null;
        this.uiState.newActionExtractPath = '';
        this.uiState.newActionType = 'chatter_link';
        this.uiState.newActionLabel = '';
        this.uiState.newActionFieldToWrite = '';
        this.uiState.newActionVariableName = '';
        this.uiState.newActionEmailRecipients = '';
        this.uiState.newActionTarget = 'new';
    }

    editResponseAction(index) {
        const act = this.responseActions[index];
        if (!act) return;
        this.uiState.showAddActionForm = true;
        this.uiState.editingActionIndex = index;
        this.uiState.newActionExtractPath = act.extract_path || '';
        this.uiState.newActionType = act.action_type || 'chatter_link';
        this.uiState.newActionLabel = act.label || '';
        this.uiState.newActionFieldToWrite = act.field_to_write || '';
        this.uiState.newActionVariableName = act.variable_name || '';
        this.uiState.newActionEmailRecipients = act.email_recipients || '';
        this.uiState.newActionTarget = act.target || 'new';
    }

    cancelAddAction() {
        this.uiState.showAddActionForm = false;
        this.uiState.editingActionIndex = null;
    }

    saveResponseAction() {
        const path = (this.uiState.newActionExtractPath || '').trim();
        const type = (this.uiState.newActionType || '').trim();
        if (!type) return;

        const entry = { action_type: type };
        if (path) entry.extract_path = path;
        if (this.uiState.newActionLabel.trim())
            entry.label = this.uiState.newActionLabel.trim();
        if (type === 'write_field' && this.uiState.newActionFieldToWrite.trim())
            entry.field_to_write = this.uiState.newActionFieldToWrite.trim();
        if (type === 'store_variable' && this.uiState.newActionVariableName.trim())
            entry.variable_name = this.uiState.newActionVariableName.trim();
        if (type === 'send_email' && this.uiState.newActionEmailRecipients.trim())
            entry.email_recipients = this.uiState.newActionEmailRecipients.trim();
        if (type === 'redirect_url')
            entry.target = this.uiState.newActionTarget || 'new';

        const current = [...this.responseActions];
        if (this.uiState.editingActionIndex !== null) {
            current[this.uiState.editingActionIndex] = entry;
        } else {
            current.push(entry);
        }
        
        this.fieldState.webhook_actions = current;
        this.uiState.showAddActionForm = false;
        this.uiState.editingActionIndex = null;
    }

    removeResponseAction(index) {
        const updated = this.responseActions.filter((_, i) => i !== index);
        this.fieldState.webhook_actions = updated;
    }

    moveActionUp(index) {
        if (index === 0) return;
        const arr = [...this.responseActions];
        [arr[index - 1], arr[index]] = [arr[index], arr[index - 1]];
        this.fieldState.webhook_actions = arr;
    }

    moveActionDown(index) {
        const arr = [...this.responseActions];
        if (index >= arr.length - 1) return;
        [arr[index], arr[index + 1]] = [arr[index + 1], arr[index]];
        this.fieldState.webhook_actions = arr;
    }
    /**
     * Returns only the store_variable actions from webhook_actions.
     * Used by the XML template to render the "Variables Created" panel.
     */
    get storeVariableActions() {
        const actions = Array.isArray(this.fieldState.webhook_actions)
            ? this.fieldState.webhook_actions : [];
        return actions.filter(a => a && a.action_type === 'store_variable' && a.variable_name);
    }

    /**
     * Returns a formatted summary string for an action (used in the list).
     * Extended to include the variable name prominently for store_variable.
     */
    actionSummaryExtended(act) {
        if (!act) return '';
        const path = act.extract_path ? `from: ${act.extract_path}` : '';
        if (act.action_type === 'store_variable') {
            return `${act.variable_name || '(unnamed)'}  ${path}`;
        }
        return this.actionSummary ? this.actionSummary(act) : path;
    }

}

WebhookNode.template = "WebhookNode";
WebhookNode.components = {
    ...ConfigurationBase.components,
    ModelFieldSelector
};
