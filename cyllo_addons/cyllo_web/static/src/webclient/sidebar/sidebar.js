/** @odoo-module **/
import { NavBar } from "@web/webclient/navbar/navbar";
import { BurgerMenu } from "@web/webclient/burger_menu/burger_menu";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { useEffect, useState, useRef, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { isMacOS } from "@web/core/browser/feature_detection";
import { getCachedSvgText } from "@cyllo_base/js/svg_icon_cache";

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.commandService = useService("command");
        this.ui = useService("ui");
        this.cyMenuSidebarRef = useRef("cyMenuSidebar");
        this.menuSidebarState = useState({
            isSidebarOpen: localStorage.getItem("cyMenuSidebarOpen") === "true",
        });
        this.bodyEl = document.querySelector("body");

        this.websiteService = registry.category("services").contains("website")
            ? useService("website")
            : null;
        this.websiteContext = this.websiteService ? useState(this.websiteService.context) : null;

        onMounted(() => {
            // The persisted sidebar state is a desktop only preference. On
            // small screens the rail stays hidden until the toggle button
            // in the navbar opens it as an overlay drawer.
            if (this.menuSidebarState.isSidebarOpen && !this.ui.isSmall) {
                this.bodyEl.classList.add("cy-menu-sidebar-open");
            }
        });

        useEffect(
            () => {
                if (!this.appSubMenus.el) {
                    return;
                }
                const observer = new ResizeObserver(() => this.adapt());
                observer.observe(this.appSubMenus.el);
                return () => observer.disconnect();
            },
            () => [this.appSubMenus.el]
        );

        useEffect(
            (appId) => {
                if (!appId) {
                    return;
                }
                // Scroll the rail to the active app on EVERY app change (not
                // once): apps also become current outside this rail — the
                // Overview's shortcut tiles switch the navbar app via
                // setCurrentMenu, and the newly appended icon may sit far
                // down the list.
                const activeAppEl = this.cyMenuSidebarRef.el?.querySelector(".cy-menu-sidebar-apps li.active");
                if (activeAppEl) {
                    activeAppEl.scrollIntoView({ block: "center", behavior: "smooth" });
                }
            },
            () => [this.currentApp?.id]
        );
    },

    handleSearchClick() {
        // The command palette runs above the content, so step out of the
        // mobile drawer before opening it.
        this.closeMobileSidebarIfOpen();
        this.commandService.openMainPalette({ searchValue: "/" });
    },

    async adapt() {
        const result = await super.adapt();
        const sectionsMenu = this.appSubMenus?.el;
        if (!sectionsMenu) {
            return result;
        }
        const extraIds = new Set(
            this.currentAppSectionsExtra.filter(Boolean).map((section) => section.id.toString())
        );
        const sections = sectionsMenu.querySelectorAll(":scope > *:not(.o_menu_sections_more)");
        for (const section of sections) {
            const sectionId =
                section.dataset.section ||
                section.querySelector("[data-section]")?.getAttribute("data-section");
            section.classList.toggle("d-none", extraIds.has(sectionId));
        }
        return result;
    },

    get currentApp() {
        return this.menuService.getCurrentApp();
    },

    get isWebsiteEditing() {
        return !!(this.websiteContext && this.websiteContext.edition);
    },

    get searchShortcutKey() {
        return isMacOS() ? "Ctrl" : "Alt";
    },

    toggleMenuSidebar() {
        this.menuSidebarState.isSidebarOpen = !this.menuSidebarState.isSidebarOpen;
        this.bodyEl.classList.toggle("cy-menu-sidebar-open", this.menuSidebarState.isSidebarOpen);
        // Only desktops remember the toggle: on small screens the drawer is a
        // temporary overlay and always starts closed again.
        if (!this.ui.isSmall) {
            localStorage.setItem("cyMenuSidebarOpen", this.menuSidebarState.isSidebarOpen);
        }
    },

    // The hamburger icon in front of the app name opens the standard drawer
    // in its apps mode (All Apps + current app sections, anchored left),
    // while the systray toggle keeps odoo's native user-menu behaviour.
    openMobileDrawer() {
        // The systray burger toggle keeps opening odoo's own drawer variant
        // (user menu only, anchored right). The hamburger in front of the
        // app name asks BurgerMenu — through the env bus — for the app
        // navigation variant: All Apps + current app sections, anchored left.
        this.env.bus.trigger("CY_OPEN_APPS_BURGER");
    },

    // On small screens the closed rail is never shown: the body
    // "cy-menu-sidebar-open" class turns it into a temporary overlay drawer
    // above the content. Selecting an app (or opening the command palette)
    // must restore the content view.
    closeMobileSidebarIfOpen() {
        if (this.ui.isSmall && this.menuSidebarState.isSidebarOpen) {
            this.toggleMenuSidebar();
        }
    },

    async onAppClick(app) {
        await this.menuService.selectMenu(app);
        this.closeMobileSidebarIfOpen();
    },

    async getSvg(svgPath, containerId) {
        const data = await getCachedSvgText(svgPath);
        if (!data) {
            return;
        }
        let svgContainer = this.cyMenuSidebarRef.el?.querySelector(`#${containerId}`);
        for (let attempt = 0; !svgContainer && attempt < 30; attempt++) {
            await new Promise((resolve) => requestAnimationFrame(resolve));
            svgContainer = this.cyMenuSidebarRef.el?.querySelector(`#${containerId}`);
        }
        if (svgContainer) {
            svgContainer.innerHTML = data;
        }
    },
});

// The standard mobile drawer serves two entry points (see sidebar.xml for
// the templates): the systray toggle keeps odoo's native behaviour —
// right-anchored drawer showing the user menu only — while the navbar
// hamburger triggers CY_OPEN_APPS_BURGER and opens the app navigation mode
// (All Apps + current app sections, anchored left). The mode lives in
// this.state.rightOnlyMode and drives the drawer's cy-burger-left /
// cy-burger-right classes (template) and the poses (sidebar.scss).
const CY_SWIPE_CLOSE_THRESHOLD = 100;

patch(BurgerMenu.prototype, {
    setup() {
        super.setup();
        this.commandService = useService("command");
        this.state.rightOnlyMode = false;
        this.state.showAllApps = false;
        this.state.allAppsSearch = "";
        onMounted(() => {
            this.env.bus.addEventListener("CY_OPEN_APPS_BURGER", () =>
                this._openBurgerWithApps()
            );
        });
    },

    get searchShortcutKey() {
        return isMacOS() ? "Ctrl" : "Alt";
    },

    // Icons for the shared cyllo_base.AppIcon renderer (All Apps section):
    // the drawer is portaled to the body, so resolve the containers globally
    // by their unique id — the template passes iconKey "burger-" + appId so
    // they can never collide with the ones of the sidebar rail.
    async getSvg(svgPath, containerId) {
        const data = await getCachedSvgText(svgPath);
        if (!data) {
            return;
        }
        let svgContainer = null;
        for (let attempt = 0; !svgContainer && attempt < 30; attempt++) {
            await new Promise((resolve) => requestAnimationFrame(resolve));
            svgContainer = document.getElementById(containerId);
        }
        if (svgContainer) {
            svgContainer.innerHTML = data;
        }
    },

    // The caret is gone everywhere: the apps drawer (left) hides the avatar
    // topbar behind the "All Apps" pill and the user menu is a drawer of its
    // own on the right, always unfolded there.
    get isUserMenuTogglable() {
        return false;
    },

    // The user menu shows only in user mode; the apps mode (navbar
    // hamburger) always shows the app navigation.
    get isUserMenuUnfolded() {
        return this.state.rightOnlyMode;
    },

    // The systray toggle keeps its native behaviour: right anchored, user
    // menu only.
    _openBurger() {
        this.state.rightOnlyMode = true;
        this.state.isUserMenuOpened = true;
        super._openBurger();
    },

    // The navbar hamburger opens the app navigation drawer from the left,
    // starting on the current app's sections (not the All Apps list).
    _openBurgerWithApps() {
        this.state.rightOnlyMode = false;
        this.state.isUserMenuOpened = false;
        super._openBurger();
        // Apps without submenus (like Overview) would show an empty page
        // with just the header: open the "All Apps" list directly instead.
        this.state.showAllApps =
            !this.currentApp || this.currentAppSections.length === 0;
    },

    // On close, the mode is deliberately left untouched: flipping
    // rightOnlyMode while the leaving animation runs would re-render the
    // drawer with the other anchoring class mid-exit and break the close
    // direction. resetBurgerState (below) runs in Transition's onLeave (see
    // the sidebar.xml BurgerMenu extension) once the drawer is gone, so the
    // displayed content stays stable during the exit as well.

    // Swaps the drawer content between the current app's sections and the
    // All Apps list; reached from the drawer's sticky footer "All Apps"
    // toggle (the header app pill is a plain, non-clickable label).
    _toggleAllApps() {
        this.state.showAllApps = !this.state.showAllApps;
    },

    // The All Apps searchbar (below the topbar) narrows the app list as the
    // user types; matching is case-insensitive on the app name.
    get filteredApps() {
        const query = (this.state.allAppsSearch || "").trim().toLowerCase();
        const apps = this.menuRepo.getApps();
        if (!query) {
            return apps;
        }
        return apps.filter((app) => (app.name || "").toLowerCase().includes(query));
    },

    onAllAppsSearch(ev) {
        this.state.allAppsSearch = ev.target.value;
    },

    openSearchPalette() {
        this._closeBurger();
        this.commandService.openMainPalette({ searchValue: "/" });
    },

    resetBurgerState() {
        this.state.rightOnlyMode = false;
        this.state.showAllApps = false;
        this.state.allAppsSearch = "";
    },

    // Swiping the drawer away must pull it past its anchoring edge:
    // left-anchored (apps mode) closes on a left swipe, right-anchored
    // (user menu mode) keeps odoo's native close on a right swipe.
    _onSwipeEnd(ev) {
        if (!this.swipeStartX) {
            return;
        }
        const deltaX = ev.changedTouches[0].clientX - this.swipeStartX;
        const dismissed = this.state.rightOnlyMode
            ? deltaX > CY_SWIPE_CLOSE_THRESHOLD
            : deltaX < -CY_SWIPE_CLOSE_THRESHOLD;
        if (!dismissed) {
            return;
        }
        this._closeBurger();
        this.swipeStartX = null;
    },
});
