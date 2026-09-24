/** @odoo-module */
const { useState, onWillStart } = owl;
import { _t } from "@web/core/l10n/translation";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { ConfigurationBase } from "../configurationBase/configurationBase";
import { CustomDropdown } from "../Assists/dropdown/CustomDropdown";
import { CustomTreeEditor } from "../writeNode/subComponents/customTreeEditor";

export class DuplicateNode extends ConfigurationBase {
    static props = ['*'];

    setup() {
        super.setup();
        this.state = useState({
            tree: [],
            model: null,
            modelId: null,
        });
        onWillStart(async () => {
            await this.loadModelFromRecord();
            this.loadTreeFromFieldState();
        });
    }

    // ── Label ────────────────────────────────────────────────────────────

    get getLabel() {
        return this.fieldState.label || "";
    }

    setLabel(label) {
        this.fieldState.label = label;
        const nodeId = this.props.id;
        this.env.bus.trigger("CHANGE-LABEL", { label, nodeId });
    }

    // ── Record selector ──────────────────────────────────────────────────

    get getRecords() {
        return this.variables
            .filter(v => ['record', 'recordset'].includes(v.variable_type) && v.modelId)
            .map(v => ({ value: v.id, label: v.variable_name }));
    }

    get getSelectedRecordValue() {
        return this.fieldState.duplicate_record
            ? (typeof this.fieldState.duplicate_record === 'object'
                ? this.fieldState.duplicate_record.value
                : this.fieldState.duplicate_record)
            : null;
    }

    async updateObject(recordVarId) {
        this.fieldState.duplicate_record = this.getRecords.find(r => r.value === recordVarId) || null;
        // Reset tree when record changes
        this.state.tree = [];
        this.fieldState.duplicate_field_overrides = '[]';
        await this.loadModelFromRecord();
    }

    // ── Model resolution (mirrors WriteNode.settingModel) ────────────────

    async loadModelFromRecord() {
        const raw = this.fieldState.duplicate_record;
        const varId = raw && typeof raw === 'object' ? raw.value : raw;
        const variable = this.variables.find(v => v.id === varId);
        if (variable?.modelId) {
            const [{ model, id }] = await this.orm.read('ir.model', [variable.modelId], ['model']);
            this.state.model = model;
            this.state.modelId = id;
        } else {
            this.state.model = null;
            this.state.modelId = null;
        }
    }

    // ── Field overrides tree (mirrors WriteNode pattern) ─────────────────

    loadTreeFromFieldState() {
        const raw = this.fieldState.duplicate_field_overrides;
        if (raw && raw !== '[]') {
            try {
                this.state.tree = JSON.parse(raw);
            } catch (e) {
                this.state.tree = [];
            }
        }
    }

    filterFields(defs) {
        // Exclude id and non-stored (computed) fields — same as WriteNode
        if (defs.name === 'id') return false;
        return !!defs.store;
    }

    getPathEditorInfo() {
        const resModel = this.state.model;
        const isDebugMode = true;
        return {
            component: ModelFieldSelector,
            extractProps: ({ update, value: path }) => ({
                path,
                update,
                resModel,
                isDebugMode,
                filter: this.filterFields.bind(this),
                readonly: false,
                followRelations: false,
            }),
            isSupported: (path) => [0, 1].includes(path) || typeof path === 'string',
            defaultValue: () => 'id',
        };
    }

    settingFieldState(tree) {
        this.fieldState.duplicate_field_overrides = JSON.stringify([...tree]);
    }

    createNewNode() {
        this.state.tree = [
            ...this.state.tree,
            { id: Date.now(), path: '', value: '', type: 'char' },
        ];
    }

    nodeUpdate(prevNode, node) {
        const tree = this.state.tree.filter(i => i.path !== node.path);
        const idx = tree.findIndex(i => i.path === prevNode.path);
        if (idx !== -1) {
            tree.splice(idx, 1, owl.reactive(node));
            this.state.tree = tree;
            this.settingFieldState(tree);
        }
    }

    nodeValueUpdate(prevNode, node) {
        const idx = this.state.tree.findIndex(i => i.path === prevNode.path);
        if (idx !== -1) {
            this.state.tree.splice(idx, 1, owl.reactive(node));
            this.settingFieldState(this.state.tree);
        }
    }

    deleteNode(node) {
        const filtered = this.state.tree.filter(i => i.id !== node.id);
        this.state.tree = filtered;
        this.settingFieldState(filtered);
    }

    // ── Code generation ──────────────────────────────────────────────────

    generateCode() {
        const { duplicate_record, duplicate_field_overrides, duplicate_result_variable } = this.fieldState;

        const raw = duplicate_record;
        const varId = raw && typeof raw === 'object' ? raw.value : raw;
        const record = this.variables.find(v => v.id === varId);
        if (!record) return '';

        const varName = record.variable_name;
        const varType = record.variable_type;
        const resultVar = (duplicate_result_variable || '').trim() || null;

        // Build the default={} overrides dict from the tree editor
        let overrides = {};
        const rawOverrides = duplicate_field_overrides;
        if (rawOverrides && rawOverrides !== '[]') {
            try {
                const tree = JSON.parse(rawOverrides);
                tree.forEach(val => {
                    if (val.path) {
                        overrides[val.path] = this.processValue(val);
                    }
                });
            } catch (e) {
                // malformed JSON — use empty overrides
            }
        }
        // Serialise overrides and unescape var_ prefix (same pattern as WriteNode)
        const overridesStr = JSON.stringify(overrides).replace(/"var_([^"]*)"/g, '$1');

        if (varType === 'record') {
            const copyLine = `_dup = ${varName}.copy(default=${overridesStr})`;
            const assignLine = resultVar ? `\n${resultVar} = _dup` : '';
            return `${copyLine}${assignLine}`;
        }

        if (varType === 'recordset') {
            const initLine = `_dup_records = ${varName}.env[${varName}._name].browse([])`;
            const forLine = `for rec in ${varName}:\n\t_copy = rec.copy(default=${overridesStr})\n\t_dup_records |= _copy`;
            const assignLine = resultVar ? `\n${resultVar} = _dup_records` : '';
            return `${initLine}\n${forLine}${assignLine}`;
        }

        return '';
    }

    // ── Validation ───────────────────────────────────────────────────────

    validateForm() {
        const { duplicate_record, label } = this.fieldState;
        const errors = {};

        if (!label) {
            errors.label = _t("Label must not be empty.");
        }

        const varId = duplicate_record && typeof duplicate_record === 'object'
            ? duplicate_record.value
            : duplicate_record;
        if (!varId) {
            errors.duplicate_record = _t("Select a record to duplicate.");
        }

        return Object.keys(errors).length
            ? { isValid: false, errors }
            : { isValid: true };
    }
}

DuplicateNode.template = "DuplicateNode";
DuplicateNode.components = {
    ...ConfigurationBase.components,
    CustomDropdown,
    CustomTreeEditor,
};
