/* @odoo-module */
import { TreeEditor } from "@web/core/tree_editor/tree_editor";
import {
    getValueEditorInfo,
} from "@web/core/tree_editor/tree_editor_value_editors";
import { Select } from "@web/core/tree_editor/tree_editor_components";
import { _t } from "@web/core/l10n/translation";

// Period options shown in the value dropdown when "in period" operator is selected
const PERIOD_OPTIONS = [
    ["this_week", "This Week"],
    ["last_week", "Last Week"],
    ["this_month", "This Month"],
    ["last_month", "Last Month"],
    ["this_quarter", "This Quarter"],
    ["last_quarter", "Last Quarter"],
    ["this_year", "This Year"],
    ["last_year", "Last Year"],
];

export class SheetTreeEditor extends TreeEditor {
    static template = "cyllo_analytics.TreeEditor"

    /**
     * Override: for "in_period" operator, show a Select dropdown with period options.
     * For "between", the base class already handles it with a Range component.
     */
    getValueEditorInfo(node) {
        if (node.operator === "in_period") {
            return {
                component: Select,
                extractProps: ({ value, update }) => ({
                    value: value || "this_month",
                    update,
                    options: PERIOD_OPTIONS.map(([v, l]) => [v, _t(l)]),
                }),
                defaultValue: () => "this_month",
                isSupported: (value) => typeof value === "string",
                message: "",
                stringify: (value) => {
                    const opt = PERIOD_OPTIONS.find(([v]) => v === value);
                    return opt ? _t(opt[1]) : String(value);
                },
            };
        }
        return super.getValueEditorInfo(node);
    }
}
SheetTreeEditor.props = {
    ...SheetTreeEditor.props,
    modelName: { type: String, optional: true },
}
SheetTreeEditor.defaultProps = {
    ...SheetTreeEditor.defaultProps,
    modelName: "",
}