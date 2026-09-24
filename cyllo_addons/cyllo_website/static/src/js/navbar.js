/** @odoo-module **/

import { NavBar } from '@web/webclient/navbar/navbar';
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { Systray} from "@cyllo_web/js/systray/cyllo_systray/systray";

const websiteSystrayRegistry = registry.category('website_systray');

patch(NavBar.prototype, {
    setup() {
        super.setup();
    },

    /**
     * @override
     */
    get systrayItems() {
        if (this.shouldDisplayWebsiteSystray) {
            return websiteSystrayRegistry
                .getEntries()
                .map(([key, value], index) => ({ key, ...value, index }))
                .filter((item) => ('isDisplayed' in item ? item.isDisplayed(this.env) : true))
                .reverse();
        }
        return super.systrayItems;
    },
})