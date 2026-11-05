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

const WEATHER_CACHE_KEY = "cyllo_dashboard_weather";

const WEATHER_CACHE_TTL = 48 * 60 * 60 * 1000;

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

        this.qaScrollState = useState({ canScrollDown: false });

        this.bannerFileInput = useRef("bannerFileInput");

        this.tabBarRef = useRef("tabBar");
        this.tabBtnDashboard = useRef("tabDashboard");

        useSortable({
            ref: this.quickAccessGrid,
            elements: ".cy_dashboard_qa_item",
            clone: false,
            ignore: ".cy_dashboard_qa_tile_add_icon",
            cursor: "grabbing",
            placeholderClasses: ["cy_dashboard_qa_placeholder"],
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

            activities: [],
            activityTypeCounts: [],
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
            this._syncOverviewMenu();

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

        useEffect(() => {
            this.updateTabInk();
        }, () => [this.state.activeTab, this.state.shortcuts.length]);

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

        const totalStorage = Number(insights.total_memory) || 0;
        const usedStorage = Number(insights.used_memory) || 0;
        const freeStorage = Math.max(totalStorage - usedStorage, 0);

        const totalRam = Number(insights.total_ram) || 0;
        const ramPercent = Number(insights.ram_percent) || 0;
        const usedRam = (totalRam * ramPercent) / 100;
        const freeRam = Math.max(totalRam - usedRam, 0);

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

        this.cleanupIdleTimer();
        var date = new Date();
        date.setMinutes(date.getMinutes() + this.minutes);
        var updatedTimestamp = date.getTime();

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

            if (distance < 0) {
                this.cleanupIdleTimer();
                $("#idle_timer").empty();
                $("#idle_timer").append("EXPIRED");
                location.replace("/web/session/logout")
            }
        }, 1000);

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

        try {
            const cached = JSON.parse(
                localStorage.getItem(WEATHER_CACHE_KEY + ":" + session.uid) || "null");
            if (cached && typeof cached.fetchedAt === "number"
                    && Date.now() - cached.fetchedAt < WEATHER_CACHE_TTL) {
                this.state.weatherDetails = cached;
            }
        } catch (e) {

        }
        jsonrpc('/weather/notification/check').then((data) => {
            if (data && data['cod'] == 200) {
                const temp = Math.floor(data.main.temp - 273);

                const details = {
                    city: data.name,
                    temp: temp,
                    description: data.weather[0].description,
                    weather: data.weather[0].main,
                    icon: data.weather[0].icon,

                    feelsLike: Math.round(data.main.feels_like - 273),
                    humidity: data.main.humidity,
                    windSpeed: Math.round(data.wind.speed * 10) / 10,

                    windDeg: data.wind.deg,

                    forecast: Array.isArray(data.forecast) ? data.forecast : [],
                    fetchedAt: Date.now(),
                };
                this.state.weatherDetails = details;
                try {
                    localStorage.setItem(
                        WEATHER_CACHE_KEY + ":" + session.uid,
                        JSON.stringify(details)
                    );
                } catch (e) {

                }
            }
        }).catch(() => {

        });
    }

    get weatherKpiIcon() {
        const group = String(this.state.weatherDetails.weather || "").toLowerCase();
        if (group === "clear") return "ri-sun-line";
        if (group === "clouds") return "ri-cloud-line";
        if (group === "rain") return "ri-rainy-line";
        if (group === "drizzle") return "ri-drizzle-line";
        if (group === "thunderstorm") return "ri-thunderstorms-line";
        if (group === "snow") return "ri-snowy-line";
        if (["mist", "haze", "fog", "smoke", "dust", "ash", "sand"].includes(group)) {
            return "ri-haze-2-line";
        }
        return "ri-cloudy-2-line";
    }

    get weatherKpiSegments() {
        const details = this.state.weatherDetails;
        if (details.temp === undefined) {
            return [];
        }
        const pos = Math.min(Math.max(((details.temp + 5) / 50) * 100, 0), 100);
        return [
            { width: pos, cls: 'bg-warning' },
            { width: 100 - pos, cls: 'bg-primary' },
        ];
    }

    get weatherKpiTitle() {
        const details = this.state.weatherDetails;
        const condition = String(details.description || "");
        const capitalized =
            condition.charAt(0).toUpperCase() + condition.slice(1);
        if (capitalized && details.city) {
            return capitalized + " in " + details.city;
        }
        if (capitalized) {
            return capitalized;
        }
        return details.city || "Weather";
    }

    get weatherKpiDetails() {
        const details = this.state.weatherDetails;
        if (details.temp === undefined) {
            return [];
        }
        const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
        let windDir = '';
        if (typeof details.windDeg === 'number') {
            windDir = ' ' + dirs[Math.round(details.windDeg / 45) % 8];
        }
        const wind = typeof details.windSpeed === 'number'
            ? details.windSpeed + ' m/s' + windDir
            : '—';
        const humidity = typeof details.humidity === 'number'
            ? details.humidity + '%'
            : '—';
        return [
            { icon: 'ri-windy-line', label: 'Wind', value: wind },
            { icon: 'ri-drop-line', label: 'Humidity', value: humidity },
        ];
    }

    get weatherKpiLegend() {
        const details = this.state.weatherDetails;
        const palette = ['bg-warning', 'bg-primary', 'bg-danger'];
        const forecast = Array.isArray(details.forecast) ? details.forecast : [];
        if (forecast.length) {
            return forecast.map((step, index) => ({
                count: step.temp,
                unit: '°C',
                label: step.time,
                cls: palette[index % palette.length],
                tip: 'Forecast at ' + step.time,
            }));
        }
        if (details.temp === undefined) {
            return [];
        }
        return [
            {
                count: details.feelsLike ?? details.temp,
                label: 'Feels Like (°C)',
                cls: 'bg-warning',
                tip: 'Feels like temperature',
            },
            {
                count: details.humidity ?? 0,
                label: 'Humidity (%)',
                cls: 'bg-primary',
                tip: 'Relative humidity',
            },
            {
                count: details.windSpeed ?? 0,
                label: 'Wind (m/s)',
                cls: 'bg-danger',
                tip: 'Wind speed',
            },
        ];
    }

    get profileCompaniesRow() {
        const service = this.env.services.company;
        const allowed = (service && service.allowedCompanies) || {};
        const activeIds = (service && service.activeCompanyIds) || [];
        const listed = activeIds.slice(0, 2).map((id) => allowed[id]).filter(Boolean);
        if (!listed.length) {
            return null;
        }

        const extra = Math.max(0, activeIds.length - listed.length);
        return {
            id: listed[0].id,
            names: listed.map((c) => c.name).join(', '),
            countText: extra
                ? ' + ' + extra + (extra === 1 ? ' company' : ' companies')
                : '',
            logos: listed.map((c) => ({
                id: c.id,
                src: '/web/image?model=res.company&field=logo&id=' + c.id,
            })),
        };
    }

    async onClickCompany() {
        const row = this.profileCompaniesRow;
        const companyId = (row && row.id)
            || (this.state.userProfile && this.state.userProfile.company_id);
        if (!companyId) {
            return;
        }
        this.env.services['action'].doAction({
            name: "Company",
            type: 'ir.actions.act_window',
            res_model: 'res.company',
            res_id: companyId,
            views: [[false, 'form']],
            target: 'current',
        });
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

    editBanner() {
        this.bannerFileInput.el?.click();
    }

    async uploadBanner(ev) {
        const file = ev.target.files[0];
        const bannerEl = ev.target.closest(".cy_dashboard_profile_banner");
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

    toggleMobileMenuSection(section) {
        this.state.mobileMenuOpen = this.state.mobileMenuOpen === section ? "" : section;
    }

    renderUserProfile() {
        this.orm.call('res.users', 'get_current_user_details').then((result) => {

            const companyService = this.env.services.company;
            const activeCompany = companyService && companyService.currentCompany;
            if (activeCompany && activeCompany.id) {
                result.company = activeCompany.name || result.company;
                result.company_id = activeCompany.id;
            }
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

                if (node.classList && node.classList.contains("cy_dashboard_qa_placeholder")) {
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

        const top = [...(this.state.shortcuts || [])];
        const from = top.findIndex((s) => String(s.id) === draggedId);
        if (from < 0) {
            return;
        }
        const [moved] = top.splice(from, 1);
        const prevId = previous ? String(getId(previous) || "") : "";
        const nextId = next ? String(getId(next) || "") : "";

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

        }
        return '/cyllo_dashboard/static/src/img/folder.png';
    }

    getShortcutPath(shortcut) {

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

    onShortcutSearch(ev) {
        this.state.shortcutSearch = ev.target.value;
    }

    get filteredShortcuts() {
        const term = (this.state.shortcutSearch || "").trim().toLowerCase();
        const list = this.state.shortcuts || [];
        if (!term) {
            return list;
        }
        return list.filter((s) => (s.name || "").toLowerCase().includes(term));
    }

    showShortcutAdd(shortcut) {

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

    async _syncOverviewMenu() {
        try {
            if (!this.menuService) {
                return;
            }
            const app = this.menuService
                .getApps()
                .find((m) => String(m.xmlid || "").endsWith("menu_cyllo_dashboard_root"));
            if (!app) {
                return;
            }
            const current = this.menuService.getCurrentApp();
            if (!current || current.appID !== app.appID) {
                this.menuService.setCurrentMenu(app);
            }
        } catch {

        }
    }

    async _openShortcutNow(data) {
        if (this._suppressShortcutClick) {
            this._suppressShortcutClick = false;
            return;
        }
        if (data.menu_id) {
            const menu = this.menuService.getMenu(data.menu_id[0]);
            if (menu && menu.actionID) {

                await this.action.doAction(menu.actionID);
                this.menuService.setCurrentMenu(menu);
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

    openUserProfile() {
        document.body.click();
        if (!this.userId) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: this.state.userProfile?.name || "User",
            res_model: "res.users",
            res_id: this.userId,
            views: [[false, "form"]],

            context: { form_view_ref: "base.view_users_form" },
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

        const userId = this.userId ?? this.userID;

        const [groups, typeRows] = await Promise.all([
            this.env.services.orm.call("res.users", "systray_get_activities"),

            this.env.services.orm.readGroup(
                "mail.activity",
                [["user_id", "=", userId]],
                ["id"],
                ["activity_type_id"]
            ),
        ]);
        this.state.activities = groups;
        const typeCounts = typeRows
            .map((row) => ({
                id: row.activity_type_id && row.activity_type_id[0],
                name: (row.activity_type_id && row.activity_type_id[1]) || "Other",
                count: row.activity_type_id_count || 0,
            }))
            .sort((a, b) => b.count - a.count);

        const typeIds = typeCounts.map((row) => row.id).filter((id) => id);
        let typeRecords = [];
        try {
            typeRecords = typeIds.length
                ? await this.env.services.orm.searchRead(
                    "mail.activity.type",
                    [["id", "in", typeIds]],

                    ["icon"]
                )
                : [];
        } catch (error) {
            typeRecords = [];
        }
        const iconById = {};
        for (const record of typeRecords) {
            iconById[record.id] = record.icon || "";
        }
        this.state.activityTypeCounts = typeCounts.map((row) => ({
            ...row,
            icon: iconById[row.id] || "",
        }));
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

            viewType: group.view_type,
        });
    }

    get activitiesTotalCount() {
        const activities = Array.isArray(this.state.activities) ? this.state.activities : [];
        return activities.reduce((total, group) => total + (group.total_count || 0), 0);
    }

    get activitiesLateTotal() {
        return (this.state.activities || []).reduce(
            (total, group) => total + (group.type === "activity" ? (group.overdue_count || 0) : 0), 0);
    }

    get activitiesTodayTotal() {
        return (this.state.activities || []).reduce(
            (total, group) => total + (group.type === "meeting" ? (group.meetings ? group.meetings.length : 0) : (group.today_count || 0)), 0);
    }

    get activitiesFutureTotal() {
        return (this.state.activities || []).reduce((total, group) => total + (group.planned_count || 0), 0);
    }

    get userKpiLegend() {
        const kpi = this.state.userKpi || {};
        const groups = [
            {
                filter: 'online',
                label: 'Online',
                cls: 'bg-primary',
                ids: kpi.online_ids,
                count: kpi.online,
            },
            {
                filter: 'away',
                label: 'Away',
                cls: 'bg-warning',
                ids: kpi.away_ids,
                count: kpi.away,
            },
            {
                filter: 'offline',
                label: 'Offline',
                cls: 'bg-danger',
                ids: kpi.offline_ids,
                count: kpi.offline,
            },
        ];
        return groups.map((group) => {
            const ids = Array.isArray(group.ids) ? group.ids : [];

            return {
                count: typeof group.count === 'number' ? group.count : ids.length,
                label: group.label,
                cls: group.cls,
                filter: group.filter,
                tip: 'View ' + group.label + ' users',
                avatars: group.count ? ids.slice(0, 2).map((id) => this.imageLoader(id)) : [],
            };
        });
    }

    get activityKpiLegend() {
        const groups = Array.isArray(this.state.activities) ? this.state.activities : [];

        const meetings = groups
            .filter((g) => g.type === "meeting")
            .reduce((sum, g) => sum + (g.meetings ? g.meetings.length : 0), 0);
        const palette = ["bg-primary", "bg-warning", "bg-danger"];

        const iconPalette = {
            "bg-primary": "cy_kpi_icon_primary",
            "bg-warning": "cy_kpi_icon_warning",
            "bg-danger": "cy_kpi_icon_danger",
        };
        const legend = [];
        if (meetings) {
            legend.push({
                count: meetings,
                label: "Meetings",
                cls: "bg-primary",
                icon: "ri-calendar-line",
                iconColor: iconPalette["bg-primary"],
                filter: "all",
                tip: "Open all upcoming activities",
            });
        }
        const types = this.state.activityTypeCounts || [];

        const topCount = meetings ? 1 : 2;
        types.slice(0, topCount).forEach((item, index) => {
            const cls = palette[(index + 1) % palette.length];
            legend.push({
                count: item.count,
                label: item.name,
                cls,

                icon: item.icon || "",
                iconColor: iconPalette[cls],
                filter: "all",
                tip: "Open all upcoming activities",
            });
        });
        const rest = types
            .slice(topCount)
            .reduce((sum, item) => sum + (item.count || 0), 0);
        if (rest) {

            const othersCls = meetings ? "bg-danger" : "bg-primary";
            legend.push({
                count: rest,
                label: "Others",
                cls: othersCls,
                icon: "ri-time-line",
                iconColor: iconPalette[othersCls],
                filter: "all",
                tip: "Open all upcoming activities",
            });
        }
        return legend;
    }

    get activityKpiSegments() {
        const legend = this.activityKpiLegend;
        const total = this.activitiesTotalCount || 0;
        let acc = 0;
        return legend.map((item, index) => {
            const isLast = index === legend.length - 1;
            const width = !item.count || !total
                ? 0
                : isLast
                    ? Math.round((100 - acc) * 10) / 10
                    : Math.round((item.count / total) * 1000) / 10;
            acc += width;
            return { width, cls: item.cls, filter: "all", tip: item.tip };
        });
    }

    get loginHistoryCount() {
        const total = this.state.loginUserTotal;
        if (typeof total === 'number') {
            return total;
        }
        const logins = this.state.loginUserDetails;
        return Array.isArray(logins) ? logins.length : 0;
    }

    selectTab(tab) {
        if (this.state.activeTab === tab) {
            return;
        }
        this.state.activeTab = tab;
    }

    updateTabInk() {
        const wrap = this.tabBarRef.el;
        const btn = this.tabBtnDashboard.el;
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

    openGroupRow(group) {
        if (group.type === "meeting") {
            this.handleGroupClick(group);
        } else if (group.model === "mail.activity") {
            this.openActivityGroup(group);
        } else {
            this.openActivityView(group);
        }
    }

    openActivityView(group) {
        document.body.click();
        this.action.doAction({
            context: { force_search_count: 1 },
            domain: [["activity_ids.user_id", "=", this.userId]],
            name: group.name,
            res_model: group.model,
            search_view_id: [false],
            type: "ir.actions.act_window",
            views: [[false, "activity"], [false, "list"], [false, "form"]],
        }, {

            viewType: "activity",
        });
    }

    getUpcomingIcon(group) {
        return group.type === "meeting" ? "ri-calendar-line" : "ri-calendar-check-line";
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

        jsonrpc('/performance/memory').then((memoryResult) => {
            Object.assign(this.state.performanceInsights, memoryResult);
        });

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
