/** @odoo-module **/
import { Component, useState, useRef, onWillStart } from "@odoo/owl";
import { Layout } from "@web/search/layout";
import { useModelWithSampleData } from "@web/model/model";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { ViewButton } from "@web/views/view_button/view_button";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { session } from "@web/session";
import { useBus, useService } from "@web/core/utils/hooks";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { useSetupView } from "@web/views/view_hook";
import { DynamicRecordList } from "@web/model/relational_model/dynamic_record_list";
export class GridController extends Component {
    static components = {
        Layout,
        Dropdown,
        DropdownItem,
        ViewButton,
        CogMenu,
        SearchBar,
    };
    async setup() {
        this.dialogService = useService("dialog");
        this.router = useService("router");
        this.orm = useService("orm");
        this.user = useService("user");
        this.viewService = useService("view");
        this.dataSearch = []
        this.ui = useService("ui");
        this.currentDate = new Date();
        onWillStart(async () => {
            const { domain, resModel } = this.props
            let date = new Date();
            var formattedDate = date.toISOString().split('T')[0];
            domain.push(['date', '=', formattedDate])
            var result = await this.orm.searchRead(resModel, domain, ["id"])
            this.limit = result.length

        })
        useBus(this.ui.bus, "resize", this.render);
        this.archInfo = this.props.archInfo;
        const fields = this.props.fields;
        this.rootRef = useRef('root')
        this.model = useState(useModelWithSampleData(this.props.Model, this.modelParams));
        this.searchBarToggler = useSearchBarToggler();
        useSetupView({
            rootRef: this.rootRef,
            beforeLeave: async () => {
                return this.model.root.leaveEditMode();
            },
            beforeUnload: async (ev) => {
                const editedRecord = this.model.root.editedRecord;
                if (editedRecord) {
                    const isValid = await editedRecord.urgentSave();
                    if (!isValid) {
                        ev.preventDefault();
                        ev.returnValue = "Unsaved changes";
                    }
                }
            },
            getLocalState: () => {
                const renderer = this.rootRef.el.querySelector(".o_grid_renderer");
                return {
                    modelState: this.model.exportState(),
                    rendererScrollPositions: {
                        left: renderer.scrollLeft,
                        top: renderer.scrollTop,
                    },
                };
            },
            getOrderBy: () => {
                return this.model.root.orderBy;
            },
        });
    }
     async createRecord({ group } = {}) {
        const grid = (group && group.grid) || this.model.root;
        if (this.editable && !grid.isGrouped) {
            if (!(grid instanceof DynamicRecordList)) {
                throw new Error("Grid should be a DynamicRecordList");
            }
            await grid.leaveEditMode();
            if (!grid.editedRecord) {
                await (group || grid).addNewRecord(this.editable === "top");
            }
            this.render();
        } else {
            await this.props.createRecord();
        }
    }
    get renderProps() {
        return {
            ...this.props,
            onPagerUpdate: this.onPagerUpdate.bind(this)
        }
    }
    async onPagerUpdate (domain) {
        var { globalDomain: domain } = this.env.searchModel
        await this.model.root.load({ domain })
    }
    get modelParams() {
        const { defaultGroupBy } = this.archInfo;
        const { activeFields, fields } = extractFieldsFromArchInfo(
            this.archInfo,
            this.props.fields
        );
        const groupByInfo = {};
        for (const fieldName in this.archInfo.groupBy.fields) {
            const fieldNodes = this.archInfo.groupBy.fields[fieldName].fieldNodes;
            const fields = this.archInfo.groupBy.fields[fieldName].fields;
            groupByInfo[fieldName] = extractFieldsFromArchInfo({ fieldNodes }, fields);
        }
        const modelConfig = this.props.state?.modelState?.config || {
            resModel: this.props.resModel,
            fields,
            activeFields,
            openGroupsByDefault: true,
        };
        return {
            config: modelConfig,
            state: this.props.state?.modelState,
            groupByInfo,
            limit: null,
            countLimit: this.archInfo.countLimit,
            defaultOrderBy: this.archInfo.defaultOrder,
            defaultGroupBy: this.props.searchMenuTypes.includes("groupBy") ? defaultGroupBy : false,
            groupsLimit: this.archInfo.groupsLimit,
            multiEdit: this.archInfo.multiEdit,
            activeIdsLimit: session.active_ids_limit,
        };
    }
    GridView() {
        return {
            type: this.archInfo.multiType,
            resModel: this.props.resModel,
            context: this.props.context,
            data : this.dataSearch
        };
    }
}
GridController.template = "grid_view.GridView";