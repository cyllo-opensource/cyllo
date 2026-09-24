/** @odoo-module **/

import {useService} from "@web/core/utils/hooks";
import {Layout} from "@web/search/layout";
import {usePager} from "@web/search/pager_hook";
import {useModelWithSampleData} from "@web/model/model";
import {DynamicRecordList} from "@web/model/relational_model/dynamic_record_list";
import {extractFieldsFromArchInfo} from "@web/model/relational_model/utils";
import {standardViewProps} from "@web/views/standard_view_props";
import {useSearchBarToggler} from "@web/search/search_bar/search_bar_toggler";
import {CyCogMenu, CogMenuList} from "@cyllo_base/js/cog_menu_form"; // TODO: Might need to change the path after merging
import {Component, onWillPatch, useRef, useState, useSubEnv, onMounted, onWillStart} from "@odoo/owl";
import {autoflowModal} from "./autoflowModal";
import {SearchBar} from "@web/search/search_bar/search_bar";
import {AutoCardSearchBar} from "./auto_card_searchbar/auto_card_searchbar.xml";


export class WorkflowCardController extends Component {
    /** class for the TileController component **/

    setup() {
        // Services
        this.actionService = useService("action");
        this.userService = useService("user");
        this.rootRef = useRef("root");
        this.action = useService("action");
        this.orm = useService("orm");

        this.dialogService = useService("dialog")
        // Component setup
        this.archInfo = this.props.archInfo;
        this.editable = false;
        this.model = useState(useModelWithSampleData(this.props.Model, this.modelParams));
        this.env.bus.addEventListener("CREATE-FLOW-RECORD", async () => await this.onClickCreate());
        useSubEnv({model: this.model});
        // Pager setup
        usePager(() => {
            const {count, hasLimitedCount, isGrouped, limit, offset} = this.model.root;
            return {
                offset: offset,
                limit: limit,
                total: count,
                onUpdate: async ({offset, limit}, hasNavigated) => {
                    if (this.model.root.editedRecord) {
                        if (!(await this.model.root.editedRecord.save())) {
                            return;
                        }
                    }
                    await this.model.root.load({limit, offset});
                    if (hasNavigated) {
                        this.onPageChangeScroll();
                    }
                },
                updateTotal:
                    !isGrouped && hasLimitedCount ? () => this.model.root.fetchCount() : undefined,
            };
        });
        // useModelWithSampleData
        // Search bar toggler
        this.searchBarToggler = useSearchBarToggler();
        // Flag to track if it's the first load
        this.firstLoad = true;
        onWillPatch(() => {
            this.firstLoad = false;
        });
    }

    // Method to handle import action

    onPageChangeScroll() {
        if (this.rootRef && this.rootRef.el) {
            this.rootRef.el.querySelector(".o_content").scrollTop = 0;
        }
    }

    // Getter for model parameters
    get modelParams() {
        const {activeFields, fields} = extractFieldsFromArchInfo(
            this.archInfo,
            this.props.fields
        );
        const modelConfig = this.props.state?.modelState?.config || {
            resModel: this.props.resModel,
            fields,
            activeFields
        };

        return {
            config: modelConfig,
            state: this.props.state?.modelState,
            limit: this.archInfo.limit || this.props.limit,
            countLimit: this.archInfo.countLimit,
            defaultOrderBy: this.archInfo.defaultOrder,
            groupsLimit: this.archInfo.groupsLimit,
        };
    }

    // Method to create a new record
    async createRecord({group} = {}) {
        const list = (group && group.list) || this.model.root;
        if (this.editable && !list.isGrouped) {
            if (!(list instanceof DynamicRecordList)) {
                throw new Error("Tile should be a DynamicRecordList");
            }
            await list.leaveEditMode();
            if (!list.editedRecord) {
                await (group || list).addNewRecord(this.editable === "top");
            }
            this.render();
        } else {
            await this.props.createRecord();
        }
    }

    // Method to open a record
    async openRecord(record) {
        if (this.archInfo.openAction) {
            this.actionService.doActionButton({
                name: this.archInfo.openAction.action,
                type: this.archInfo.openAction.type,
                resModel: record.resModel,
                resId: record.resId,
                resIds: record.resIds,
                context: record.context,
                onClose: async () => {
                    await record.model.root.load();
                },
            });
        } else {
            const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
            this.props.selectRecord(record.resId, {activeIds});
        }
    }

    // Method to handle create action
    async onClickCreate(e) {
        if (owl.status(this) !== 'destroyed') {
            const rule = await this.orm.create("work.auto", [{'name': 'Automation rule'}])
            this.action.doAction({
                type: "ir.actions.client",
                tag: "automation_view",
                context: {
                    id: rule[0]
                }
            });
        }
    }

    // Getter for the CSS class name
    get className() {
        return this.props.className;
    }

    // Getter for the number of selected items
    get nbSelected() {
        return this.model.root.selection.length;
    }

    // Getter for the display settings
    get display() {
        const {controlPanel} = this.props.display;
        if (!controlPanel) {
            return this.props.display;
        }
        return {
            ...this.props.display,
            controlPanel: {
                ...controlPanel,
                layoutActions: !this.nbSelected,
            },
        };
    }

    // Method to disable buttons
    disableButtons() {
        const btns = [...this.rootRef.el.querySelectorAll("button:not([disabled])")];
        for (const btn of btns) {
            btn.setAttribute("disabled", "1");
        }
        this.disabledButtons = btns;
    }

    // Method to enable buttons
    enableButtons() {
        for (const btn of this.disabledButtons) {
            btn.removeAttribute("disabled");
        }
        this.disabledButtons = null;
    }
}

WorkflowCardController.template = `cyllo_workflow_automation.WorkflowCardController`;
WorkflowCardController.components = {
    Layout,
    CyCogMenu,
    CogMenuList,
    AutoCardSearchBar,
    SearchBar
};
WorkflowCardController.props = {
    ...standardViewProps,
    allowSelectors: {type: Boolean, optional: true},
    editable: {type: Boolean, optional: true},
    onSelectionChanged: {type: Function, optional: true},
    showButtons: {type: Boolean, optional: true},
    Model: Function,
    Renderer: Function,
    archInfo: Object,
};
WorkflowCardController.defaultProps = {
    allowSelectors: true,
    createRecord: () => {
    },
    editable: true,
    selectRecord: () => {
    },
    showButtons: true,
};
