/** @odoo-module **/

import {
    leafToString,
    useLoadDisplayNames,
    extractIdsFromTree,
    getPathsInTree,
    getResModel,
} from "@web/core/tree_editor/utils";
import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import {
    condition,
    cloneTree,
    formatValue,
    removeVirtualOperators,
    connector,
} from "./custom_search_condition_tree";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Input, Select } from "@web/core/tree_editor/tree_editor_components";
import {
    getDefaultValue,
    getValueEditorInfo,
} from "@web/core/tree_editor/tree_editor_value_editors";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";
import { deepEqual, shallowEqual } from "@web/core/utils/objects";
import { filterVariable } from "../../Assists/utils/utils";
import {RecordPathSelector} from "../../Assists/recordPathSelector/recordPathSelector";
import {VariableSelector} from "../../Assists/variableSelector/variableSelector";
import { FieldTypeDropdown } from "../../Assists/fieldTypeDropdown/fieldTypeDropDown";

const TRUE_TREE = condition(1, "=", 1);

const DEFAULT_CONDITION = condition("id", "=", 1);

function collectDifferences(tree, otherTree) {
    // some differences shadow the other differences "below":
    if (tree.type !== otherTree.type) {
        return [{ type: "other" }];
    }
    if (tree.negate !== otherTree.negate) {
        return [{ type: "other" }];
    }
    if (tree.type === "condition") {
        if (formatValue(tree.path) !== formatValue(otherTree.path)) {
            return [{ type: "other" }];
        }
        if (formatValue(tree.value) !== formatValue(otherTree.value)) {
            return [{ type: "other" }];
        }
        if (formatValue(tree.operator) !== formatValue(otherTree.operator)) {
            if (tree.operator === "!=" && otherTree.operator === "set") {
                return [{ type: "replacement", tree, operator: "set" }];
            } else if (tree.operator === "=" && otherTree.operator === "not_set") {
                return [{ type: "replacement", tree, operator: "not_set" }];
            } else {
                return [{ type: "other" }];
            }
        }
        return [];
    }
    if (tree.value !== otherTree.value) {
        return [{ type: "other" }];
    }
    if (tree.type === "complex_condition") {
        return [];
    }
    if (tree.children.length !== otherTree.children.length) {
        return [{ type: "other" }];
    }
    const diffs = [];
    for (let i = 0; i < tree.children.length; i++) {
        const child = tree.children[i];
        const otherChild = otherTree.children[i];
        const childDiffs = collectDifferences(child, otherChild);
        if (childDiffs.some((d) => d.type !== "replacement")) {
            return [{ type: "other" }];
        }
        diffs.push(...childDiffs);
    }
    return diffs;
}

function restoreVirtualOperators(tree, otherTree) {
    const diffs = collectDifferences(tree, otherTree);
    // note that the array diffs is homogeneous:
    // we have diffs of the form [], [other], [repl, ..., repl]
    if (diffs.some((d) => d.type !== "replacement")) {
        return;
    }
    for (const { tree, operator } of diffs) {
        tree.operator = operator;
    }
}

export class CustomSearchTreeEditor extends Component {
    static template = "cyllo_workflow_automation.CustomSearchTreeEditor";
    static components = {
        Dropdown,
        DropdownItem,
        ModelFieldSelector,
        CheckBox,
        FieldTypeDropdown
    };
    static props ={
        tree: Object,
        variables: Object,
        resModel: String,
        update: Function,
        getPathEditorInfo: Function,
        getOperatorEditorInfo: Function,
        getDefaultOperator: Function,
        readonly: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        isDebugMode: { type: Boolean, optional: true },
        defaultConnector: { type: [{ value: "&" }, { value: "|" }], optional: true },
        defaultCondition: { type: Object, optional: true },
    };
    static defaultProps = {
        defaultConnector: "&",
        defaultCondition: DEFAULT_CONDITION,
        readonly: false,
    };

    setup() {
        this.loadFieldInfo = useLoadFieldInfo();
        this.loadDisplayNames = useLoadDisplayNames();
        onWillStart(() => this.onPropsUpdated(this.props));
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps));
    }

    async onPropsUpdated(props) {
        this.tree = cloneTree(props.tree);
        if (shallowEqual(this.tree, TRUE_TREE)) {
            this.tree = connector(props.defaultConnector);
        } else if (this.tree.type !== "connector") {
            this.tree = connector(props.defaultConnector, [this.tree]);
        }
        if (this.previousTree) {
            // find "first" difference
            restoreVirtualOperators(this.tree, this.previousTree);
            this.previousTree = null;
        }
        const paths = getPathsInTree(this.tree);
        await this.loadFieldDefs(props.resModel, paths);
        if (props.readonly) {
            const idsByModel = extractIdsFromTree(this.tree, this.getFieldDef.bind(this));
            this.displayNames = await this.loadDisplayNames(idsByModel);
        }
    }

    get className() {
        return `${this.props.readonly ? "o_read_mode" : "o_edit_mode"}`;
    }

    get isDebugMode() {
        return this.props.isDebugMode !== undefined ? this.props.isDebugMode : !!this.env.debug;
    }
    getFieldDef(path) {
        if (typeof path === "string") {
            return this.fieldDefs[path];
        }
        return null;
    }

    async loadFieldDefs(resModel, paths) {
        const promises = [];
        const fieldDefs = {};
        for (const path of paths) {
            if (typeof path === "string") {
                promises.push(
                    this.loadFieldInfo(resModel, path).then(({ fieldDef }) => {
                        fieldDefs[path] = fieldDef;
                    })
                );
            }
        }
        await Promise.all(promises);
        this.fieldDefs = fieldDefs;
    }

    notifyChanges() {
        this.previousTree = cloneTree(this.tree);
        this.props.update(this.tree);
    }

    updateConnector(node, value) {
        node.value = value;
        node.negate = false;
        this.notifyChanges();
    }

    updateComplexCondition(node, value) {
        node.value = value;
        this.notifyChanges();
    }

    createNewLeaf() {
        return cloneTree(this.props.defaultCondition);
    }

    createNewBranch(value) {
        return connector(value, [this.createNewLeaf(), this.createNewLeaf()]);
    }

    insertRootLeaf(parent) {
        parent.children.push(this.createNewLeaf());
        this.notifyChanges();
    }

    insertLeaf(parent, node) {
        const newNode = node.type !== "connector" ? cloneTree(node) : this.createNewLeaf();
        const index = parent.children.indexOf(node);
        parent.children.splice(index + 1, 0, newNode);
        this.notifyChanges();
    }

    insertBranch(parent, node) {
        const nextConnector = parent.value === "&" ? "|" : "&";
        const newNode = this.createNewBranch(nextConnector);
        const index = parent.children.indexOf(node);
        parent.children.splice(index + 1, 0, newNode);
        this.notifyChanges();
    }

    delete(parent, node) {
        const index = parent.children.indexOf(node);
        parent.children.splice(index, 1);
        this.notifyChanges();
    }

    getDescription(node) {
        const fieldDef = this.getFieldDef(node.path);
        return leafToString(node, fieldDef, this.displayNames[getResModel(fieldDef)]);
    }

    reverseParser(parsedString) {
      const [variableName, pathPart] = parsedString.split('.');

      return {
        record: this.props.variables.find(item => item.variable_name === variableName).id,
        path: pathPart,
        pathValue: pathPart
      };
    }


    getValueEditorInfo(node) {
        const fieldDef = this.getFieldDef(node.path);
        const editorValue = getValueEditorInfo(fieldDef, node.operator);

        if(["set", "not_set"].includes(node.operator)) {
            return editorValue;
        }
        // const fl_variables = filterVariable(this.props.variables, fieldDef.type)
        if (node.selectionType === "variable") {
            // let variables = fl_variables.map(variable => ["v_" + variable.variable_name, variable.variable_name])
            return {
                component: VariableSelector,
                extractProps: ({value, update}) => {
                    return {
                        value,
                        update,
                        fieldDef,
                        variables: this.props.variables,
                        operator: node.operator
                    }
                },
                isSupported: () => true,
            }
        } else if (node.selectionType === "record") {
            return {
                component: RecordPathSelector,
                extractProps: ({value, update}) => {
                    return {
                        value,
                        update,
                        operator: node.operator,
                        variables: (this.props.variables || []).filter(variable => variable.variable_type === "record"),
                        fieldInfo: { fieldDef, resModel: this.props.resModel },
                    }
                },
                isSupported: () => true,
            }
        }
        return editorValue
    }

    async updatePath(node, path) {
        const { fieldDef } = await this.loadFieldInfo(this.props.resModel, path);
        node.path = path;
        node.negate = false;
        node.operator = this.props.getDefaultOperator(fieldDef);
        node.value = this.getDefaultNodeValue(node, fieldDef, node.operator);
        this.notifyChanges();
    }

    updateLeafOperator(node, operator, negate) {
        const previousNode = cloneTree(node);
        const fieldDef = this.getFieldDef(node.path);
        node.negate = negate;
        node.operator = operator;
        node.value = this.getDefaultNodeValue(node, fieldDef, operator, node.value);
        if (deepEqual(removeVirtualOperators(node), removeVirtualOperators(previousNode))) {
            // no interesting changes for parent
            // this means that parent might not render the domain selector
            // but we need to udpate edgetDefaultValueitors
            this.render();
        }
        this.notifyChanges();
    }

    updateLeafValue(node, value) {
        node.value = value;
        this.notifyChanges();
    }

    highlightNode(target) {
        const nodeEl = target.closest(".o_tree_editor_node");
        nodeEl.classList.toggle("o_hovered_button");
    }

    getDefaultNodeValue(node, fieldDef, operator, currentValue = undefined) {
        if (node.selectionType === "variable") {
            return {
                selectedVariable: currentValue?.selectedVariable || false,
                pathValue: currentValue?.pathValue || false,
                isVariable: true,
            };
        }
        if (node.selectionType === "record") {
            return {
                record: currentValue?.record || false,
                path: currentValue?.path || "",
                pathValue: currentValue?.pathValue || false,
            };
        }
        return getDefaultValue(fieldDef, operator, currentValue);
    }

    toggleIncludeVariable(value,node) {
        const fieldDef = this.getFieldDef(node.path);
        node.selectionType = value;
        node.value = this.getDefaultNodeValue(node, fieldDef, node.operator, node.value);
        this.notifyChanges();
    }

    getDropdownLabel(selectionType) {
        const labels = {
            static: 'Fixed',
            variable: 'Variable',
            record: 'Record',
        };
        return labels[selectionType] || 'Fixed';
    }
}
