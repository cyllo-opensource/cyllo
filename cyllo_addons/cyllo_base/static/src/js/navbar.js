/** @odoo-module **/
import {patch} from "@web/core/utils/patch";
import {NavBar} from "@web/webclient/navbar/navbar";
import {registry} from "@web/core/registry";
import {useService, useBus} from "@web/core/utils/hooks";

const {useRef, onMounted, useState} = owl;
const navbarRegistry = registry.category("navbaritems");

patch(NavBar.prototype, {
    setup() {
        this.action = useService("action");
        this.menuToggleIcon = useRef('menu-toggle-icon')
        this.checkIconDirection()
        this.menuService = useService("menu");
        this.menuState = useState({
            isSubMenuOn: localStorage.getItem("isSidebarOn") === 'true'
        })
        useBus(this.env.bus, 'homeButtonClicked', ({detail}) => {
            this.menuState.isSubMenuOn = detail.isSubMenuOn
        });
        onMounted(() => {
            this.checkIconDirection()
        });
        super.setup();
    },

    get NavBarItems() {
        return navbarRegistry
            .getEntries()
            .map(([key, value]) => ({
                key,
                ...value
            })).filter((item) => ("isDisplayed" in item ? item.isDisplayed(this.env) : true))
    },

    checkIconDirection() {
        const mainMenuVisibility = localStorage.getItem('mainMenuVisibility');
        if (this.menuToggleIcon.el) {
            this.menuToggleIcon.el.classList.toggle('inverted', mainMenuVisibility === 'true');
        }
    },

    onClickLogo() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "cyllo_user_dashboard",
        });
        this.env.bus.trigger('RESET_MENUS', {
            condition: false
        })
        localStorage.setItem("cy_selected_app", false)
    },

    set NavBarItems(_) {
    }
})