/* @odoo-module */
import { DomainSelector } from "@web/core/domain_selector/domain_selector";
import { SheetTreeEditor } from "./tree_editor";
import { getOperatorEditorInfo } from "@web/core/tree_editor/tree_editor_operator_editor";
import { getDomainDisplayedOperators } from "./getDomainDisplayedOperators";
import { condition } from "@web/core/tree_editor/condition_tree";

export const ALLOWED_FIELD_TYPES = [
    'many2one',
    'boolean',
    'selection',
    'char',
    'text',
    'html',
    'date',
    'datetime',
    'integer',
    'float',
    'monetary',
]

// Human-readable labels for the custom operators
const CUSTOM_OPERATOR_LABELS = {
    "in_period": "in period",
    "between": "between",
};

export class SheetDomainSelector extends DomainSelector {
    static template = "SheetDomainSelector"

    setup() {
        super.setup();
        this.domainDefaultCondition = condition("id", "in", [])
    }

    getPathEditorInfo() {
        const { resModel, isDebugMode } = this.props;
        const res = super.getPathEditorInfo(...arguments);
        return {
            ...res,
            extractProps: ({ update, value: path }) => {
                return {
                    path,
                    update,
                    resModel,
                    isDebugMode,
                    readonly: false,
                    followRelations: false,
                    filter: (fieldDef) => {
                        return ALLOWED_FIELD_TYPES.includes(fieldDef.type) && fieldDef.store
                    }
                };
            },
        };
    }

    getOperatorEditorInfo(node) {
        const fieldDef = this.getFieldDef(node.path);
        const operators = getDomainDisplayedOperators(fieldDef);

        // Build the standard info from Odoo's core
        const baseInfo = getOperatorEditorInfo(operators);

        // Extend with custom period operators
        const origExtractProps = baseInfo.extractProps;
        baseInfo.extractProps = ({ update, value }) => {
            const props = origExtractProps({ update, value });
            // Add custom labels to the options list
            props.options = props.options.map(([key, label]) => {
                // Direct match (e.g. "between")
                if (key in CUSTOM_OPERATOR_LABELS) {
                    return [key, CUSTOM_OPERATOR_LABELS[key]];
                }
                // JSON-encoded key (e.g. '["\"in_period\"",false]')
                try {
                    const parsed = JSON.parse(key);
                    if (Array.isArray(parsed)) {
                        let op = typeof parsed[0] === 'string' ? parsed[0] : String(parsed[0]);
                        // Remove potential extra quotes from formatValue
                        op = op.replace(/^"(.*)"$/, '$1');
                        if (op in CUSTOM_OPERATOR_LABELS) {
                            return [key, CUSTOM_OPERATOR_LABELS[op]];
                        }
                    }
                } catch (_) { }
                return [key, label];
            });
            return props;
        };

        // Extend isSupported to recognize custom operators
        const origIsSupported = baseInfo.isSupported;
        baseInfo.isSupported = (value) => {
            const [operator] = value;
            if (typeof operator === "string" && operator in CUSTOM_OPERATOR_LABELS) {
                return true;
            }
            return origIsSupported(value);
        };

        // Extend stringify for custom operators
        const origStringify = baseInfo.stringify;
        baseInfo.stringify = (value) => {
            const [operator] = value;
            if (typeof operator === "string" && operator in CUSTOM_OPERATOR_LABELS) {
                return CUSTOM_OPERATOR_LABELS[operator];
            }
            return origStringify ? origStringify(value) : undefined;
        };

        return baseInfo;
    }
}

SheetDomainSelector.components = {
    ...SheetDomainSelector.components,
    SheetTreeEditor,
}

SheetDomainSelector.props = {
    ...SheetDomainSelector.props,
    modelName: { type: String, optional: true },
    handleDeleteDomain: { type: Function, optional: true },
}
SheetDomainSelector.defaultProps = {
    ...SheetDomainSelector.defaultProps,
    modelName: "",
    handleDeleteDomain: () => {
    },
}