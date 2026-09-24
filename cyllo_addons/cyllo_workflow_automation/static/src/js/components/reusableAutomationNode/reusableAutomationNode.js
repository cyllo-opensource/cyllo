/** @odoo-module **/
import { useState } from "@odoo/owl";
import { ConfigurationBase } from "../configurationBase/configurationBase";
import { CustomDropdown } from "../Assists/dropdown/CustomDropdown";

export class ReusableAutomationNode extends ConfigurationBase {
    setup() {
        super.setup();
        this.state = useState({
            automationOptions: [],
            // metadata keyed by automation id — stores label, model, isGeneric,
            // AND the automation's own triggerType (list of trigger_type strings).
            // This is the critical piece: when we call _process() on the reused
            // automation, we must pass ITS trigger_type(s), not the calling
            // workflow's trigger_type. Otherwise the generated code guard
            // `if trigger_type == 'create':` will never match when called from
            // an On Write workflow.
            automationMetadata: {},
        });
    }

    async fetchData() {
        await super.fetchData();
        await this.loadAutomations();
        this.syncNodeLabelFromSelection();
    }

    async loadAutomations() {
        // Base filters: active + marked reusable.
        // NOTE: we intentionally drop the ['trigger_function_ids', '!=', false]
        // filter here so that generic reusables (no trigger nodes, no
        // trigger_function_ids) also appear in the list.
        const baseDomain = [
            ['active', '=', true],
            ['is_reusable', '=', true],
            ['is_editable_copy', '=', false],
        ];
        if (this.props.work_auto_id) {
            baseDomain.push(['id', '!=', this.props.work_auto_id]);
        }

        const allRecords = await this.orm.searchRead(
            'work.auto',
            [...baseDomain, ['reuse_scope', '=', 'generic']],
            ['id', 'name', 'model_id', 'reuse_scope', 'trigger_type']
        );

        const options = allRecords.map(rec => {
            const modelName = rec.model_id?.[1] || '';
            return {
                value: rec.id,
                label: `[Generic] ${rec.name}`,
                model: modelName,
                isGeneric: true,
                // Store the automation's primary trigger_type (e.g. 'create',
                // 'write', 'unlink', 'time', 'field_change', or '' for generic).
                triggerType: rec.trigger_type || '',
            };
        });

        const metadata = {};
        options.forEach(option => { metadata[option.value] = option; });
        this.state.automationOptions = options;
        this.state.automationMetadata = metadata;
    }

    get automationDropdownOptions() {
        return this.state.automationOptions;
    }

    get selectedAutomationModel() {
        const metadata = this.state.automationMetadata[this.fieldState.reused_work_auto_id];
        if (!metadata) return '';
        if (metadata.isGeneric) return 'Generic (any model)';
        return metadata.model || '';
    }

    get selectedAutomationTriggerType() {
        const metadata = this.state.automationMetadata[this.fieldState.reused_work_auto_id];
        return metadata?.triggerType || '';
    }

    getReusableNodeLabel(metadata) {
        if (!metadata) {
            return "Reuse Automation Rule";
        }
        return metadata.label;
    }

    syncNodeLabelFromSelection() {
        const metadata = this.state.automationMetadata[this.fieldState.reused_work_auto_id];
        if (metadata) {
            this.setLabel(this.getReusableNodeLabel(metadata));
        }
    }

    get recordVariableOptions() {
        return this.variables
            .filter(variable => ['record', 'recordset'].includes(variable.variable_type))
            .map(variable => ({
                value: variable.id,
                label: `${variable.variable_name} (${variable.variable_type})`,
                variable,
            }));
    }

    onSelectAutomation(value) {
        // Store as integer so generateCode() and node.struct write receive a clean id.
        this.fieldState.reused_work_auto_id = value ? parseInt(value, 10) : null;
        const metadata = this.state.automationMetadata[value];
        if (metadata) {
            this.setLabel(this.getReusableNodeLabel(metadata));
        }
    }

    onSelectVariable(value) {
        const option = this.recordVariableOptions.find(opt => opt.value === value);
        if (option) {
            this.fieldState.reused_variable = option.variable;
            this.updateUsedVariables(option.variable.id);
        } else {
            this.fieldState.reused_variable = null;
        }
    }

    setLabel(value) {
        this.fieldState.label = value;
        this.env.bus.trigger("CHANGE-LABEL", { label: value, nodeId: this.props.id });
    }

    async rewriteAutomationFlow() {
        if (!this.fieldState.reused_work_auto_id || !this.props.onEditReusableFlow) {
            return;
        }
        await this.props.onEditReusableFlow();
        this.props.close();
    }

    generateCode() {
        // Coerce to integer — CustomDropdown may return a number or a string.
        const rawId = this.fieldState.reused_work_auto_id;
        const automationId = rawId ? parseInt(rawId, 10) : null;
        const variable = this.fieldState.reused_variable;
        if (!automationId || isNaN(automationId)) {
            return "";
        }

        this.props.updateImports({
            parent: 'import logging\n_logger = logging.getLogger(__name__)',
            child: '',
            nodeId: this.props.id,
        });

        const parentId = Number(this.props.work_auto_id || 0);
        const stackLines = parentId > 0 ? [`    cy_w_stack.append(${parentId})`] : [];

        // Use the selected variable as the record source, or fall back to
        // current_record (always available from the calling workflow's context).
        const recordsExpr = variable ? this.getRecordsExpression(variable) : 'current_record';

        // ── KEY FIX ──────────────────────────────────────────────────────────
        // The reused automation's generated Python code wraps its logic in a
        // trigger-type guard:
        //
        //   if trigger_type == 'create':   # Workflow A's guard
        //       schedule_activity(...)
        //
        // If we naively pass the CALLING workflow's trigger_type (e.g. 'write'
        // from Workflow B), the guard in Workflow A evaluates to False and
        // nothing runs — the automation silently does nothing.
        //
        // Fix: pass the REUSED automation's OWN trigger_type as a literal
        // string so its internal guard always matches.
        //
        // For generic reusables (reuse_scope='generic'), trigger_type is ''
        // and their code is generated WITHOUT a trigger guard, so we pass
        // the special sentinel '__reuse__'. The backend _process() will detect
        // this and execute the code unconditionally (no guard to match).
        // ─────────────────────────────────────────────────────────────────────
        const reusedTriggerType = this.selectedAutomationTriggerType;

        // If the reused automation has a known trigger type, pass it as a
        // literal. If it has none (generic reusable), pass the special sentinel
        // '__reuse__' so the backend knows to skip any trigger guard.
        const triggerTypeLiteral = reusedTriggerType
            ? `'${reusedTriggerType}'`
            : `'__reuse__'`;

        const lines = [
            'try:',
            '    cy_w_stack = list(__workflow_stack__)',
            ...stackLines,
            `    env["work.auto"].browse(${automationId})._process({`,
            `        'records': ${recordsExpr},`,
            `        '__workflow_stack__': cy_w_stack,`,
            // Pass the reused automation's OWN trigger_type so its internal
            // `if trigger_type == '...'` guard evaluates correctly.
            `        'trigger_type': ${triggerTypeLiteral},`,
            // Signal to the backend that this is a reuse call — the backend
            // uses this to skip dedup and resolve the correct model context.
            `        '__is_reuse_call__': True,`,
            '    })',
            'except Exception as e:',
            `    _logger.error("Reusable automation ${automationId} failed: %s", e)`,
            '    raise'
        ];
        return lines.join('\n');
    }

    getRecordsExpression(variable) {
        if (variable.variable_type === 'recordset') {
            return variable.variable_name;
        }
        const modelName = variable.modelName || this.props.primary_model_name;
        if (modelName) {
            return `env['${modelName}'].browse(${variable.variable_name}.id)`;
        }
        return variable.variable_name;
    }
}

ReusableAutomationNode.components = {
    ...ConfigurationBase.components,
    CustomDropdown,
};
ReusableAutomationNode.template = "ReusableAutomationNode";
