/** @odoo-module **/

import { Component } from "@odoo/owl";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { registry } from "@web/core/registry";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { CogMenuItem } from "@cyllo_base/js/cog_menu_item";

const cogMenuRegistry = registry.category("cogMenu");

class Refresh extends Component {
    static template = "cyllo_web.Refresh";
    static components = { DropdownItem, CogMenuItem };
    onRefresh() {
        this.env.searchModel._notify();
    }
}

export const RefreshItem = {
    Component: Refresh,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: async (env) =>
        env.config.viewType === "list"
};

cogMenuRegistry.add("refresh-menu", RefreshItem, { sequence: 10 });