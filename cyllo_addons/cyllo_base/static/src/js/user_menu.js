/** @odoo-module **/

import { useRef, Component, useState, useChildSubEnv, onWillStart, markup, useExternalListener } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import {
    SwitchCompanyMenu,
    SwitchCompanyItem,
} from "@web/webclient/switch_company_menu/switch_company_menu";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { isMacOS } from "@web/core/browser/feature_detection";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { escape } from "@web/core/utils/strings";
import { registry } from "@web/core/registry";

class ShortcutsFooterComponent extends Component {
    setup() {
        this.runShortcutKey = isMacOS() ? "CONTROL" : "ALT";
    }
}

ShortcutsFooterComponent.template = "web.UserMenu.ShortcutsFooterComponent";

patch(UserMenu.prototype, {
    setup() {
        super.setup();
        this.dropdown = useRef("dropdown")
        this.orm = useService('orm');
        this.userId = session.uid

        this.companyService = useService("company");
        // Reuse the real CompanySelector + SwitchCompanyItem (the actual
        // checkbox-row component core uses), just under our own toggle
        // instead of the standalone systray switcher's own Dropdown —
        // gives the exact standard look (incl. "Select all", added by the
        // cyllo_base/webclient/switchCompanyMenu.xml extension on top of
        // the base template everywhere it's used) without depending on
        // that other component's internal open/close state.
        this.companySelector = useState(
            new SwitchCompanyMenu.CompanySelector(this.companyService, SwitchCompanyMenu.toggleDelay)
        );
        useChildSubEnv({ companySelector: this.companySelector });
        this.availableCompanyIds = Object.values(this.companyService.allowedCompanies).map(
            (company) => company.id
        );

        this.state = useState({
            autoEdit: true,
            showCompanySwitcher: false,
        })
        this.companySwitcherRef = useRef("companySwitcher");
        useExternalListener(window, "click", (ev) => {
            if (this.state.showCompanySwitcher && !this.companySwitcherRef.el?.contains(ev.target)) {
                this.state.showCompanySwitcher = false;
            }
        });
        onWillStart(async () => {
            await this.orm.call('res.users', 'get_auto_edit_value').then((result) => {
                this.state.autoEdit = result;
            });
        })
    },

    get companyName() {
        return this.companyService.currentCompany?.name;
    },

    // Rather than fighting to trigger the standalone SwitchCompanyMenu
    // systray item's own internal Dropdown (its dropdown positions
    // relative to ITS OWN toggle button elsewhere in the navbar, and
    // forwarding a synthetic click to it doesn't actually open it), show
    // the real SwitchCompanyItem rows here, driven by our own toggle.
    get topLevelCompanies() {
        return Object.values(this.companyService.allowedCompaniesWithAncestors).filter(
            (company) => !company.parent_id
        );
    },

    get isSelectedAllCompanies() {
        return this.availableCompanyIds.every((id) =>
            this.companySelector.selectedCompaniesIds.includes(id)
        );
    },

    onSelectAllCompanies() {
        const companiesSelected = this.isSelectedAllCompanies
            ? [this.companyService.currentCompany.id]
            : this.availableCompanyIds;
        this.companyService.setCompanies(companiesSelected);
    },

    toggleCompanySwitcher(ev) {
        ev.stopPropagation();
        this.state.showCompanySwitcher = !this.state.showCompanySwitcher;
    },

    logOut() {
        localStorage.setItem('mainMenuVisibility', 'true')
        localStorage.setItem("cy_selected_app", false)
        localStorage.setItem("isSidebarOn", true)
        browser.location.href = "/web/session/logout";
    },

    shortCut() {
        this.env.services.command.openMainPalette({ FooterComponent: ShortcutsFooterComponent });
    },

    handleClick(event) {
        event.stopPropagation()
    },

    async profile() {
        const actionDescription = await this.env.services.orm.call("res.users", "action_systray_view_account");
        actionDescription.res_id = this.env.services.user.userId
        this.env.services.action.doAction(actionDescription, { clearBreadcrumbs: true, });
    },

    get command() {
        return isMacOS() ? "Cmd + K" : "Ctrl + K"
    },

    async handleEdit(ev) {
        this.state.autoEdit = !this.state.autoEdit
        await this.orm.call('res.users', 'toggle_auto_edit', [this.state.autoEdit]).then(() => {
            this.env.services['action'].doAction('reload_context');
        });
    },
})

UserMenu.components = { ...UserMenu.components, SwitchCompanyItem };

function documentationItem(env) {
    const documentationURL = "https://www.cyllo.com/docs";
    return {
        type: "item",
        id: "documentation",
        description: _t("Documentation"),
        href: documentationURL,
        callback: () => {
            browser.open(documentationURL, "_blank");
        },
        sequence: 10,
    };
}

function supportItem(env) {
    const url = session.support_url;
    return {
        type: "item",
        id: "support",
        description: _t("Support"),
        href: url,
        callback: () => {
            browser.open(url, "_blank");
        },
        sequence: 20,
    };
}

function shortCutsItem(env) {
    const translatedText = _t("Shortcuts");
    return {
        type: "item",
        id: "shortcuts",
        hide: env.isSmall,
        description: markup(
            `<span>${escape(translatedText)}
                    <span class="badge badge-secondary ms-4">${isMacOS() ? "CMD" : "CTRL"}+K</span>
                    </span>
                    `
        ),
        callback: () => {
            env.services.command.openMainPalette({ FooterComponent: ShortcutsFooterComponent });
        },
        sequence: 30,
    };
}

function separator() {
    return {
        type: "separator",
        sequence: 40,
    };
}

export function preferencesItem(env) {
    return {
        type: "item",
        id: "settings",
        description: _t("Preferences"),
        callback: async function () {
            const actionDescription = await env.services.orm.call("res.users", "action_get");
            actionDescription.res_id = env.services.user.userId;
            env.services.action.doAction(actionDescription);
        },
        sequence: 50,
    };
}

function cylloAccountItem(env) {
    return {
        type: "item",
        id: "account",
        description: _t("My Cyllo.com account"),
        callback: () => {
            browser.open("https://cyllo.com?auto_signin=1", "_blank");
        },
        sequence: 60,
    };
}

function logOutItem(env) {
    const route = "/web/session/logout";
    return {
        type: "item",
        id: "logout",
        description: markup(`<span><i class="ri-logout-box-r-line me-1"></i>Logout</span>`),
        href: `${browser.location.origin}${route}`,
        callback: () => {
            browser.location.href = route;
        },
        sequence: 70,
    };
}

registry
    .category("user_menuitems")
    .add("documentation", documentationItem)
    .add("support", supportItem)
    .add("shortcuts", shortCutsItem, { force: true })
    .add("separator", separator, { force: true })
    .add("log_out", logOutItem, { force: true })
    .add("cyllo_account", cylloAccountItem);