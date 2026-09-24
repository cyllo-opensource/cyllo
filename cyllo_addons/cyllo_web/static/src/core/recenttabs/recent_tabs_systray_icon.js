/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

const MAX_PINNED_TABS = 3;

export class RecentTabsSystrayIcon extends Component {
    static components = { Dropdown, DropdownItem };
    static props = {
        // Set by the systray overflow tray, which renders the item with its label.
        nameShow: { type: Boolean, optional: true },
    };
    static template = "cyllo_web.RecentTabsMenu";

    setup() {
        this.state = useState({
            tabs: [],
            numberOfPinnedTabs: 0,
        });
        this.recentTabsService = useService("recentTabsService");
        this.notification = useService("notification");
        this.orm = useService("orm")
    }

    get pinLimitReached() {
        return this.state.numberOfPinnedTabs >= MAX_PINNED_TABS;
    }

    /**
     * The Dropdown awaits beforeOpen before showing its menu, so the list is
     * always fetched right before it becomes visible.
     */
    onBeforeOpen() {
        return this.refreshTabs();
    }

    async isExists(tab) {
        /**
         * Checks if the user has cliked a tab item that points to a deleted record(menu_id)
         */
        let records = await this.orm.search("ir.ui.menu", [['id', '=', tab.menu_id]], { limit: 1 });
        if (records.length) {
            return true;
        }
        this.notification.add("The tab you are trying to access may have deleted!", {
            title: "Unable to redirect!",
            type: "warning", // Options: "success", "danger", "warning", "info"
            sticky: false,   // Set to true if it should stay until manually closed
        });
        return false;
    }

    async refreshTabs() {
        this.state.tabs = await this.recentTabsService.loadTabs();
        this.state.numberOfPinnedTabs =
            Number(JSON.parse(sessionStorage.getItem("numberOfPinnedTabs"))) || 0;
    }

    async openTab(tab) {
        if (! await this.isExists(tab)) {
            return
        }
        if (tab.pinned) {
            this.recentTabsService.updateLastVisitedPinned(tab);
        }
        window.open(tab.tab_url, "_self");
    }

    async openInNewTab(tab) {
        if (! await this.isExists(tab)) {
            return
        }
        if (tab.pinned) {
            this.recentTabsService.updateLastVisitedPinned(tab);
        }
        window.open(tab.tab_url, "_blank");
    }

    async onPinTabClicked(tab) {
        if (! await this.isExists(tab)) {
            return
        }
        if (this.pinLimitReached) {
            return;
        }
        await this.recentTabsService.pinTab(tab);
        await this.refreshTabs();
    }

    async onUnpinTabClicked(tab) {
        await this.recentTabsService.unpinTab(tab, this.state.numberOfPinnedTabs);
        await this.refreshTabs();
    }

    async clearTab(tab) {
        if (tab) {
            if (tab.pinned) {
                await this.recentTabsService.unpinTab(tab, this.state.numberOfPinnedTabs);
            }
            await this.recentTabsService.clearTab(tab);
        }
        await this.refreshTabs();
    }

    async clearAllTabs() {
        await this.recentTabsService.clearAllTabs();
        await this.refreshTabs();
    }
}

registry.category("systray").add("RecentTabsSystrayIcon", {
    Component: RecentTabsSystrayIcon,
});