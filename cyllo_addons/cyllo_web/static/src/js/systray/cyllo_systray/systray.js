/** @odoo-module **/
import {registry} from "@web/core/registry";
import {session} from "@web/session";
import {ErrorHandler} from "@web/core/utils/components";

const {Component, useState, useEffect} = owl;
import {useService} from "@web/core/utils/hooks";

const items = registry.category("systray")
const navbarItems = registry.category("navbaritems")

// QuickCreate ("+") lives in the "navbaritems" registry (cyllo_base's
// NavBar patch), not "systray" — merge it into the same item list so it
// gets pin/unpin management like every other systray entry instead of
// being force-shown outside that system.
function getAllItemEntries() {
    return [
        ...items.getEntries(),
        ...navbarItems.getEntries().filter(([key]) => key === "QuickCreate"),
    ]
}

export class Systray extends Component {
    setup() {
        this.alwaysPinned = ["SwitchCompanyMenu", "web.user_menu", "burger_menu", "discuss.CallMenu",
            "hr_attendance.attendance_menu", "web.debug_mode_menu", "SystrayReviewNotification"]
        this.state = useState({
            pinned: session.systray_pins,
            items: getAllItemEntries().map(([key, value]) => ({
                key, ...value,
                pinned: session.systray_pins.includes(key)
            })),
            pinnedItems: [],
            alwaysItems: [],
            showTray: false,
        })
        this.orm = useService("orm");
        this.notification = useService('notification');
        useEffect(() => {
            this.state.pinnedItems = this.state.items.filter((item) => !this.alwaysPinned.includes(item.key) && item.pinned && ("isDisplayed" in item ? item.isDisplayed(this.env) : true)).reverse()
            this.state.alwaysItems = this.state.items.filter((item) => this.alwaysPinned.includes(item.key) && ("isDisplayed" in item ? item.isDisplayed(this.env) : true)).reverse()
        }, () => [this.state.items, this.state.pinned.length])
    }

    get allItems() {
        return this.state.items.filter((item) => {
            return !this.alwaysPinned.includes(item.key) && ("isDisplayed" in item ? item.isDisplayed(this.env) : true)
        })
    }

    onClickShowTray() {
        this.state.showTray = !this.state.showTray
    }

    keyToName(key) {
        let split = key.split(".");
        let last = split[split.length - 1];
        last = last.replaceAll("_", " ");
        return last[0].toUpperCase() + last.slice(1);
    }

    async onPin(key, pin) {
        let pins = this.state.pinned
        if (pin) {
            if (pins.length > 4) {
                this.notification.add(
                    "You can only pin 5 items at a time.",
                    {type: "info"}
                );
                return
            } else {
                pins.push(key)
            }
        } else {
            let index = pins.indexOf(key);
            if (index !== -1) {
                pins.splice(index, 1);
            }
        }
        await this.orm.call("res.users", "pin_systray_icons", [session.uid, pins])
        this.state.pinned = pins
        this.state.items = getAllItemEntries().map(([key, value]) => ({key, ...value, pinned: pins.includes(key)}))
    }

}

Systray.template = "Systray"
Systray.components = {ErrorHandler}
