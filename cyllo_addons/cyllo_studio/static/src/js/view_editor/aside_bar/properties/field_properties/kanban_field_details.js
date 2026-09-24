/** @odoo-module **/

import {
    Component, onWillUpdateProps, useState, onWillStart
} from "@odoo/owl";
import {
    CylloStudioDropdown
} from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import {
    registry
} from "@web/core/registry";
import {
    useService,
    useOwnedDialogs
} from "@web/core/utils/hooks";
import {
    ExpressionEditorDialog
} from "@web/core/expression_editor_dialog/expression_editor_dialog";


export class KanbanFieldProperties extends Component {
    static template = "cyllo_studio.KanbanFieldProperties";

    setup() {
        this.rpc = useService("rpc");
        this.actionService = useService("action");
        this.action = useService("action");
        this.orm = useService("orm");
        this.addDialog = useOwnedDialogs();
        this.state = useState({
            widget: this.props.widget || '',
            path: this.props.path,
            fieldInvisible: this.props.invisible || false,
            widget_value: this.props.widget ? this.props.widget : false,
            defaultWidgets: []

        });
        onWillUpdateProps(async (nextProps) => {
            if (this.state.path !== nextProps.path) {
                this.state.widget = nextProps.widget
                this.state.path = nextProps.path
                this.state.fieldInvisible = nextProps.invisible || false;
            }
        });
        onWillStart(async () => {
            await this.defaultWidgets()
        })
    }

    undoOperation(response) {
        let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
        let cleanedStr = response.replace(/\s+/g, ' ').trim();
        storedArray.push(cleanedStr);
        sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
        sessionStorage.setItem('ReDO', JSON.stringify([]));
    }

    handleInvisibleChange(event) {
        this.state.fieldInvisible = event.target.checked ? 'True' : 'False';
        this.autoSave();
    }
    async attrDomain(ev) {
        const parent = ev.target.closest('.cy-basedOn');
        var attribute = parent.getAttribute('data-attribute');
        var domain = '';
        if (attribute === 'invisible' && (this.state.fieldInvisible || this.props.invisible)) {
            const raw = this.state.fieldInvisible || this.props.invisible;
            domain = (raw === true || raw === 1) ? 'True' : (raw === false || raw === 0 || raw === null) ? 'False' : String(raw);
        } else {
            domain = false;
        }
        var resModel = this.action.currentController.props.resModel;
        domain = domain ? domain : "False";

        this.addDialog(ExpressionEditorDialog, {
            resModel,
            fields: this.props.allFields,
            expression: domain,
            onConfirm: (expression) => this.modifier(expression, attribute),
        });
    }
    modifier(expression, attribute) {
        this.attribute = attribute;
        if (attribute === 'invisible') {
            this.state.fieldInvisible = expression;
        }
        this.autoSave();
    }
    async defaultWidgets() {
        this.state.defaultWidgets = await this.orm.searchRead("default.widgets", [])
    }

    get defaultWidget() {
        const widget = this.props.widget ? this.props.widget : this.state.widget_value
        return widget
    }

    get widgets() {
        let widgets = [];
        let hasWidget = false;
        let type =
            this.props.allFields[this.props.name].type === "image" ?
                "binary" :
                this.props.allFields[this.props.name].type;
        let widget_params = {
            name: this.defaultWidget,
            field: this.props.name,
            model: this.props.model,
            view_id: this.props.view_id,
            defaultWidgets: this.state.defaultWidgets,
        }
        const val = registry.category("cyllo_studio_widget_list").get("widget_list")
        const values = val(widget_params)
        if (values.defaultWidget) {
            this.orm.create('default.widgets', [values.defaultWidget])
        }
        this.content = values.widgets
        Object.entries(this.content).forEach(
            ([key, value]) => {
                if (key.includes(".") && key.split(".")[0] !== 'kanban') {
                    return;
                }

                if (
                    value[1].supportedTypes !== undefined &&
                    value[1].supportedTypes.includes(type)
                ) {

                    if (key === this.state.widget) {
                        hasWidget = true;
                    }
                    widgets.push({
                        value: key,
                        label: `${value[1].displayName || ""} (${key.split(".").pop()})`,
                    });
                }
            }
        );
        if (!hasWidget && this.state.widget && this.state.widget !== 'False') {
            widgets.push({ value: this.state.widget, label: `(${this.state.widget})` })
        }
        return [{ value: false, label: '(None)' }, ...widgets];
    }
    handleWidget(value) {
        this.state.widget_value = value;
        this.autoSave();
    }

    autoSave() {
        if (this._autoSaving) { this._autoSavePending = true; return; }
        this._autoSaving = true;
        this.updateKanban().finally(() => {
            this._autoSaving = false;
            if (this._autoSavePending) { this._autoSavePending = false; this.autoSave(); }
        });
    }
    async updateKanban() {
        const args = {
            model: this.props.viewDetails.model,
            view_id: this.props.viewDetails.viewId,
            view_type: this.props.viewDetails.viewType,
            path: this.props.path,
            widget: this.state.widget_value || this.state.widget || '',
            invisible: this.state.fieldInvisible,
            active_fields: this.props.activeFields,
            remove_widget: this.state.widget_value === false || this.state.widget_value === '',
        }
        const response = await this.rpc("cyllo_studio/kanban/update/field", { args });
        if (response) {
            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
            let cleanedStr = response.replace(/\s+/g, ' ').trim();
            storedArray.push(cleanedStr);
            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
            sessionStorage.setItem('ReDO', JSON.stringify([]));
        }

        this.env.bus.trigger('resetProperties');
        this.action.doAction('studio_reload');

    }
    async RemoveField() {
        const path = this.props.path
        const regex = /field(\[\d+\])?$/;
        let isChildField = false;
        const childNames = [];
        const element = this.props.element
        for (let i = 0; i < element?.children.length; i++) {
            const childPath = element.children[i].getAttribute('cy-xpath');
            const childName = element.children[i].getAttribute('name');
            if (regex.test(childPath)) {
                isChildField = true;
            }
            if (childName) {
                childNames.push(childName);
            }
        }
        const fieldName = this.props.name
        const isField = regex.test(path);
        let field = ""
        if (isField) {
            const fieldNodes = this.props.fieldNodes;
            const nameExists = Object.keys(fieldNodes).filter(element => element.startsWith(fieldName));
            let isPathIncluded = nameExists.some(name => fieldNodes[name].MainPath.includes('/kanban/field'));
            field = isPathIncluded ? "" : fieldName
        }
        let childField = ""
        if (isChildField) {
            const fieldNodes = this.props.fieldNodes;
            const nameExists = Object.keys(fieldNodes).filter(element => element.startsWith(childNames));
            let isPathIncluded = nameExists.some(name => fieldNodes[name].MainPath.includes('/kanban/field'));
            childField = isPathIncluded ? "" : childNames
        }
        const response = await this.rpc("cyllo_studio/delete/kanban/field", {
            model: this.props.viewDetails.model,
            view_id: this.props.viewDetails.viewId,
            view_type: this.props.viewDetails.viewType,
            path: this.props.path,
            field_name: field,
            child_field_name: childField,
        });
        if (response) {
            this.undoOperation(response)
        }
        this.env.bus.trigger("CLEAR-MENU");
        this.action.doAction('studio_reload');
    }

}
KanbanFieldProperties.components = {
    CylloStudioDropdown
}