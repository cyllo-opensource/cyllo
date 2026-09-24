/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { Record } from "@web/model/record";
import { CharField } from "@web/views/fields/char/char_field";
import { SelectionField } from "@web/views/fields/selection/selection_field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { ConfigurationBase } from "../configurationBase/configurationBase";
import { CustomSearchDomainSelector } from "../searchNode/subComponents/custom_search_domain_selector.js";
import {
    domainFromTree,
    treeFromDomain,
} from "../searchNode/subComponents/custom_search_condition_tree";
import { Domain } from "@web/core/domain";

const { useState } = owl;

const EMPTY_TREE = { children: [], negate: false, type: "connector", value: "&" };

function cloneTree(tree) {
    return JSON.parse(JSON.stringify(tree));
}

function isValidTree(tree) {
    return (
        tree &&
        typeof tree === "object" &&
        !Array.isArray(tree) &&
        "type" in tree &&
        Array.isArray(tree.children)
    );
}

function safeTreeFromDomain(raw) {
    if (!raw || raw.trim() === "[]") {
        return cloneTree(EMPTY_TREE);
    }
    try {
        const tree = treeFromDomain(raw);
        return isValidTree(tree) ? tree : cloneTree(EMPTY_TREE);
    } catch {
        return cloneTree(EMPTY_TREE);
    }
}

export class WindowNode extends ConfigurationBase {
    static props = ["*"];

    setup() {
        super.setup();
        this.windowState = useState({ resModel: false });
    }

    async fetchData() {
        await super.fetchData();
        const stored = this.fieldState.window_domain_tree;
        if (isValidTree(stored)) {
            // Already a valid tree from DB — use as-is (deep clone for isolation).
            this.fieldState.window_domain_tree = cloneTree(stored);
        } else {
            // Fall back: parse the char domain string (legacy nodes or first open).
            const raw = (this.fieldState.window_domain || "").trim();
            this.fieldState.window_domain_tree = safeTreeFromDomain(raw);
        }
        await this._loadActionModel(this.fieldState.window_action_id);
    }

    async _loadActionModel(actionId) {
        if (!actionId) {
            this.windowState.resModel = false;
            return;
        }
        const id = typeof actionId === "object" ? actionId[0] : actionId;
        const result = await this.orm.read("ir.actions.act_window", [id], ["res_model"]);
        this.windowState.resModel = result[0]?.res_model || false;
    }

    get recordProps() {
        const label = { type: "char", string: "Label" };
        const window_action_id = {
            type: "many2one",
            string: "Window Action",
            relation: "ir.actions.act_window",
        };
        const window_view_type = {
            type: "selection",
            string: "View Type",
            selection: [
                ["list", "List"],
                ["form", "Form"],
                ["kanban", "Kanban"],
                ["calendar", "Calendar"],
                ["pivot", "Pivot"],
                ["graph", "Graph"],
                ["activity", "Activity"],
            ],
        };
        const window_target = {
            type: "selection",
            string: "Target",
            selection: [
                ["current", "Current"],
                ["new", "New Tab / Dialog"],
                ["fullscreen", "Fullscreen"],
                ["inline", "Inline"],
            ],
        };
        const window_context = { type: "char", string: "Context" };

        const fields = {
            label,
            window_action_id,
            window_view_type,
            window_target,
            window_context,
        };

        return {
            mode: "edit",
            onRecordChanged: async (record, changes) => {
                for (const key in changes) {
                    this.fieldState[key] = changes[key];
                }
                if ("window_action_id" in changes) {
                    // Reset tree when action changes — the model may differ.
                    this.fieldState.window_domain_tree = cloneTree(EMPTY_TREE);
                    await this._loadActionModel(changes.window_action_id);
                }
            },
            resModel: "node.struct",
            resId: this.props.id,
            fieldNames: fields,
            activeFields: fields,
        };
    }

    get domainSelectorProps() {
        const tree = isValidTree(this.fieldState.window_domain_tree)
            ? this.fieldState.window_domain_tree
            : cloneTree(EMPTY_TREE);
        return {
            readonly: false,
            isDebugMode: false,
            resModel: this.windowState.resModel,
            tree,
            variables: [],
            update: (updatedTree) => {
                this.fieldState.window_domain_tree = isValidTree(updatedTree)
                    ? cloneTree(updatedTree)
                    : cloneTree(EMPTY_TREE);
            },
        };
    }

    onChangeLabel(label) {
        this.fieldState.label = label;
        this.env.bus.trigger("CHANGE-LABEL", { label, nodeId: this.props.id });
    }

    get contextSuggestionGroups() {
        const resModel = this.windowState?.resModel || "";
        const current = (this.fieldState.window_context || "").trim();

        const recordLinking = [
            "{}",
            "{'active_id': current_record.id}",
            "{'active_ids': [current_record.id]}",
        ];
        if (resModel) {
            recordLinking.push(`{'active_model': '${resModel}', 'active_id': current_record.id}`);
        }

        const defaults = [
            "{'default_FIELD_NAME': current_record.id}",
            "{'default_FIELD_NAME': current_record.name}",
            "{'default_FIELD_NAME': 'VALUE'}",
        ];

        const searchAndFilters = [
            "{'search_default_FILTER_NAME': 1}",
            "{'group_by': ['FIELD_NAME']}",
            "{'search_default_group_by_FIELD_NAME': 1}",
        ];

        const viewBehavior = [
            "{'form_view_initial_mode': 'edit'}",
            "{'create': False}",
            "{'edit': False}",
            "{'delete': False}",
            "{'no_breadcrumbs': True}",
        ];

        const groups = [
            { title: "Record reference", items: recordLinking },
            { title: "Field defaults", items: defaults },
            { title: "Search & filters", items: searchAndFilters },
            { title: "View behavior", items: viewBehavior },
        ];

        return groups
            .map((group) => ({ ...group, items: group.items.filter((s) => s !== current) }))
            .filter((group) => group.items.length > 0);
    }

    selectContextSuggestion(record, value) {
        this.fieldState.window_context = value;
        record.update({ window_context: value });
    }

    _toDomainString() {
        const tree = this.fieldState.window_domain_tree;
        if (!tree || !tree.children || tree.children.length === 0) {
            return "[]";
        }
        try {
            return Domain.and([domainFromTree(tree)]).toString();
        } catch {
            return "[]";
        }
    }

    generateCode() {
        const actionId = this.fieldState.window_action_id;
        if (!actionId) {
            return "";
        }

        this.props.updateImports({
            parent: 'import logging\n_logger = logging.getLogger(__name__)',
            child: '',
            nodeId: this.props.id,
        });

        const id = typeof actionId === "object" ? actionId[0] : actionId;
        const viewType = this.fieldState.window_view_type || "list";
        const target = this.fieldState.window_target || "current";
        const domain = this._toDomainString();
        // Keep the char field in sync so it reflects the visual selection.
        this.fieldState.window_domain = domain;
        const context = (this.fieldState.window_context || "{}").trim() || "{}";

        return `
try:
    action_obj = env["ir.actions.act_window"].browse(${id}).read()[0]
    action_obj["view_mode"] = "${viewType}"
    action_obj["target"] = "${target}"
    action_obj["domain"] = ${domain}
    action_obj["context"] = ${context}
    channel = "bus_do_action"
    message = {
        "auth": {"user": env.user.id},
        "action": action_obj,
        "channel": channel,
    }
    env["bus.bus"]._sendone(channel, "notification", message)
except Exception as e:
    _logger.error("Check Workflow automation rule(ID:${this.props.id}): %s", e)
`;
    }

    validateForm() {
        const errors = {};
        const { label, window_action_id } = this.fieldState;

        if (!label || !label.trim()) {
            errors.label = _t("Label is required.");
        }
        if (!window_action_id) {
            errors.window_action_id = _t("Please select a Window Action.");
        }

        return {
            isValid: Object.keys(errors).length === 0,
            errors,
        };
    }
}

WindowNode.template = "WindowNode";
WindowNode.components = {
    ...ConfigurationBase.components,
    Record,
    CharField,
    SelectionField,
    Many2OneField,
    CustomSearchDomainSelector,
};
