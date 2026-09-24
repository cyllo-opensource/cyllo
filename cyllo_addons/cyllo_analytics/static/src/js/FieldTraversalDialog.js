/** @odoo-module **/
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
const { Component, useState, onWillStart } = owl;

export class FieldTraversalDialog extends Component {
    /** Dialog to select a field from a related model with traversal support */
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            stack: [],
            path: [],
            search: '',
            selectedField: null,
            loading: false,
        });
        this.modelCache = {};

        onWillStart(async () => {
            this.rootModel = await this._loadModelById(this.props.model_id);
            if (this.rootModel) {
                this.state.stack.push(this.rootModel);
            }
        });
    }

    async _getModelInfo(modelName) {
        if (this.modelCache[modelName]) {
            return this.modelCache[modelName];
        }
        const model = await this.orm.searchRead('ir.model', [['model', '=', modelName]], ['id', 'name', 'model']);
        if (!model.length) {
            return false;
        }
        const modelData = await this.orm.call("dashboard.sheet", "get_data", [model[0].id]);
        const info = this._normalizeModelData(modelData);
        this.modelCache[modelName] = info;
        return info;
    }

    async _loadModelById(modelId) {
        const modelData = await this.orm.call("dashboard.sheet", "get_data", [modelId]);
        const info = this._normalizeModelData(modelData);
        this.modelCache[info.model] = info;
        return info;
    }

    _normalizeModelData(modelData) {
        const fields = Object.values(modelData.fields)
            .filter(f => {
                // 1. Basic exclusions
                if (!f.store || ['one2many', 'many2many'].includes(f.type)) return false;

                // 2. Always keep relational fields for navigation
                if (f.type === 'many2one' && !!f.relation) return true;

                // 3. Filter based on targetType (dimension vs measure)
                const isNumeric = ['float', 'integer', 'monetary'].includes(f.type);
                if (this.props.targetType === 'dimension') {
                    return !isNumeric || f.name === 'id';
                } else if (this.props.targetType === 'measure') {
                    return isNumeric;
                }
                return true;
            })
            .map(f => ({
                name: f.name,
                label: f.string,
                type: f.type,
                relation: f.relation,
                is_json: f.type === 'char' && f.translate ? true : false,
                table: modelData.table,
                model: modelData.model,
                modelName: modelData.name,
                modelId: modelData.id,
                is_relational: f.type === 'many2one' && !!f.relation,
            }));
        return {
            id: modelData.id,
            name: modelData.name,
            model: modelData.model,
            table: modelData.table,
            fields,
        };
    }

    get currentLevel() {
        return this.state.stack[this.state.stack.length - 1];
    }

    get filteredFields() {
        if (!this.currentLevel) return [];
        const fields = this.currentLevel.fields || [];
        if (!this.state.search) return fields;
        const search = this.state.search.toLowerCase();
        return fields.filter(f =>
            f.label.toLowerCase().includes(search) || f.name.toLowerCase().includes(search)
        );
    }

    get pathLabel() {
        const crumbs = [this.props.base_label || this.currentLevel?.modelName || ""];
        this.state.path.forEach(item => crumbs.push(item.fieldLabel));
        return crumbs.filter(Boolean).join(" > ");
    }

    onSelect(field) {
        this.state.selectedField = field;
    }

    async onNavigate(field) {
        if (!field.is_relational || !field.relation) return;
        this.state.loading = true;
        const nextModel = await this._getModelInfo(field.relation);
        this.state.loading = false;
        if (!nextModel) return;

        const fromTable = this.currentLevel.table;
        const fromModelName = this.currentLevel.name;
        this.state.path.push({
            fieldName: field.name,
            fieldLabel: field.label,
            fromTable,
            fromModelName,
            toTable: nextModel.table,
            toModelName: nextModel.name,
            toModelId: nextModel.id,
        });
        this.state.stack.push(nextModel);
        this.state.search = '';
        this.state.selectedField = null;
    }

    onBack() {
        if (this.state.stack.length > 1) {
            this.state.stack.pop();
            this.state.path.pop();
            this.state.search = '';
            this.state.selectedField = null;
        }
    }

    confirm() {
        if (this.state.selectedField) {
            this.props.onConfirm({
                field: this.state.selectedField,
                path: this.state.path,
                rootModel: this.rootModel,
            });
            this.props.close();
        }
    }
}

FieldTraversalDialog.template = "FieldTraversalDialog";
FieldTraversalDialog.components = { Dialog };
