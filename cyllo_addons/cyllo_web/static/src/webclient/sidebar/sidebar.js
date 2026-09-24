/** @odoo-module **/
import { NavBar } from "@web/webclient/navbar/navbar";
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
            if (this.menuSidebarState.isSidebarOpen) {
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

        this.hasScrolledToActiveApp = false;
        useEffect(
            (appId) => {
                if (!appId || this.hasScrolledToActiveApp) {
                    return;
                }
                const activeAppEl = this.cyMenuSidebarRef.el?.querySelector(".cy-menu-sidebar-apps li.active");
                if (activeAppEl) {
                    activeAppEl.scrollIntoView({ block: "center", behavior: "auto" });
                    this.hasScrolledToActiveApp = true;
                }
            },
            () => [this.currentApp?.id]
        );
    },

    handleSearchClick() {
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
        if (this.menuSidebarState.isSidebarOpen) {
            this.bodyEl.classList.add("cy-menu-sidebar-open");
        } else {
            this.bodyEl.classList.remove("cy-menu-sidebar-open");
        }
        localStorage.setItem("cyMenuSidebarOpen", this.menuSidebarState.isSidebarOpen);
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
