/* @odoo-module */
import {Component, useEffect, useState} from "@odoo/owl";
import {WorkflowCard} from "./components/workflow_card";
import {useService} from "@web/core/utils/hooks";
import {useSaveContext} from "@cyllo_workflow_automation/js/useSaveContext";
import {KanbanHeader} from "@web/views/kanban/kanban_header";
import {KanbanRenderer} from "@web/views/kanban/kanban_renderer";
import {evaluateBooleanExpr} from "@web/core/py_js/py";
import {isRelational} from "@web/model/relational_model/utils";
import {isNull} from "@web/views/utils";
import {_t} from "@web/core/l10n/translation";

export class WorkflowCardRenderer extends Component {
    // This is the class for the TileRenderer component
    setup() {
        // Component state to manage records
        this.state = useState({
            records: this.props.list.records,
        })
        this.orm = useService('orm')
        this.action = useService('action')
        this.actionContext = useSaveContext()
        // Effect to update records when the list changes
    }

    getWorkRecords() {
        const {list} = this.props
        if (list.isGrouped) {
            return [...list.groups].map((group, i) => {
                return {
                    group,
                    key: isNull(group.value) ? `group_key_${i}` : String(group.value),
                };
            })
        }
        return list.records
    }

    _getEmptyGroupLabel(fieldName) {
        return _t("None");
    }

    get groupName() {
        const {groupByField, displayName} = this.group;
        let name = displayName;
        if (groupByField.type === "boolean") {
            name = name ? _t("Yes") : _t("No");
        } else if (!name) {
            if (
                isRelational(groupByField) ||
                groupByField.type === "date" ||
                groupByField.type === "datetime" ||
                isNull(name)
            ) {
                name = this._getEmptyGroupLabel(groupByField.name);
            }
        }
        return name;
    }

    groupRecords(group) {
        const fieldName = this.props.list._config.groupBy[0]
        if (group.displayName || this.groupName === 'Yes') {
            return this.state.records.filter((item) => {
                if (typeof item.data[this.props.list._config.groupBy] === 'object') {
                    return item.data[this.props.list._config.groupBy?.[0]]?.[1] === group.displayName
                }
                return item.data[this.props.list._config.groupBy] === group.displayName
            })
        }
        return this.state.records.filter((item) => item.data[this.props.list._config.groupBy?.[0]] === false)
    }

    async deleteGroup(group) {
        await this.props.list.deleteGroups([group]);
        if (this.props.list.groups.length === 0) {
        }
    }

    async onDelete(props) {
        for (const record of props) {
            await this._onDelete(record)
        }
        this.action.doAction("soft_reload")
    }
    async _onDelete(prop) {
    }
    onClickCreate(){
        this.env.bus.trigger('CREATE-FLOW-RECORD')
    }
}

// Template for TileRenderer component
WorkflowCardRenderer.template = `cyllo_workflow_automation.WorkflowCardRenderer`;
// Components used within TileRenderer
WorkflowCardRenderer.components = {
    WorkflowCard
};