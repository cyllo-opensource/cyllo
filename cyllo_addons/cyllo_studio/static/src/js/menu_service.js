/** @odoo-module **/

/**
 * Cyllo Studio Menu Service
 *
 * This module overrides the default Odoo menu loading mechanism to ensure
 * that newly created menus from Cyllo Studio are fetched fresh, bypassing
 * cached menus. It provides a service to manage menus and current app state,
 * and integrates with the Odoo action and router services.
 *
 * Features:
 * 1. Fetches menus using a unique hash to prevent cached menus from being used.
 * 2. Provides methods to get all menus, apps, and menu trees.
 * 3. Manages current app/menu state and triggers app change events.
 * 4. Handles menu selection and integrates with Odoo actions.
 *
 * Dependencies: ["action", "router"]
 */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";


const loadMenusUrl = `/web/webclient/cyllo_load_menus`;

/**
 * Creates a function to fetch menus from the server, bypassing cached menus.
 *
 * @returns {Function} fetchLoadMenus - Function that fetches the latest menus.
 */
function makeFetchLoadMenus() {
    const cacheHashes = session.cache_hashes;
    let loadMenusHash = cacheHashes.load_menus || new Date().getTime().toString();
    return async function fetchLoadMenus(reload) {
        const res = await browser.fetch(`${loadMenusUrl}/${loadMenusHash}`);
        if (!res.ok) {
            throw new Error("Error while fetching menus");
        }
        return res.json();
    };
}

/**
 * Creates the menu service object with utility methods to interact with menus.
 *
 * @param {Object} env - Owl component environment
 * @param {Object} menusData - Fetched menu data
 * @param {Function} fetchLoadMenus - Function to reload menus from the server
 * @returns {Object} - The menu service API
 */
function makeMenus(env, menusData, fetchLoadMenus) {
    let currentAppId;
    function _getMenu(menuId) {
        return menusData[menuId];
    }
    function _updateURL(menuId) {
        env.services.router.pushState({ menu_id: menuId }, { lock: true });
    }
    function _setCurrentMenu(menu, updateURL = true) {
        menu = typeof menu === "number" ? _getMenu(menu) : menu;
        if (menu && menu.appID !== currentAppId) {
            currentAppId = menu.appID;
            env.bus.trigger("MENUS:APP-CHANGED");
            if (updateURL) {
                _updateURL(menu.id);
            }
        }
    }

    return {
        getAll() {
            return Object.values(menusData);
        },
        getApps() {
            return this.getMenu("root").children.map((mid) => this.getMenu(mid));
        },
        getMenu: _getMenu,
        getCurrentApp() {
            if (!currentAppId) {
                return;
            }
            return this.getMenu(currentAppId);
        },
        /**
         * Returns the menu and its children recursively as a tree.
         *
         * @param {number|string} menuID - Menu ID to convert to tree
         */
        getMenuAsTree(menuID) {
            const menu = this.getMenu(menuID);
            if (!menu.childrenTree) {
                menu.childrenTree = menu.children.map((mid) => this.getMenuAsTree(mid));
            }
            return menu;
        },
         /**
         * Selects a menu and executes its action, updating the current app/menu.
         *
         * @param {number|Object} menu - Menu ID or menu object
         */
        async selectMenu(menu) {
            menu = typeof menu === "number" ? this.getMenu(menu) : menu;
            if (!menu.actionID) {
                return;
            }
            await env.services.action.doAction(menu.actionID, {
                clearBreadcrumbs: true,
                onActionReady: () => {
                    _setCurrentMenu(menu, false);
                },
            });
            _updateURL(menu.id);
        },
        setCurrentMenu: (menu) => _setCurrentMenu(menu),

        /**
         * Reloads menus from the server and triggers app change event.
         */
        async reload() {
            if (fetchLoadMenus) {
                menusData = await fetchLoadMenus(true);
                env.bus.trigger("MENUS:APP-CHANGED");
            }
        },
    };
}

export const menuService = {
    dependencies: ["action", "router"],
    async start(env) {
        const fetchLoadMenus = makeFetchLoadMenus();
        const menusData = await fetchLoadMenus();
        return makeMenus(env, menusData, fetchLoadMenus);
    },
};

registry.category("services").add("menu", menuService,{force:true});


