/** @odoo-module **/
import {_t} from "@web/core/l10n/translation";
import {ListController} from "@web/views/list/list_controller";
import {patch} from "@web/core/utils/patch";
import {View} from "@web/views/view";
import {useBus, useService} from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const {Component, reactive, useState, useRef, useSubEnv, xml} = owl;

class SplitFormHost extends Component {
    static template = xml`<View t-props="props.viewProps"/>`;
    static components = {View};
    static props = ["viewProps"];
    setup() {
        let displayName;
        const breadcrumbs = reactive([{ get name() { return displayName; } }]);
        useSubEnv({
            config: {
                ...this.env.config,
                breadcrumbs,
                getDisplayName: () => displayName,
                setDisplayName: (newDisplayName) => {
                    displayName = newDisplayName;
                    breadcrumbs.push(undefined);
                    breadcrumbs.pop();
                },
                viewSwitcherEntries: [],
            },
        });
    }
}

patch(ListController.prototype, {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.user = useService('user');
        this.is_split_view = null
        this.spil = useState({
            split_view_enable: false
        })
        this.state = useState({
            currentSelectedId: false
        })
        this.splitViewForm = useRef('split-form-parent')
        useBus(this.env.bus, "split_view_selected_model", this.selected_split_model);
        useBus(this.env.bus, "remove_split_view_selected_model", this.unselect_split_model);
        useBus(this.env.bus, "update_current_selected_id", this.updateCurrentSelectedId);
    },

    async selected_split_model() {
        await this.orm.call('ir.model', "add_split_view", [this.model.env.searchModel.resModel])
    },

    async unselect_split_model() {
        await this.orm.call('ir.model', "remove_split_view", [this.model.env.searchModel.resModel])
    },

    get SpiltFormView() {
        this.props.display.controlPanel = true;
        return {
            type: "form",
            mode: "edit",
            resModel: this.props.resModel,
            resId: this.state.currentSelectedId,
            loadActionMenus: true,
            context: this.props.context,
        }
    },

    set SpiltFormView(value) {
        return value
    },

    async openRecord(record) {
        this.is_split_view = await this.orm.call("ir.model", "get_split_view_mode", [this.model.env.searchModel.resModel]);
        if (this.is_split_view[0].list_split_view) {
            if (this.state.currentSelectedId != record.resId) {
                this.state.currentSelectedId = record.resId;
                this.rootRef.el.querySelector('.o_content').style.display = 'flex';
                const purchaseDashboardElement = this.rootRef.el.querySelector('.o_purchase_dashboard');
                if (purchaseDashboardElement) {
                    purchaseDashboardElement.style.display = 'none';
                }
                const expenseDashboardElement = this.rootRef.el.querySelector('.o_expense_container');
                if (expenseDashboardElement) {
                    expenseDashboardElement.style.display = 'none';
                    expenseDashboardElement.classList.add('expense_hidden');
                }
                const listRendererElement = this.rootRef.el.querySelector('.o_list_renderer');
                if (listRendererElement) {
                    listRendererElement.style.flex = '1 1 0';
                    listRendererElement.style.width = 'auto';
                    listRendererElement.style.maxWidth = 'none';
                    listRendererElement.style.overflowX = 'auto';
                    listRendererElement.classList.remove('col-6');
                }
                this.env.bus.trigger('split_view_record_clicked');
            }
        } else {
            super.openRecord(record);
        }
    },

    closeSplit(ev) {
        this.env.bus.trigger('split_view_close_clicked');
        this.state.currentSelectedId = false
        if (this.rootRef.el.querySelector('.o_content').style.display === 'flex') {
            this.rootRef.el.querySelector('.o_content').style.display = ''
        }
        const purchaseDashboardElement = this.rootRef.el.querySelector('.o_purchase_dashboard');
        if (purchaseDashboardElement) {
            purchaseDashboardElement.style.display = '';
        }
        const expenseDashboardElement = this.rootRef.el.querySelector('.o_expense_container');
        if (expenseDashboardElement) {
            expenseDashboardElement.style.display = '';
            expenseDashboardElement.classList.remove('expense_hidden');
        }
        const listRendererElement = this.rootRef.el.querySelector('.o_list_renderer');
        if (listRendererElement) {
            listRendererElement.style.flex = '';
            listRendererElement.style.width = '';
            listRendererElement.style.maxWidth = '';
            listRendererElement.style.overflowX = '';
            listRendererElement.classList.remove('col-6');
        }
    },

    updateCurrentSelectedId() {
        this.state.currentSelectedId = false
    },

    getStaticActionMenuItems() {
        const list = this.model.root;
        const isM2MGrouped = list.groupBy.some((groupBy) => {
            const fieldName = groupBy.split(":")[0];
            return list.fields[fieldName].type === "many2many";
        });
        return {
            export: {
                isAvailable: () => this.isExportEnable,
                sequence: 10,
                icon: "ri-upload-2-line",
                description: _t("Export"),
                callback: () => this.onExportData(),
            },
            archive: {
                isAvailable: () => this.archiveEnabled && !isM2MGrouped && this.user.isAdmin,
                sequence: 20,
                icon: "ri-archive-line",
                description: _t("Archive"),
                callback: () => {
                    this.dialogService.add(ConfirmationDialog, this.archiveDialogProps);
                },
            },
            unarchive: {
                isAvailable: () => this.archiveEnabled && !isM2MGrouped && this.user.isAdmin,
                sequence: 30,
                icon: "ri-inbox-unarchive-line",
                description: _t("Unarchive"),
                callback: () => this.toggleArchiveState(false),
            },
            duplicate: {
                isAvailable: () => this.activeActions.duplicate && !isM2MGrouped,
                sequence: 35,
                icon: "ri-file-copy-line",
                description: _t("Duplicate"),
                callback: () => this.duplicateRecords(),
            },
            delete: {
                isAvailable: () => this.activeActions.delete && !isM2MGrouped,
                sequence: 40,
                icon: "ri-delete-bin-line",
                description: _t("Delete"),
                callback: () => this.onDeleteSelectedRecords(),
            },
        };
    }
})
ListController.components = {...ListController.components, View, SplitFormHost}