/** @odoo-module */
import { registry } from "@web/core/registry";
import { Component, onWillStart, onWillUnmount, useRef, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { useSortable } from "@web/core/utils/sortable_owl";
import { jsonrpc } from "@web/core/network/rpc_service";
import { session } from "@web/session";
import { AccountSettingsPanel } from "@cyllo_dashboard/js/account_settings_panel";
import { DashboardKpi } from "@cyllo_dashboard/js/dashboard_kpi";
import { BannerCropDialog } from "@cyllo_dashboard/js/banner_crop_dialog";
import { browser } from "@web/core/browser/browser";

const actionRegistry = registry.category("actions");

// Define a new component named 'Cyllo Dashboard'
export class UserDashboard extends Component {
    setup() {
        super.setup(...arguments);
        this.user = useService("user");
        this.notification = useService("notification");
        this.origin = browser.location;
        this.orm = useService('orm');
        this.menuService = useService("menu");
        this.dialogService = useService("dialog");
        this.root = useRef("root");
        this.chartCanvas = useRef('system_ram');
        this.storageChart = useRef('storageChart');
        this.ramOverviewChart = useRef('ramOverviewChart');
        this.cpuChart = useRef('cpuChart');
        this.rootNonAdmin = useRef("root-non-admin");
        this.quickAccessGrid = useRef("quickAccessGrid");
        // Floating scroll-down affordance for the Quick access card.
        this.qaScrollState = useState({ canScrollDown: false });
        // Dashboard / Quick access split tabs in the page heading.
        this.tabBarRef = useRef("tabBar");
        this.tabBtnDashboard = useRef("tabDashboard");
        this.tabBtnQuickAccess = useRef("tabQuickAccess");
        // Quick access order via SortableJS (stock useSortable).
        // clone:false => placeholder is a plain div (no data-shortcut-id),
        // so it never collides with real tile keys.
        useSortable({
            ref: this.quickAccessGrid,
            elements: ".cy_quick_access_item",
            clone: false,
            ignore: ".cy_shortcut_add_icon",
            cursor: "grabbing",
            placeholderClasses: ["cy_quick_access_placeholder"],
            enable: () => (this.state.shortcuts || []).length > 1 && !(this.state.shortcutSearch || "").trim(),
            onDragStart: () => {
                this._suppressShortcutClick = true;
            },
            onDragEnd: () => {
                setTimeout(() => {
                    this._suppressShortcutClick = false;
                }, 100);
            },
            onDrop: (params) => this.onQuickAccessSortDrop(params),
        });
        this.userID = session.uid;
        this.session = session;
        this.state = useState({
            shortcuts: [],
            loginUserDetails: {},
            loginUserTotal: 0,
            userProfile: {},
            weatherDetails: {},
            activities: {},
            performanceInsights: {},
            nonAdmin: {},
            notifType: false,
            autoEdit: false,
            showLoading: true,
            userKpi: {},
            bannerUrl: "/cyllo_dashboard/static/src/img/coverImage.png",
            activeTab: "dashboard",
            inkLeft: 0,
            inkWidth: 0,
            mobileMenuOpen: "",
            shortcutSearch: "",
        })
        this.action = useService("action");
        this.getActivities();
        onWillStart(async () => {
            this.renderShortcuts();
            // Login details are admin-only: the non-admin dashboard has no
            // Login History card (it shows the Account Settings card).
            if (session.is_admin) {
                this.renderLoginUserDetails();
            }
            this.renderNonAdminUserDetails();
            this.renderUserProfile();
            this.getIdleTime();
            this.renderWeatherNotification();
            this.renderPerformanceInsight();
            this.renderUserKpi();

            await this.orm.call('res.users', 'get_change_pwd_view_id').then((result) => {
                this.view_id = result;
            });
            await this.orm.call('res.users', 'get_groups').then((result) => {
                this.groups = result;
            });
            await this.orm.call('res.users', 'get_current_user_details').then((result) => {
                this.userId = result.id;
                this.tz = result.current_tz
            });
            await this.orm.call('res.users', 'get_auto_edit_value').then((result) => {
                this.state.autoEdit = result;
            });
            await this.orm.call('res.users', 'clean_up_menus', [this.orm.user.userId]);
            const userBanner = await this.orm.searchRead(
                "res.users",
                [["id", "=", this.userId]],
                ["banner_image"]
            );
            if (userBanner && userBanner.length > 0 && userBanner[0].banner_image) {
                this.state.bannerUrl = `data:image/png;base64,${userBanner[0].banner_image}`;
            } else {
                this.state.bannerUrl = false;
            }
        });
        useEffect((ev) => {
            if (ev) {
                this.state.showLoading = false
                this.renderChart()
            } else {
                this.state.showLoading = true
            }
        }, () => [this.state.performanceInsights.ram_percent, this.state.activeTab])
        useEffect(() => {
            this.renderOverviewCharts();
        }, () => [this.state.performanceInsights.ram_percent, this.state.performanceInsights.used_memory, this.state.performanceInsights.total_memory, this.state.performanceInsights.total_ram, this.state.performanceInsights.total_cpu_usage, this.state.activeTab])
        // Show the scroll-down button + bottom fade while the Quick access
        // grid has content below the fold. Recomputed on scroll and on any
        // size change (shortcuts loading, window resize).
        useEffect(() => {
            const grid = this.quickAccessGrid.el;
            if (!grid) {
                return;
            }
            const update = () => {
                const overflows = grid.scrollHeight > grid.clientHeight + 2;
                const atBottom = grid.scrollHeight - grid.scrollTop - grid.clientHeight <= 2;
                this.qaScrollState.canScrollDown = overflows && !atBottom;
            };
            update();
            grid.addEventListener("scroll", update, { passive: true });
            const observer = new ResizeObserver(update);
            observer.observe(grid);
            return () => {
                grid.removeEventListener("scroll", update);
                observer.disconnect();
            };
        }, () => [this.state.shortcuts.length, this.state.activeTab]);
        // Slide the ink bar under the active heading tab (re-measured after
        // each render, so the active button's wider font is accounted for).
        useEffect(() => {
            this.updateTabInk();
        }, () => [this.state.activeTab, this.state.shortcuts.length]);
        // Keep the ink glued to its tab on container resizes.
        useEffect(() => {
            const wrap = this.tabBarRef.el;
            if (!wrap) {
                return;
            }
            const observer = new ResizeObserver(() => this.updateTabInk());
            observer.observe(wrap);
            return () => observer.disconnect();
        }, () => []);
        onWillUnmount(() => {
            this.cleanupIdleTimer();
            this.destroyOverviewCharts();
        });
    }

    cleanupIdleTimer() {
        if (this._idleInterval) {
            clearInterval(this._idleInterval);
            this._idleInterval = null;
        }
        for (const evt of this._idleHandlers || []) {
            document[evt] = null;
        }
        this._idleHandlers = [];
    }

    imageLoader(userid) {
        return `${this.origin.origin}/web/image?model=res.users&field=avatar_128&id=${userid}`
    }

    renderChart() {
        const ctx = this.chartCanvas.el
        const usedMemory = (this.state.performanceInsights.total_ram * this.state.performanceInsights.ram_percent) / 100
        const unUsedMemory = this.state.performanceInsights.total_ram - usedMemory
        if (ctx) {
            if (this.chart) {
                this.chart.destroy();
            }
            this.chart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Used memory', 'Free memory'],
                    datasets: [{
                        data: [usedMemory, unUsedMemory],
                        backgroundColor: [
                            '#9EA700',
                            '#ecedcc',
                        ],
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: 'Memory Usage in GB'
                        }
                    }
                }
            });
        }
    }

    renderOverviewCharts() {
        const insights = this.state.performanceInsights || {};
        // Storage (disk) values from System Monitor
        const totalStorage = Number(insights.total_memory) || 0;
        const usedStorage = Number(insights.used_memory) || 0;
        const freeStorage = Math.max(totalStorage - usedStorage, 0);
        // RAM values from System Monitor
        const totalRam = Number(insights.total_ram) || 0;
        const ramPercent = Number(insights.ram_percent) || 0;
        const usedRam = (totalRam * ramPercent) / 100;
        const freeRam = Math.max(totalRam - usedRam, 0);
        // CPU value from System Monitor
        const cpuUsage = Number(insights.total_cpu_usage) || 0;
        const cpuIdle = Math.max(100 - cpuUsage, 0);

        const makeBarChart = (ref, oldChartKey, labels, data, title) => {
            const canvas = ref && ref.el;
            if (!canvas) {
                return;
            }
            if (this[oldChartKey]) {
                this[oldChartKey].destroy();
                this[oldChartKey] = null;
            }
            // Skip rendering when there is no data yet
            if (!data.some((v) => Number(v) > 0)) {
                return;
            }
            this[oldChartKey] = new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: title,
                        data: data,
                        backgroundColor: ['#9EA700', '#ecedcc'],
                        borderColor: '#9EA700',
                        borderWidth: 1,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        title: { display: true, text: title }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        };

        makeBarChart(this.storageChart, 'storageChartInstance',
            ['Used', 'Free'],
            [usedStorage, freeStorage], 'Storage Usage in GB');
        makeBarChart(this.ramOverviewChart, 'ramOverviewChartInstance',
            ['Used', 'Free'],
            [usedRam, freeRam], 'Memory Usage in GB');
        makeBarChart(this.cpuChart, 'cpuChartInstance',
            ['Used', 'Idle'],
            [cpuUsage, cpuIdle], 'CPU Usage in %');
    }

    destroyOverviewCharts() {
        for (const key of ['storageChartInstance', 'ramOverviewChartInstance', 'cpuChartInstance']) {
            if (this[key]) {
                this[key].destroy();
                this[key] = null;
            }
        }
    }

    getIdleTime() {
        jsonrpc('/get_idle_time/timer').then((data) => {
            if (data) {
                this.minutes = data
                this.idleTimer()
            }
        })
    }

    idleTimer() {
        // Clear any timer/handlers from a previous mount before starting fresh.
        this.cleanupIdleTimer();
        var date = new Date();
        date.setMinutes(date.getMinutes() + this.minutes);
        var updatedTimestamp = date.getTime();
        /** Running the count down using setInterval function */
        this._idleInterval = setInterval(() => {
            var now = new Date().getTime();
            var distance = updatedTimestamp - now;
            var days = Math.floor(distance / (1000 * 60 * 60 * 24));
            var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            var seconds = Math.floor((distance % (1000 * 60)) / 1000);
            $("#idle_timer").empty();
            if (hours && days) {
                $("#idle_timer").append('<span>' + days + "d " + hours + "h " + minutes + "m " + seconds + "s " + '</span>');
            } else if (hours) {
                $("#idle_timer").append('<span>' + hours + "h " + minutes + "m " + seconds + "s " + '</span>');
            } else {
                $("#idle_timer").append('<span>' + minutes + "m " + seconds + "s " + '</span>')
            }
            /** if the countdown is zero the link is redirect to the login page*/
            if (distance < 0) {
                this.cleanupIdleTimer();
                $("#idle_timer").empty();
                $("#idle_timer").append("EXPIRED");
                location.replace("/web/session/logout")
            }
        }, 1000);
        /** Any user activity resets the countdown. */
        const resetTimer = () => {
            var d = new Date();
            d.setMinutes(d.getMinutes() + this.minutes);
            updatedTimestamp = d.getTime();
        };
        this._idleHandlers = ['onmousemove', 'onkeypress', 'onclick',
            'ontouchstart', 'onmousedown', 'onload'];
        for (const evt of this._idleHandlers) {
            document[evt] = resetTimer;
        }
    }

    renderWeatherNotification() {
        jsonrpc('/weather/notification/check').then((data) => {
            if (data['cod'] == 200) {
                var temp = Math.floor(data.main.temp - 273);
                this.state.weatherDetails.city = data.name
                this.state.weatherDetails.temp = temp
                this.state.weatherDetails.description = data.weather[0].description
                this.state.weatherDetails.weather = data.weather[0].main
                this.state.weatherDetails.icon = data.weather[0].icon
            }
        })
    }

    async onClickPermissions() {
        this.env.services['action'].doAction({
            name: "Permissions",
            type: 'ir.actions.act_window',
            res_model: 'res.groups',
            views: [[false, 'tree'], [false, 'form']],
            domain: [['id', 'in', this.groups]],
            target: 'current',
        });
    }

    async uploadBanner(ev) {
        const file = ev.target.files[0];
        const bannerEl = ev.target.closest(".cy_user_dashboard_profile_banner");
        ev.target.value = "";
        if (!file) return;
        const objectUrl = URL.createObjectURL(file);
        const aspectRatio = bannerEl && bannerEl.clientHeight
            ? bannerEl.clientWidth / bannerEl.clientHeight
            : 4;
        this.dialogService.add(BannerCropDialog, {
            imageUrl: objectUrl,
            aspectRatio,
            onConfirm: async (base64Data) => {
                URL.revokeObjectURL(objectUrl);
                try {
                    const result = await jsonrpc("/user/upload_banner", { banner_data: base64Data });
                    if (result.success) {
                        this.state.bannerUrl = `data:image/png;base64,${base64Data}`;
                    } else {
                        this.notification.add(`Upload failed: ${result.error || "Unknown error"}`, { type: "danger" });
                    }
                } catch (err) {
                    this.notification.add("Upload failed", { type: "danger" });
                }
            },
        });
    }

    async renderNonAdminUserDetails() {
        if (!session.is_admin) {
            const user = await this.orm.call('res.users', 'get_non_admin_user_details', [session.user_id[0]])
            this.state.nonAdmin = user
        }
    }

    onClickChangePassword() {
        this.env.services['action'].doAction({
            name: "Change Password",
            type: 'ir.actions.act_window',
            res_model: 'change.password.own',
            views: [[this.view_id, 'form']],
            target: 'new',
        });
    }

    /**
     * Mobile actions dropdown: run the picked action and close the menu
     * (Bootstrap 5 doesn't auto-close on item clicks). Closing is done via
     * DOM classes/aria: the webclient's `window.bootstrap` may not carry the
     * full BS5 Dropdown (asset bundle order can expose a partial build that
     * lacks getOrCreateInstance), so the instance route is optional and
     * never required.
     */
    onClickMobileAction(action, ev) {
        this.state.mobileMenuOpen = "";
        const dropdownEl = ev.currentTarget.closest(".dropdown");
        const menu = dropdownEl?.querySelector(".dropdown-menu");
        menu?.classList.remove("show", "showing");
        const toggle = dropdownEl?.querySelector("[data-bs-toggle='dropdown']");
        if (toggle) {
            toggle.setAttribute("aria-expanded", "false");
            const winDropdown = window.bootstrap?.Dropdown;
            if (winDropdown && typeof winDropdown.getOrCreateInstance === "function") {
                winDropdown.getOrCreateInstance(toggle).hide();
            }
        }
        if (action === "permissions") {
            this.onClickPermissions();
        } else if (action === "password") {
            this.onClickChangePassword();
        }
    }

    /**
     * Mobile menu: expand/collapse the Language/Timezone sections inside
     * the Settings dropdown (one section open at a time).
     */
    toggleMobileMenuSection(section) {
        this.state.mobileMenuOpen = this.state.mobileMenuOpen === section ? "" : section;
    }

    renderUserProfile() {
        this.orm.call('res.users', 'get_current_user_details').then((result) => {
            this.state.userProfile = result;
            this.userId = result.id;
        });
    }

    async renderShortcuts() {
        const domain = [['create_uid', '=', session.uid]];
        const fields = ['name', 'window_action_id', 'client_action_id', 'server_action_id', 'menu_id', 'xml_id', 'model', 'path', 'can_create', 'sequence'];
        try {
            let menuItems = [];
            try {
                menuItems = await this.orm.searchRead('shortcut.menu', domain, fields, { order: 'sequence, id' });
            } catch (orderError) {
                menuItems = await this.orm.searchRead('shortcut.menu', domain, fields, {});
            }
            const filtered = (menuItems || []).filter((item) =>
                item.window_action_id || item.client_action_id || item.server_action_id);
            // Guard against duplicate ids (would crash t-foreach with duplicate key).
            const seen = new Set();
            this.state.shortcuts = filtered.filter((item) => {
                const key = String(item.id);
                if (seen.has(key)) {
                    return false;
                }
                seen.add(key);
                return true;
            });
        } catch (error) {
            console.error('Error fetching shortcuts:', error);
        }
    }

    async onQuickAccessSortDrop({ element, previous, next }) {
        const getId = (node) => {
            try {
                if (!node || !node.dataset || !node.dataset.shortcutId) {
                    return false;
                }
                // Ignore the sortable placeholder even if it carries a cloned id.
                if (node.classList && node.classList.contains("cy_quick_access_placeholder")) {
                    return false;
                }
                return node.dataset.shortcutId;
            } catch (err) { }
            return false;
        };
        const draggedId = String(getId(element) || "");
        if (!draggedId) {
            return;
        }
        // Anchor-based reorder: never trust DOM order (placeholder is a clone
        // carrying the dragged id, so reading the DOM yields duplicates).
        const top = [...(this.state.shortcuts || [])];
        const from = top.findIndex((s) => String(s.id) === draggedId);
        if (from < 0) {
            return;
        }
        const [moved] = top.splice(from, 1);
        const prevId = previous ? String(getId(previous) || "") : "";
        const nextId = next ? String(getId(next) || "") : "";
        // previous/next are placeholder siblings; either may be the dragged
        // element itself when dropped back near its origin — ignore those.
        if (prevId && prevId !== draggedId) {
            const idx = top.findIndex((s) => String(s.id) === prevId);
            if (idx >= 0) {
                top.splice(idx + 1, 0, moved);
            } else {
                top.push(moved);
            }
        } else if (nextId && nextId !== draggedId) {
            const idx = top.findIndex((s) => String(s.id) === nextId);
            if (idx >= 0) {
                top.splice(idx, 0, moved);
            } else {
                top.push(moved);
            }
        } else if (previous || next) {
            // Both anchors missing/filtered (start/end edge): decide by which
            // side exists. previous-only => end, next-only => start.
            if (previous && !next) {
                top.push(moved);
            } else if (next && !previous) {
                top.unshift(moved);
            } else {
                top.push(moved);
            }
        } else {
            top.push(moved);
        }
        // Final safety: drop any accidental duplicate ids before render.
        const seen = new Set();
        const deduped = [];
        for (const s of top) {
            const key = String(s.id);
            if (seen.has(key)) {
                continue;
            }
            seen.add(key);
            deduped.push(s);
        }
        // Append any state items missing from the move (should not happen).
        for (const s of (this.state.shortcuts || [])) {
            if (!seen.has(String(s.id))) {
                seen.add(String(s.id));
                deduped.push(s);
            }
        }
        this.state.shortcuts = deduped;
        this.state.shortcuts.forEach((s, index) => {
            s.sequence = (index + 1) * 10;
        });
        try {
            await jsonrpc('/quick_access/reorder', {
                order: this.state.shortcuts.map((s) => ({ type: 'shortcut', id: s.id })),
            });
        } catch (err) {
            console.error('Error persisting shortcut order:', err);
        }
        this._suppressShortcutClick = true;
        setTimeout(() => {
            this._suppressShortcutClick = false;
        }, 100);
    }

    getShortcutIcon(shortcut) {
        try {
            const menuId = shortcut.menu_id ? shortcut.menu_id[0] : false;
            const menu = menuId ? this.menuService.getMenu(menuId) : null;
            if (menu && menu.appID) {
                return `/web/image/ir.ui.menu/${menu.appID}/web_icon_data`;
            }
        } catch {
            // fall through to folder icon
        }
        return '/cyllo_dashboard/static/src/img/folder.png';
    }

    getShortcutPath(shortcut) {
        // Full menu breadcrumb ("App / Section / Menu") for the tile tooltip.
        // Walks the parent chain from the loaded menu tree; falls back to the
        // stored path / name when the menu is missing or the lookup fails.
        const fallback = (shortcut && (shortcut.path || shortcut.name)) || "";
        const menuId = shortcut && shortcut.menu_id ? shortcut.menu_id[0] : false;
        if (!menuId) {
            return fallback;
        }
        try {
            const names = [];
            let menu = this.menuService.getMenu(menuId);
            let guard = 0;
            while (menu && menu.id && guard < 20) {
                names.unshift(menu.name);
                const parentId = menu.parent_id ? menu.parent_id[0] : false;
                menu = parentId ? this.menuService.getMenu(parentId) : null;
                guard++;
            }
            return names.length ? names.join(" / ") : fallback;
        } catch {
            return fallback;
        }
    }

    /**
     * Quick access search: live-filters the shortcut tiles by name.
     */
    onShortcutSearch(ev) {
        this.state.shortcutSearch = ev.target.value;
    }

    /**
     * Shortcuts visible in the Quick access grid (search-filtered).
     */
    get filteredShortcuts() {
        const term = (this.state.shortcutSearch || "").trim().toLowerCase();
        const list = this.state.shortcuts || [];
        if (!term) {
            return list;
        }
        return list.filter((s) => (s.name || "").toLowerCase().includes(term));
    }

    showShortcutAdd(shortcut) {
        // + quick-create badge for every shortcut whose model allows record
        // creation (can_create on shortcut.menu). No app-level exclusion:
        // top-level apps get the badge too when can_create is set.
        return Boolean(shortcut && shortcut.can_create);
    }

    onChangeLang(ev) {
        const langCode = typeof ev === 'string' ? ev : ev.target.value;
        this.orm.write("res.users", [this.userId], { 'lang': langCode });
        this.env.services['action'].doAction('reload_context');
    }

    onChangeTimezone(ev) {
        const tzCode = typeof ev === 'string' ? ev : ev.target.value;
        this.orm.write("res.users", [this.userId], { 'tz': tzCode });
        this.env.services['action'].doAction('reload_context');
    }

    async onClickShortCutMenu(data) {
        return this._openShortcutNow(data);
    }

    async _openShortcutNow(data) {
        if (this._suppressShortcutClick) {
            this._suppressShortcutClick = false;
            return;
        }
        if (data.menu_id) {
            const menu = this.menuService.getMenu(data.menu_id[0]);
            if (menu) {
                await this.menuService.selectMenu(menu);
                return;
            }
        }
        this.action.doAction(data.xml_id, {
            additionalContext: {
                active_id: false,
            },
        });
    }

    onClickShortCutAdd(shortcut) {
        // Open the quick-create form dialog with the exact shortcut name as
        // its title. Without a `name`, Odoo falls back to its default "Odoo"
        // dialog title (which Cyllo rebrands to "Cyllo").
        const model = shortcut && shortcut.model;
        if (model) {
            this.env.services['action'].doAction({
                type: 'ir.actions.act_window',
                res_model: model,
                views: [[false, 'form']],
                target: 'new',
                name: shortcut.name || model,
            });
        }
    }

    renderUserKpi() {
        this.orm.call('res.users', 'get_user_presence_kpi').then((result) => {
            this.state.userKpi = result || {};
        });
    }

    onClickUserKpi(filter) {
        const kpi = this.state.userKpi || {};
        const idsByFilter = {
            total: kpi.total_ids,
            internal: kpi.internal_ids,
            portal: kpi.portal_ids,
            online: kpi.online_ids,
            away: kpi.away_ids,
            offline: kpi.offline_ids,
        };
        const titles = {
            total: 'Total Users',
            internal: 'Internal Users',
            portal: 'Portal Users',
            online: 'Online Users',
            away: 'Away Users',
            offline: 'Offline Users',
        };
        const ids = idsByFilter[filter] || [];
        this.env.services['action'].doAction({
            name: titles[filter] || 'Users',
            type: 'ir.actions.act_window',
            res_model: 'res.users',
            views: [[false, 'list'], [false, 'form']],
            domain: [['id', 'in', ids.length ? ids : [0]]],
            target: 'current',
        });
    }

    pct(part, total) {
        if (!total) {
            return 0;
        }
        return Math.min(Math.max((part / total) * 100, 0), 100);
    }

    get onlineWidth() {
        const kpi = this.state.userKpi || {};
        return this.pct(kpi.online || 0, kpi.total || 0);
    }

    get awayWidth() {
        const kpi = this.state.userKpi || {};
        return this.pct(kpi.away || 0, kpi.total || 0);
    }

    get offlineWidth() {
        const kpi = this.state.userKpi || {};
        return this.pct(kpi.offline || 0, kpi.total || 0);
    }

    get storageUsedWidth() {
        const insights = this.state.performanceInsights || {};
        return this.pct(insights.used_memory || 0, insights.total_memory || 0);
    }

    get storageFreeWidth() {
        const insights = this.state.performanceInsights || {};
        const total = Number(insights.total_memory) || 0;
        const used = Number(insights.used_memory) || 0;
        return this.pct(Math.max(total - used, 0), total);
    }

    get storageFreeGb() {
        const insights = this.state.performanceInsights || {};
        const total = Number(insights.total_memory) || 0;
        const used = Number(insights.used_memory) || 0;
        return Math.round(Math.max(total - used, 0) * 100) / 100;
    }

    get ramUsedWidth() {
        const insights = this.state.performanceInsights || {};
        return Math.min(Math.max(Number(insights.ram_percent) || 0, 0), 100);
    }

    get ramFreeWidth() {
        return Math.max(100 - this.ramUsedWidth, 0);
    }

    get ramUsedGb() {
        const insights = this.state.performanceInsights || {};
        const total = Number(insights.total_ram) || 0;
        const percent = Number(insights.ram_percent) || 0;
        return Math.round(((total * percent) / 100) * 100) / 100;
    }

    get ramFreeGb() {
        const insights = this.state.performanceInsights || {};
        const total = Number(insights.total_ram) || 0;
        return Math.round(Math.max(total - this.ramUsedGb, 0) * 100) / 100;
    }

    get cpuUsedWidth() {
        const insights = this.state.performanceInsights || {};
        return Math.min(Math.max(Number(insights.total_cpu_usage) || 0, 0), 100);
    }

    get cpuIdleWidth() {
        return Math.max(100 - this.cpuUsedWidth, 0);
    }

    get cpuIdlePercent() {
        return Math.round(this.cpuIdleWidth * 10) / 10;
    }

    renderLoginUserDetails() {
        // Preview the latest logins for the card, but count the whole table
        // so the header badge reflects the real number of login records.
        Promise.all([
            this.orm.call('login.user.detail', 'search_read', [], {
                fields: ["name", "date_time", "ip_address", "res_user_id"],
                order: 'id desc', limit: 6,
            }),
            this.orm.call('login.user.detail', 'search_count', [[]], {}),
        ]).then(([result, total]) => {
            this.state.loginUserDetails = result;
            this.state.loginUserTotal = total;
        });
    }

    onClickLoginUser(login) {
        if (!login.id) {
            return;
        }
        this.env.services['action'].doAction({
            name: login.name || 'Login Detail',
            type: 'ir.actions.act_window',
            res_model: 'login.user.detail',
            res_id: login.id,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openAllLoginHistory() {
        this.action.doAction("cyllo_dashboard.action_view_login_details");
    }

    onQaScrollDown() {
        const grid = this.quickAccessGrid.el;
        if (grid) {
            grid.scrollTo({ top: grid.scrollHeight, behavior: "smooth" });
        }
    }

    openAllActivities() {
        document.body.click();
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Activities",
            res_model: "mail.activity",
            views: [[false, "list"], [false, "form"]],
            domain: [["user_id", "=", this.userId]],
            context: { force_search_count: 1 },
            target: "current",
        });
    }

    formatLoginDateTime(dateTime) {
        if (!dateTime) {
            return '';
        }
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'];
        const match = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}:\d{2}:\d{2})/.exec(dateTime);
        if (!match) {
            return dateTime;
        }
        const monthIndex = parseInt(match[2], 10) - 1;
        if (monthIndex < 0 || monthIndex > 11) {
            return dateTime;
        }
        return `${months[monthIndex]} ${match[3]} ${match[1]} ${match[4]}`;
    }

    async getActivities() {
        const groups = await this.env.services.orm.call("res.users", "systray_get_activities");
        let total = 0;
        for (const group of groups) {
            total += group.total_count || 0;
        }
        this.state.activities = groups;
    }

    openActivityGroup(group, filter = "all") {
        document.body.click();
        const context = {
            force_search_count: 1,
        };
        if (filter === "all") {
            context.search_default_activities_overdue = 1;
            context.search_default_activities_today = 1;
        } else {
            context["search_default_activities_" + filter] = 1;
        }
        var domain = [["activity_ids.user_id", "=", this.userId]];
        if (group.model === 'mail.activity') {
            domain = [["user_id", "=", this.userId]];
        }
        const views = this.availableViews(group);
        this.action.doAction({
            context,
            domain,
            name: group.name,
            res_model: group.model,
            search_view_id: [false],
            type: "ir.actions.act_window",
            views,
        }, {
            clearBreadcrumbs: true,
            viewType: group.view_type,
        });
    }

    /** Total activity records behind the grouped upcoming lists. */
    get activitiesTotalCount() {
        const activities = this.state.activities || [];
        return activities.reduce((total, group) => total + (group.total_count || 0), 0);
    }

    /** Total login records for the Login History card badge. */
    get loginHistoryCount() {
        const total = this.state.loginUserTotal;
        if (typeof total === 'number') {
            return total;
        }
        const logins = this.state.loginUserDetails;
        return Array.isArray(logins) ? logins.length : 0;
    }

    /** Switch between the Dashboard and Quick access views. */
    selectTab(tab) {
        if (this.state.activeTab === tab) {
            return;
        }
        this.state.activeTab = tab;
    }

    /** Position the sliding ink bar under the active tab button. */
    updateTabInk() {
        const wrap = this.tabBarRef.el;
        const btn =
            this.state.activeTab === "quickaccess" ? this.tabBtnQuickAccess.el : this.tabBtnDashboard.el;
        if (!wrap || !btn) {
            return;
        }
        const wrapRect = wrap.getBoundingClientRect();
        const btnRect = btn.getBoundingClientRect();
        const left = Math.round(btnRect.left - wrapRect.left);
        const width = Math.round(btnRect.width);
        if (left !== this.state.inkLeft || width !== this.state.inkWidth) {
            this.state.inkLeft = left;
            this.state.inkWidth = width;
        }
    }

    /** Row-level click: meetings open the calendar, activities the list. */
    openGroupRow(group) {
        if (group.type === "meeting") {
            this.handleGroupClick(group);
        } else {
            this.openActivityGroup(group);
        }
    }

    handleGroupClick(group) {
        if (group.type === "meeting") {
            const today = new Date();
            const start = today.toISOString().split("T")[0] + " 00:00:00";
            const end = today.toISOString().split("T")[0] + " 23:59:59";

            this.env.services.action.doAction({
                type: "ir.actions.act_window",
                name: "Meetings",
                res_model: "calendar.event",
                view_mode: "kanban",
                views: [[false, "kanban"], [false, "form"]],
                domain: [["start", ">=", start], ["start", "<=", end]],
                target: "current",
            });
        } else {
            this.openActivityGroup(group);
        }
    }

    availableViews(group) {
        return [[false, "kanban"], [false, "list"], [false, "form"], [false, "activity"],];
    }

    renderPerformanceInsight() {
        // Lightweight, non-blocking memory stats for the 'Memory' chart -
        // fetched for every user.
        jsonrpc('/performance/memory').then((memoryResult) => {
            Object.assign(this.state.performanceInsights, memoryResult);
        });
        // The heavy system/config insight is admin-only; skip the request
        // entirely for regular users so no profiling runs for them.
        if (session.is_admin) {
            jsonrpc('/performance').then((performanceResult) => {
                Object.assign(this.state.performanceInsights, performanceResult);
            });
        }
    }
}

UserDashboard.template = "UserDashboard";
UserDashboard.components = { DashboardKpi, AccountSettingsPanel };
actionRegistry.add('cyllo_user_dashboard', UserDashboard);
