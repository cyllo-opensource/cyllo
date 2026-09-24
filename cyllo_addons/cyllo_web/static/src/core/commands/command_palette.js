/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { fuzzyLookup } from "@web/core/utils/search";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { CommandPalette, DefaultCommandItem } from "@web/core/commands/command_palette";
import { getCachedSvgText } from "@cyllo_base/js/svg_icon_cache";
import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { useService } from "@web/core/utils/hooks";
import { scrollTo } from "@web/core/utils/scrolling";
import { Component } from "@odoo/owl";

// -----------------------------------------------------------------------
// Apps/menu search ("/") — with app icons resolved
// -----------------------------------------------------------------------

// Core's "web.AppIconCommand" template only branches on webIconData (a
// base64 image) vs webIcon as a font-icon class — it has no case for our
// "module,path/to/icon.svg" convention (the same one cyllo_base.AppIcon
// handles for the sidebar), so those apps show up as an empty/broken
// font-icon box in the command palette (Ctrl+K / Alt+F search). Rather than
// patching core's unexported AppIconCommand class, resolve the svg into a
// data URI upfront so it flows through the existing webIconData -> <img>
// branch untouched.
class AppIconCommand extends Component {
    static template = "web.AppIconCommand";
    static props = {
        webIconData: { type: String, optional: true },
        webIcon: { type: Object, optional: true },
        ...DefaultCommandItem.props,
    };
}

async function buildAppIconProps(menu) {
    const props = {};
    if (menu.webIconData) {
        const prefix = menu.webIconData.startsWith("P")
            ? "data:image/svg+xml;base64,"
            : "data:image/png;base64,";
        props.webIconData = menu.webIconData.startsWith("data:image")
            ? menu.webIconData
            : prefix + menu.webIconData.replace(/\s/g, "");
        return props;
    }
    if (menu.webIcon && typeof menu.webIcon === "string" && menu.webIcon.endsWith(".svg")) {
        const svgText = await getCachedSvgText(menu.webIcon);
        if (svgText) {
            props.webIconData = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svgText)));
            return props;
        }
    }
    props.webIcon = menu.webIcon;
    return props;
}

registry.category("command_categories").add("apps", { namespace: "/" }, { sequence: 10, force: true });
registry.category("command_categories").add("menu_items", { namespace: "/" }, { sequence: 20, force: true });

registry.category("command_setup").add("/", {
    emptyMessage: _t("No menu found"),
    name: _t("menus"),
    placeholder: _t("Search for a menu..."),
}, { force: true });

registry.category("command_provider").add("menu", {
    namespace: "/",
    async provide(env, options) {
        const result = [];
        const menuService = env.services.menu;
        let { apps, menuItems } = computeAppsAndMenuItems(menuService.getMenuAsTree("root"));
        if (options.searchValue !== "") {
            apps = fuzzyLookup(options.searchValue, apps, (menu) => menu.label);

            fuzzyLookup(options.searchValue, menuItems, (menu) =>
                (menu.parents + " / " + menu.label).split("/").reverse().join("/")
            ).forEach((menu) => {
                result.push({
                    action() {
                        menuService.selectMenu(menu);
                    },
                    category: "menu_items",
                    name: menu.parents + " / " + menu.label,
                    href: menu.href || `#menu_id=${menu.id}&action_id=${menu.actionID}`,
                });
            });
        }

        const appProps = await Promise.all(apps.map(buildAppIconProps));
        apps.forEach((menu, index) => {
            result.push({
                Component: AppIconCommand,
                action() {
                    menuService.selectMenu(menu);
                },
                category: "apps",
                name: menu.label,
                href: menu.href || `#menu_id=${menu.id}&action_id=${menu.actionID}`,
                props: appProps[index],
            });
        });

        return result;
    },
}, { force: true });

// -----------------------------------------------------------------------
// Apps grid/list layout toggle (persisted, see command_palette.xml)
// -----------------------------------------------------------------------

const APPS_LAYOUT_STORAGE_KEY = "commandPaletteAppsLayout";

patch(CommandPalette.prototype, {
    setup() {
        super.setup();
        this.menuService = useService("menu");
        this.state.appsLayout = browser.localStorage.getItem(APPS_LAYOUT_STORAGE_KEY) || "grid";

        // Core only wires ArrowUp/ArrowDown (built for a single-column list),
        // stepping the flat command list by 1. The apps grid is multi-column,
        // so it needs real 2D nav: Left/Right step by 1 (visually sideways,
        // same as core's step), Up/Down need to jump by the actual rendered
        // column count to move a full row — handled in the
        // selectCommandAndScrollTo override below, keyed off axis so it only
        // changes behavior while the apps grid is showing. Same
        // bypassEditableProtection as core's Up/Down: arrow keys in this
        // search input are reserved for result navigation, never
        // text-cursor movement.
        useHotkey("ArrowLeft", () => this.selectCommandAndScrollTo("PREV", "horizontal"), {
            bypassEditableProtection: true,
            allowRepeat: true,
        });
        useHotkey("ArrowRight", () => this.selectCommandAndScrollTo("NEXT", "horizontal"), {
            bypassEditableProtection: true,
            allowRepeat: true,
        });
    },

    async executeCommand(command) {
        if (command.href) {
            const params = new URLSearchParams(command.href.split("#")[1]);
            let menu = params?.get("menu_id")
                        ? this.menuService.getMenuAsTree(params.get("menu_id"))
                        : false;
            if (menu?.id && menu?.appID) {
                this.env.bus.trigger("OPEN-MENU", menu);
            }
        }
        super.executeCommand(command);
    },

    setAppsLayout(mode) {
        this.state.appsLayout = mode;
        browser.localStorage.setItem(APPS_LAYOUT_STORAGE_KEY, mode);
    },

    // Master search's browse-mode model-title rows (isModelHeader, see
    // command_palette.js's master_search provider) are labels, not results —
    // bounce selection past them instead of letting default init, arrow
    // navigation, or mouse hover ever land on one. This is the single
    // choke-point every selection path (default index-0, PREV/NEXT, the grid
    // column-jump above, mouse hover) already routes through. Direction
    // matters: bouncing forward when the arrow moved backward would get
    // stuck flipping between the header and the row right after it, so the
    // bounce direction is inferred from which way the target index moved
    // relative to the current selection, wrapping at the edges the same way
    // core's own PREV/NEXT already does.
    selectCommand(index) {
        const total = this.state.commands.length;
        if (!total) {
            return super.selectCommand(-1);
        }
        const currentIndex = this.state.commands.indexOf(this.state.selectedCommand);
        const direction = index >= currentIndex ? 1 : -1;
        let guard = 0;
        while (this.state.commands[index]?.isModelHeader && guard < total) {
            index += direction;
            if (index < 0) {
                index = total - 1;
            } else if (index >= total) {
                index = 0;
            }
            guard += 1;
        }
        return super.selectCommand(index);
    },

    get isAppsGridActive() {
        return this.state.appsLayout === "grid" && this.state.selectedCommand?.category === "apps";
    },

    getAppsGridColumnCount() {
        const gridEl = this.listboxRef.el?.querySelector(".o_command_category_grid");
        if (!gridEl) {
            return 1;
        }
        const columns = getComputedStyle(gridEl).gridTemplateColumns.split(" ").filter(Boolean).length;
        return columns || 1;
    },

    selectCommandAndScrollTo(type, axis = "vertical") {
        if (axis !== "vertical" || !this.isAppsGridActive) {
            return super.selectCommandAndScrollTo(type);
        }

        // Vertical move while the apps grid is showing: jump by the actual
        // column count instead of core's default step-by-1, so Up/Down move
        // a full row like a real grid instead of sliding sideways.
        this.mouseSelectionActive = false;
        const index = this.state.commands.indexOf(this.state.selectedCommand);
        if (index === -1) {
            return;
        }
        const columns = this.getAppsGridColumnCount();
        const delta = type === "NEXT" ? columns : -columns;
        const nextIndex = Math.max(0, Math.min(this.state.commands.length - 1, index + delta));
        this.selectCommand(nextIndex);

        const command = this.listboxRef.el.querySelector(`#o_command_${nextIndex}`);
        if (command) {
            scrollTo(command, { scrollable: this.listboxRef.el });
        }
    },
});

// -----------------------------------------------------------------------
// Master search (">") — reuses the /cy/master/search RPC behind the
// Master Search systray dialog, surfaced as a command palette namespace.
// -----------------------------------------------------------------------

registry
    .category("command_categories")
    .add("master_search_results", { namespace: ">" }, { sequence: 10, force: true });

registry.category("command_setup").add(
    ">",
    {
        emptyMessage: _t("No record found"),
        name: _t("records"),
        placeholder: _t("Search for a record..."),
    },
    { force: true }
);

registry.category("command_provider").add(
    "master_search",
    {
        namespace: ">",
        async provide(env, options) {
            const result = [];

            const openRecord = (item) => {
                env.services.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: item.model,
                    res_id: item.id,
                    target: "current",
                    views: [[false, "form"]],
                });
            };

            result.push({
                action() {
                    env.services.action.doAction({
                        res_model: "ir.model",
                        name: _t("Models"),
                        target: "current",
                        type: "ir.actions.act_window",
                        view_mode: "tree,form",
                        views: [[false, "list"], [false, "form"]],
                    });
                },
                category: "master_search_results",
                name: _t("Add a model to master search"),
            });

            if (options.searchValue) {
                // Something typed: hit the same paginated search-as-you-type
                // RPC the Master Search dialog itself uses (no eager
                // full-table fetch — only what matches the query).
                const groups = await env.services.rpc("/cy/master/search", {
                    query: options.searchValue,
                    page: 1,
                    company_ids: env.services.company.activeCompanyIds,
                }).then(([data]) => data);

                for (const group of groups) {
                    for (const item of group) {
                        if (!item.isChild) {
                            continue;
                        }
                        result.push({
                            action: () => openRecord(item),
                            category: "master_search_results",
                            name: item.name,
                        });
                    }
                }
            } else {
                // Nothing typed yet: browse instead of searching — the 3
                // most recently master-search-enabled models, 5 most
                // recent records each (15 max), so opening ">" isn't a
                // dead end before you've typed anything.
                const models = await env.services.orm.searchRead(
                    "ir.model",
                    [["master_search", "=", true]],
                    ["name", "model"],
                    { limit: 3, order: "id desc" }
                );

                const perModelRecords = await Promise.all(
                    models.map((model) =>
                        env.services.orm
                            .searchRead(model.model, [], ["display_name"], {
                                limit: 5,
                                order: "id desc",
                            })
                            .catch(() => [])
                    )
                );

                models.forEach((model, index) => {
                    const records = perModelRecords[index];
                    if (!records.length) {
                        return;
                    }
                    // A model-name title row (grey background, see
                    // command_palette.xml/.scss for the isModelHeader
                    // styling) instead of prefixing every record's name —
                    // no-op action since it's a label, not a real result.
                    result.push({
                        action: () => {},
                        category: "master_search_results",
                        name: model.name,
                        isModelHeader: true,
                    });
                    for (const record of records) {
                        result.push({
                            action: () => openRecord({ model: model.model, id: record.id }),
                            category: "master_search_results",
                            name: record.display_name,
                        });
                    }
                });
            }

            return result;
        },
    },
    { force: true }
);
