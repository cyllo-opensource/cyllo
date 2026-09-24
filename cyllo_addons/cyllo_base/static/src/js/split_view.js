/** @odoo-module **/
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { registry } from "@web/core/registry";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { CogMenuItem } from "@cyllo_base/js/cog_menu_item";
const { Component, onMounted, useRef } = owl;

const cogMenuRegistry = registry.category("cogMenu");

class SplitView extends Component {
    static template = "cyllo_split_view.SplitView";
    static components = { DropdownItem, CogMenuItem };
    setup() {
        this.orm = useService('orm');
        this.splitIconRef = useRef('splitIcon');
        this.viewId = this.env.config.viewId;
        this.viewType = this.env.config.viewType;
        if (this.viewId !== undefined && this.viewType === 'list') {
            this.lastViewId = browser.localStorage.getItem('last_view_id');
            if (String(this.lastViewId) !== String(this.viewId)) {
                this.isSplitView = browser.localStorage.getItem(`is_split_view_${this.viewId}`) === 'true';
                this.isSplitView = false;
                browser.localStorage.setItem(`is_split_view_${this.env.config.viewId}`, this.isSplitView.toString());
            }
            else {
                this.isSplitView = browser.localStorage.getItem(`is_split_view_${this.viewId}`) === 'true';
            }
            browser.localStorage.setItem('last_view_id', this.viewId);
        }
        onMounted(async () => {
            if (this.isSplitView) {
                const pagerSplitElement = this.splitIconRef.el;
                pagerSplitElement.parentElement.classList.add('clicked-split');
                pagerSplitElement.classList.add('split_icon');
            }
            if (this.isSplitView === false) {
                const modelName = this.env.searchModel?.resModel || this.env.config?.resModel || (window.location.href.includes('#') ? new URLSearchParams(window.location.href.split('#')[1]).get('model') : null);
                if (modelName) {
                    await this.orm.call("ir.model", "remove_split_view", [modelName]);
                }
            }
        })
    }

    on_click_SplitView(ev) {
        if (!this.isSplitView) {
            this.env.bus.trigger('split_view_selected_model');
            if (ev.target.children.length === 0) {
                ev.target.parentElement.classList.add("clicked-split");
                ev.target.classList.add("split_icon");
            }
            else {
                ev.target.classList.add("clicked-split");
                ev.target.children.split_tree_view?.classList.add("split_icon");
            }
            this.isSplitView = true;
        } else {
            this.env.bus.trigger('remove_split_view_selected_model');
            if (ev.target.children.length === 0) {
                ev.target.parentElement.classList.remove("clicked-split");
                ev.target.classList.remove("split_icon");
            }
            else {
                ev.target.classList.remove("clicked-split");
                ev.target.children.split_tree_view?.classList.remove("split_icon");
            }
            this.isSplitView = false;
            this.env.bus.trigger('split_view_close_clicked');
            this.env.bus.trigger('update_current_selected_id');
            if (this.splitIconRef.el.offsetParent.querySelector('.o_content')?.style.display === 'flex') {
                this.splitIconRef.el.offsetParent.querySelector('.o_content').style.display = ''
            }
            const purchaseDashboardElement = this.splitIconRef.el.offsetParent.querySelector('.o_purchase_dashboard');
            if (purchaseDashboardElement) {
                purchaseDashboardElement.style.display = '';
            }
            const expenseDashboardElement = this.splitIconRef.el.offsetParent?.querySelector('.o_expense_container');
            if (expenseDashboardElement) {
                expenseDashboardElement.style.display = '';
                expenseDashboardElement.classList.remove('expense_hidden');
            }
        }
        browser.localStorage.setItem(`is_split_view_${this.env.config.viewId}`, this.isSplitView.toString());
    }
}
export const SplitViewItem = {
    Component: SplitView,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: async (env) => env.config.viewType === "list"
};
cogMenuRegistry.add("splitview-menu", SplitViewItem, { sequence: 11 });