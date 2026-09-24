/** @odoo-module **/
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {CogMenuItem} from "@cyllo_base/js/cog_menu_item";
import {registry} from "@web/core/registry";
import {jsonrpc} from "@web/core/network/rpc_service";
import {useService} from "@web/core/utils/hooks";
import {sprintf} from "@web/core/utils/strings";
import {session} from "@web/session";
import {_t} from "@web/core/l10n/translation";

const {Component, useState, onMounted} = owl;
const cogMenuRegistry = registry.category("cogMenu");

export class AddToShortcut extends Component {
    setup() {
        this.menuService = useService("menu");
        this.action = useService("action");
        this.orm = useService('orm');
        this.notification = useService("notification");
        this.state = useState({
            name: this.env.config.getDisplayName(),
            isAddedToShortcut: false,
        });
        onMounted(async () => {
                var shortcut = await this.orm.searchRead('shortcut.menu', [])
                var is_added_to_shortcut = shortcut.find((rec) => rec.window_action_id[0] === this.env.config.actionId
                    && rec.create_uid[0] === session.uid)
                if (is_added_to_shortcut) {
                    this.state.isAddedToShortcut = true
                }
            }
        )
    }

    getMenuIdFromUrl() {
        const hash = window.location.hash;
        const params = new URLSearchParams(hash.slice(1));
        return params.get('menu_id');
    }

    async addToShortcuts() {
        if (this.env.config.actionId) {
            const result = await jsonrpc('/add_to_shortcuts', {
                actionId: this.env.config.actionId,
                name: this.state.name,
                model: this.env.searchModel.resModel,
                menu_id: parseInt(this.action.currentController?.action?.context?.params?.menu_id || this.getMenuIdFromUrl()),
            });
            if (result) {
                this.notification.add(
                    sprintf(_t(`"%s" added to your shortcuts`), this.state.name),
                    {
                        title: 'Shortcut Added',
                        type: "success",
                    }
                );
                this.state.name = this.env.config.getDisplayName();
                this.env.services['action'].doAction('reload_context');
            } else {
                this.notification.add(_t("Could not add shortcut to dashboard"), {
                    type: "danger",
                });
            }
        }
    }

    async removeFromShortcuts() {
        if (this.env.config.actionId) {
            const result = await jsonrpc('/remove_from_shortcuts', {
                actionId: this.env.config.actionId,
            });
            if (result) {
                this.notification.add(
                    sprintf(_t(`"%s" removed from shortcut`), this.state.name),
                    {
                        title: 'Shortcut Removed',
                        type: "warning",
                    }
                );
                this.state.name = this.env.config.getDisplayName();
                this.env.services['action'].doAction('reload_context');
            } else {
                this.notification.add(_t("Could not remove shortcut from dashboard"), {
                    type: "danger",
                });
            }
        }
    }
}

AddToShortcut.template = "cyllo_dashboard.AddToShortcuts";
AddToShortcut.components = {DropdownItem, Dropdown, CogMenuItem};

export const addToShortcutItem = {
    Component: AddToShortcut,
    groupNumber: 1,
    isDisplayed: ({config}) => config.viewType !== "form",
};

cogMenuRegistry.add("add-to-shortcut", addToShortcutItem, {sequence: 10});
