/** @odoo-module **/
/**
 * Cyllo Studio Control Panel Patch
 *
 * Extends Odoo's ControlPanel component to add custom Studio features:
 * 1. Maintains Kanban scale in sessionStorage and triggers scale changes via the event bus.
 * 2. Detects when editing `ir.model.access` or `ir.rule` and triggers a `studio_editable_list` event.
 * 3. Emits the active views and current view type when ControlPanel is mounted.
 * 4. Handles cleanup on unmounting by resetting `studio_editable_list`.
 * 5. Adds a custom Kanban preview event handler.
 * 6. Extends default ControlPanel components to include Pager.
 *
 * Props:
 * - type: Optional string to identify the panel type.
 * - isSearchView: Optional boolean to indicate if it’s in search view mode.
 */
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from '@web/core/utils/patch';
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { Pager } from "@web/core/pager/pager";
import { onMounted, onWillUnmount, useState, useEffect } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useOwnedDialogs } from "@web/core/utils/hooks";
import { ReportCreationDialog } from "./report_creation_dialog";


patch(ControlPanel.prototype, {
    setup() {
        super.setup()
        this.state = useState({
            ...this.state,
            scale: sessionStorage.getItem('kanbanScale') || '100%',
        })
        this.addDialog = useOwnedDialogs();

        onMounted(() => {
            if (this.env?.searchModel?.resModel === 'ir.model.access' || this.env?.searchModel?.resModel === 'ir.rule') {
                this.env.bus.trigger('studio_editable_list', true);
            }
            if (this.env?.config.views) {
                this.env.bus.trigger("ACTIVE-VIEWS", {
                    views: this.env.config.views,
                    viewType: this.env.config.viewType
                });
            }
        })

        onWillUnmount(() => {
            if (this.env?.searchModel?.resModel === 'ir.model.access' || this.env?.searchModel?.resModel === 'ir.rule') {
                this.env.bus.trigger('studio_editable_list', false);
            }
        })

        useEffect(() => {
            sessionStorage.setItem('kanbanScale', this.state.scale)
            this.env.bus.trigger("KanbanScale", { scale: this.state.scale })
        }, () => [this.state.scale])
    },
    /**
     * Trigger Kanban preview event.
     */
    handleKanbanPreview() {
        this.env.bus.trigger("KanbanPreview")
    },
    /**
     * Open the Report Creation Dialog.
     */
    handleCreateNewReport() {
        this.addDialog(ReportCreationDialog, {});
    },
    get shouldShowPager() {
        const hasValidPagerProps = this.pagerProps &&
            typeof this.pagerProps.offset === 'number' &&
            typeof this.pagerProps.limit === 'number' &&
            typeof this.pagerProps.onUpdate === 'function';

        if (!hasValidPagerProps) {
            return false;
        }

        const isMetaModel = this.env?.searchModel?.resModel === 'ir.model.access' ||
            this.env?.searchModel?.resModel === 'ir.rule' ||
            this.env?.searchModel?.resModel === 'ir.actions.report';

        return (!this.env.config.actionType || isMetaModel) && !this.props.isSearchView;
    }
})
ControlPanel.components = {
    ...ControlPanel.components, Pager
}
ControlPanel.template = "studio.CylloControlPanel"

ControlPanel.props = {
    ...ControlPanel.props,
    type: { type: String, optional: true },
    isSearchView: { type: Boolean, optional: true }
}
