/** @odoo-module **/
import { NavBar } from "@web/webclient/navbar/navbar";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useRef, useExternalListener, useState } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { SearchBar } from "@web/search/search_bar/search_bar";


export class GlobalSearch extends SearchBar {
    // NavBar is extended using patching to add functions of global search.
    setup() {
        this.globalsearch = useRef("globalSearch");
        this.menuService = useService("menu");
        this.state = useState({
            menu_list: [],
            result: null,
        });
        this.root = useRef("root");
        this.ui = useService("ui");
        this.scrollContainer = useRef("scrollContainer");
        // core state
        this.state = useState({
            expanded: [],
            focusedIndex: 0,
            query: "",
        });

        // derived state
        this.items = useState([]);
        this.subItems = {};
        this.globalSearchMobile = useRef("GlobalSearchMobile")
        this.orm = useService("orm");
        this.inputRef = useRef("autofocus")
        this.items_list = useRef("items_list")
        this.keepLast = new KeepLast();
        useExternalListener(window, "click", this.onWindowClick);
        useExternalListener(document, "keydown", this.onWindowKeydown);
        this.arowup_first_time = true;
    }

    onClickSearchIcon() {
        this.globalSearchMobile.el.classList.toggle("d-none")
    }

    onSearchInput(ev) {
        const query = ev.target.value.trim();
        const app_list = this.menuService.getAll();
        const menu_list = [];

        if (query) {
            const apps = this.menuService.getApps();
            app_list.forEach(app => {
                if (app.id !== "root" && app.actionModel !== false &&
                    app.name.toLowerCase().match(new RegExp(query.toLowerCase().replace(/[.*+\-?^${}()|[\]\\]/g, '\\$&')))
                ) {
                    let app_name = "";
                    apps.forEach(a => {
                        if (a.appID === app.appID) {
                            app_name = a.name;
                            if (a.childrenTree) a.childrenTree.forEach(item => {
                                const childNames = item.childrenTree.map(child => child.name);
                                if (childNames.includes(app.name) && app.childrenTree && !app.childrenTree.length) app.name = `${item.name}/${app.name}`;
                            });
                        }
                    });

                    const pathArray = app.name.split("/").filter(segment => segment.trim() !== "");
                    const uniquePathArray = [...new Set(pathArray)];
                    app.name = uniquePathArray.join("/");
                    menu_list.push({
                        id: app.id,
                        name: `${app_name}/${app.name}`,
                        actionModel: app.actionModel,
                        class: ""
                    });
                    app.name = uniquePathArray[uniquePathArray.length - 1]
                }
            });
        }
        this.state.items = query ? menu_list : [];
    }

    onWindowClick(ev) {
        if (this.state.items && this.root.el.contains(ev.target)
        ) {
            this.resetState();
        }
    }

    resetState() {
        this.state.expanded = false
        this.state.items = []
    }

    onSearchKeydown(ev) {
        if (ev.isComposing) {
            // This case happens with an IME for example: we let it handle all key events.
            return;
        }
        let focusedItem = this.state.items && this.state.items.length ? this.state.items[this.state.focusedIndex] : [];
        let focusedIndex;
        switch (ev.key) {
            case "ArrowDown":
                ev.preventDefault();
                this.arowup_first_time = true
                if (this.state.items) {
                    if (this.state.focusedIndex === 0 || this.state.focusedIndex >= this.state.items.length) {
                        focusedIndex = 0;
                        focusedItem = this.state.items && this.state.items.length ? this.state.items[focusedIndex] : [];
                        focusedIndex += 1
                    } else {
                        focusedItem = this.state.items && this.state.items.length ? this.state.items[this.state.focusedIndex] : [];
                        focusedIndex = this.state.focusedIndex + 1
                    }
                }
                const suggestionLists = this.root.el.querySelectorAll('.cy-search_suggestion-list.active');
                suggestionLists.forEach(e => e.classList.remove('active'));
                if (focusedItem) {
                    const searchItem = this.root.el.querySelector(`.search-item-${focusedItem.id}`);
                    if (searchItem) {
                        searchItem.classList.add('active');
                    } else {
                        console.error(`Element with class '.search-item-${focusedItem.id}' not found.`);
                    }
                } else {
                    console.error('focusedItem is not defined or falsy.');
                }
                break;
            case "ArrowUp":
                ev.preventDefault();
                if (this.state.items) {
                    if (this.state.focusedIndex === 0 || this.state.focusedIndex > this.state.items.length - 1) {
                        focusedIndex = this.state.items.length - 1;
                        focusedItem = this.state.items && this.state.items.length ? this.state.items[focusedIndex] : [];
                    } else {
                        if (this.arowup_first_time === true) {
                            focusedIndex = this.state.focusedIndex - 2;
                            this.arowup_first_time = false;
                        } else {
                            focusedIndex = this.state.focusedIndex - 1;
                        }
                        focusedItem = this.state.items && this.state.items.length ? this.state.items[focusedIndex] : [];
                    }
                }
                this.root.el.querySelectorAll('.cy-search_suggestion-list.active').forEach(e => e.classList.remove('active'));
                if (focusedItem) {
                    const item = this.root.el.querySelector(`.search-item-${focusedItem.id}`);
                    if (item) {
                        item.classList.add('active');
                    }
                }
                break;
            case "ArrowLeft":
                if (focusedItem && focusedItem.isParent && focusedItem.isExpanded) {
                    ev.preventDefault();
                    this.toggleItem(focusedItem, false);
                } else if (focusedItem && focusedItem.isChild) {
                    ev.preventDefault();
                    focusedIndex = this.state.items.findIndex(
                        (item) => item.isParent && item.searchItemId === focusedItem.searchItemId
                    );
                } else if (focusedItem && focusedItem.isFieldProperty) {
                    ev.preventDefault();
                    focusedIndex = this.state.items.findIndex(
                        (item) => item.isParent && item.searchItemId === focusedItem.propertyItemId
                    );
                } else if (ev.target.selectionStart === 0) {
                    // focus rightmost facet if any.
                    this.focusFacet();
                } else {
                    // do nothing and navigate inside text
                }
                break;
            case "ArrowRight":
                if (ev.target.selectionStart === this.state.query.length) {
                    if (focusedItem && focusedItem.isParent) {
                        ev.preventDefault();
                        if (focusedItem.isExpanded) {
                            focusedIndex = this.state.focusedIndex + 1;
                        } else {
                            this.toggleItem(focusedItem, true);
                        }
                    } else if (ev.target.selectionStart === this.state.query.length) {
                        // Priority 3: focus leftmost facet if any.
                        this.focusFacet(0);
                    }
                }
                break;
            case "Enter":
                const items = this.state.items;
                if (items && items.length) {
                    ev.preventDefault(); // keep the focus inside the search bar
                    this.selectMenu(this.root.el.querySelector('.cy-search_suggestion-list.active'), this);
                }
                break;
            case "Tab":
                if (this.state.query.length && focusedItem) {
                    ev.preventDefault(); // keep the focus inside the search bar
                    this.selectItem(focusedItem);
                }
                break;
            case "Escape":
                this.inputRef.el.value = ''
                this.state.items = []
                break;
        }

        if (focusedIndex !== undefined) {
            this.state.focusedIndex = focusedIndex;
        }
    }

    onFocusSearchInput() {
        let searchSpan = this.root.el.querySelectorAll('.cy-search');
        searchSpan.forEach(element => {
            element.classList.add('focused');
        });
    }

    onBlurSearchInput() {
        let searchSpan = this.root.el.querySelectorAll('.cy-search')
        searchSpan.forEach(element => {
            element.classList.remove('focused');
        });
    }

    onWindowKeydown(ev) {
        if (ev.key === "Escape") {
            this.resetState();
        }
    }

    selectMenu(ev, self) {
        /*
         * Handle the selection of a menu item.
         * If the selected item has a hash, it updates the window location.
         * Clears the search area and resets the menu list state.
         * @param {Event} ev - The click event object.
         */
        if (!ev || (Array.isArray(ev) && ev.length === 0)) {
            return
        }
        if (ev && ev.id) {
            window.location.href = "#menu_id=" + ev.id;
        } else if (ev && ev.target.hash === undefined) {
            if (ev.target.children[0]) {
                window.location.href = ev.target.children[0].hash;
            }
        }
        this.inputRef.el.value = ''
        self.state.items = [];
    }


}

GlobalSearch.template = "GlobalSearch";
GlobalSearch.components = {
    Dropdown,
    DropdownItem
};

NavBar.components = {
    /**
     * Object that defines the components of the NavBar.
     */
    ...NavBar.components,
    GlobalSearch,
};

export const GlobalSearchItem = {
    Component: GlobalSearch,
};

// registry.category("navbaritems").add("GlobalSearch", GlobalSearchItem, {
//     sequence: 1,
// });