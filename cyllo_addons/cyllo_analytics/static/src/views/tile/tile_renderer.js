/* @odoo-module */
import { Component, useEffect, useState } from "@odoo/owl";
import { TileCard } from "./components/tile_card";
import { useService } from "@web/core/utils/hooks";
import { useSaveContext } from "@cyllo_analytics/js/useSaveContext";


export class TileRenderer extends Component {
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
        useEffect(() => {
            this.state.records = this.props.list.records
        }, () => [this.props.list])
    }
    async onDelete(props) {
        for (const record of props){
            await this._onDelete(record)
        }
        this.action.doAction("soft_reload")
    }
    async _onDelete(prop) {
        const { value: { _config, evalContext } } = prop;
        const { resModel, resId } = _config;
        const value = this.actionContext.getKeyValue("cy_analytic_dashboard")
        if (resModel === "dashboard.config" && value?.id && value.id === resId) {
            this.actionContext.removeManually("cy_analytic_dashboard")
        }
        await this.orm.unlink(resModel, [resId], {
            context: evalContext.context
        })
    }
}
// Template for TileRenderer component
TileRenderer.template = `cyllo_analytics.TileRenderer`;
// Components used within TileRenderer
TileRenderer.components = {
    TileCard
};