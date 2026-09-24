/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { Layout } from "@web/search/layout";
import { useModelWithSampleData } from "@web/model/model";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { extractFieldsFromArchInfo } from "@web/model/relational_model/utils";

export class MapViewController extends Component {
    setup() {
        this.searchBarToggler = useSearchBarToggler();
        this.archInfo = this.props.archInfo;
        this.state = useState({
            isLayoutChanged: false,
        });
        this.activeActions = this.archInfo.activeActions;
        this.editable = this.activeActions.edit && this.props.editable ? this.archInfo.editable : false;
        this.create = this.activeActions.create
        this.model = useState(useModelWithSampleData(this.props.Model, this.modelParams));
    }
    get modelParams() {
        const { activeFields, fields } = extractFieldsFromArchInfo(
            this.archInfo,
            this.props.fields
        );
        return {
            config: {
                resModel: this.props.resModel,
                fields,
                openGroupsByDefault: true,
                activeFields: activeFields,
            },
            fieldNodes: this.archInfo.fieldNodes,
            handleField: this.archInfo.handleField,
            viewMode: "map_view",
            groupByInfo: this.archInfo.groupBy.fields,
            limit: this.archInfo.limit || this.props.limit,
            countLimit: this.archInfo.countLimit,
            defaultOrder: this.archInfo.defaultOrder,
            defaultGroupBy: this.props.defaultGroupBy,
            rootState: {}
        }
    }
    openRecord(resId) {
        const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
        this.props.selectRecord(resId, {
            activeIds
        })
    }
    get display() {
        const {
            controlPanel
        } = this.props.display;
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
    get nbSelected() {
        return this.model.root.selection.length;
    }
    layoutChanged(val) {
        this.state.isLayoutChanged = val
    }
}
MapViewController.template = 'cyllo_map.MapView'
MapViewController.components = {
    Layout,
    CogMenu,
    SearchBar
}
