/** @odoo-module */
import {registry} from "@web/core/registry";
import {Component, onWillStart, onWillUnmount, useRef, markup, useEffect} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {useState} from "@odoo/owl";
import {jsonrpc} from "@web/core/network/rpc_service";
import {session} from "@web/session";
import {CompanyDetailsDialog} from "@cyllo_dashboard/js/company_dialog";
import {BannerCropDialog} from "@cyllo_dashboard/js/banner_crop_dialog";
import { browser } from "@web/core/browser/browser";

const actionRegistry = registry.category("actions");

function htmlToText(html) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const result = [];
    function getText(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            result.push(node.textContent);
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.tagName === 'BR') {
                result.push('\n');
            }
            for (let childNode of node.childNodes) {
                getText(childNode);
            }
        }
    }

    getText(doc.body);
    return result.join('');
}

function textToHtml(text) {
    // Replace newline characters with <br> tags
    const htmlContent = text.replace(/\n/g, '<br>');
    return htmlContent;
}

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
        this.rootNonAdmin = useRef("root-non-admin");
        this.userID = session.uid;
        this.session = session;
        this.state = useState({
            shortcuts: {},
            loginUserDetails: {},
            userProfile: {},
            weatherDetails: {},
            activities: {},
            performanceInsights: {},
            nonAdmin: {},
            notifType: false,
            autoEdit: false,
            showLoading: true,
            bannerUrl: "/cyllo_dashboard/static/src/img/coverImage.png"
        })
        this.action = useService("action");
        this.getActivities();
        onWillStart(async () => {
            this.renderShortcuts();
            this.renderLoginUserDetails();
            this.renderNonAdminUserDetails();
            this.renderUserProfile();
            this.getIdleTime();
            this.renderWeatherNotification();
            this.renderPerformanceInsight();

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
        }, () => [this.state.performanceInsights.ram_percent])
        onWillUnmount(() => this.cleanupIdleTimer());
    }

    cleanupIdleTimer() {
        // Stop the countdown interval and detach the global activity handlers
        // so they don't accumulate across remounts of the dashboard.
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

    editSignature() {
        this.rootNonAdmin.el.querySelector('#signatureContent').style.display = 'none'
        this.rootNonAdmin.el.querySelector('#email-sign-textarea').classList.remove("d-none");
        this.rootNonAdmin.el.querySelector('#signatureSaveBtn').classList.remove("d-none");
        this.rootNonAdmin.el.querySelector('#signatureEditBtn').style.display = 'none';
    }

    saveSignature() {
        var textarea = this.rootNonAdmin.el.querySelector('#email-sign-textarea')
        var textContent = textarea.value;
        var htmlContent = textToHtml(textContent);
        this.orm.write("res.users", [this.userId], {'signature': htmlContent});
        this.env.services['action'].doAction('reload_context');
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
        const bannerEl = ev.target.closest(".cy-dashbaord-profile-banner");
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
                    const result = await jsonrpc("/user/upload_banner", {banner_data: base64Data});
                    if (result.success) {
                        this.state.bannerUrl = `data:image/png;base64,${base64Data}`;
                        this.notification.add("Banner updated successfully", {type: "success"});
                    } else {
                        this.notification.add(`Upload failed: ${result.error || "Unknown error"}`, {type: "danger"});
                    }
                } catch (err) {
                    this.notification.add("Upload failed", {type: "danger"});
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

    get markupSignature() {
        return markup(this.state.nonAdmin.signature);
    }

    get signature() {
        return htmlToText(this.state.nonAdmin.signature);
    }

    onClickGroups() {
        this.env.services['action'].doAction({
            name: 'Groups',
            type: 'ir.actions.act_window',
            res_model: 'res.groups',
            views: [[false, 'tree'], [false, 'form']],
            target: 'current',
            context: {'create': false, 'delete': false},
            domain: [['id', 'in', this.state.nonAdmin.groups_id]],
        });
    }

    onClickAccessRights() {
        this.env.services['action'].doAction({
            name: 'Access Rights',
            type: 'ir.actions.act_window',
            res_model: 'ir.model.access',
            views: [[false, 'tree']],
            target: 'current',
            context: {'create': false, 'delete': false},
            domain: [['id', 'in', this.state.nonAdmin.model_access]],
        });
    }

    onClickRecordRules() {
        this.env.services['action'].doAction({
            name: 'Record Rules',
            type: 'ir.actions.act_window',
            res_model: 'ir.rule',
            views: [[false, 'tree']],
            target: 'current',
            context: {'create': false, 'delete': false},
            domain: [['id', 'in', this.state.nonAdmin.rule_groups]],
        });
    }

    onClickCompany(company) {
        this.dialogService.add(CompanyDetailsDialog, {
            company: company,
            model: "res.company",
            title: company.name,
        })
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

    renderUserProfile() {
        this.orm.call('res.users', 'get_current_user_details').then((result) => {
            this.state.userProfile = result;
            this.userId = result.id;
        });
    }

    async renderShortcuts() {
        try {
            const menuItems = await this.orm.searchRead(
                'shortcut.menu',
                [['create_uid', '=', session.uid]],
                ['name', 'window_action_id', 'client_action_id', 'server_action_id', 'menu_id', 'xml_id', 'model', 'path', 'can_create']
            );
            this.state.shortcuts = menuItems.filter(item =>
                item.window_action_id || item.client_action_id || item.server_action_id);
        } catch (error) {
            console.error('Error fetching shortcuts:', error);
        }
    }

    isCompleteNameUnique(name) {
        const count = this.state.shortcuts.filter(shortcut => shortcut.name === name).length;
        return count === 1;
    }

    onChangeLang(ev) {
        this.orm.write("res.users", [this.userId], {'lang': ev.target.value});
        this.env.services['action'].doAction('reload_context');
    }

    onChangeTimezone(ev) {
        this.orm.write("res.users", [this.userId], {'tz': ev.target.value});
        this.env.services['action'].doAction('reload_context');
    }

    async onClickShortCutMenu(data) {
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

    onToggleAutoEdit(ev) {
        this.state.autoEdit = ev.target.checked
        this.orm.write("res.users", [this.userId], {'auto_edit': ev.target.checked});
        this.env.services['action'].doAction('reload_context');
    }

    onToggleAutoEditNonAdmin(ev) {
        this.state.autoEdit = ev.target.checked
        this.orm.call("res.users", 'toggle_auto_edit', [ev.target.checked]);
        this.env.services['action'].doAction('reload_context');
    }

    onClickShortCutAdd(model) {
        if (model) {
            this.env.services['action'].doAction({
                type: 'ir.actions.act_window',
                res_model: model,
                views: [[false, 'form']],
                target: 'new',
            });
        }
    }

    renderLoginUserDetails() {
        this.orm.call('login.user.detail', 'search_read', [], {
            fields: ["name", "date_time", "ip_address", "res_user_id"],
            order: 'id desc', limit: 5,
        }).then((result) => {
            this.state.loginUserDetails = result;
        });
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

    onClickAction(action, group) {
        document.body.click();
        if (action.action_xmlid) {
            this.env.services.action.doAction(action.action_xmlid);
        } else {
            let domain = [["activity_ids.user_id", "=", this.userId]];
            if (group.domain) {
                domain = domain.concat(group.domain);
            }
            this.env.services['action'].doAction({
                domain,
                name: group.name,
                res_model: group.model,
                type: "ir.actions.act_window",
                views: this.availableViews(group),
            }, {clearBreadcrumbs: true, viewType: "activity"});
        }
    }

    availableViews(group) {
        return [[false, "kanban"], [false, "list"], [false, "form"], [false, "activity"],];
    }

    onInputNotifType(ev) {
        this.orm.write("res.users", [this.userId], {'notification_type': ev.target.value});
        this.env.services['action'].doAction('reload_context');
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
actionRegistry.add('cyllo_user_dashboard', UserDashboard);
