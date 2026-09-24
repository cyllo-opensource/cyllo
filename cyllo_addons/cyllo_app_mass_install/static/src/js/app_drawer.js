/** @odoo-module **/

import {registry} from "@web/core/registry";
import {useBus, useService} from "@web/core/utils/hooks";
import {
    Component,
    useSubEnv,
    onWillStart,
    onWillDestroy,
    useState,
    useRef,
    useEffect
} from "@odoo/owl";
import {Apps} from "./app";
import {SelectedAppDetails} from "./selected_app_details";
import {_t} from "@web/core/l10n/translation";

const COLORPICKER = ['cy-app-install-color__label--transparent', 'cy-app-install-color__label--red', 'cy-app-install-color__label--orange', 'cy-app-install-color__label--yellow', 'cy-app-install-color__label--blue', 'cy-app-install-color__label--sakura', 'cy-app-install-color__label--beige', 'cy-app-install-color__label--turquoise', 'cy-app-install-color__label--purple', 'cy-app-install-color__label--pink', 'cy-app-install-color__label--green', 'cy-app-install-color__label--lavender']

/**
 * AppDrawer Component for handling massive app installation.
 */
export class AppDrawer extends Component {
    static template = "cyllo_app_mass_install.massive";
    static components = {
        Apps,
        SelectedAppDetails,
    };

    /**
     * Setup function for initializing the component state and subscribing to events.
     */
    async setup() {
        this.showLoading = false
        this.env.bus.addEventListener("CY_INSTALL_ERR", () => {
            this.state.loading = false
        })
        useEffect(() => {
            // Function to display loading messages
            const showLoading = () => {
                const erpFacts = [
                    "Cyllo is an open-source ERP designed to streamline business processes.",
                    "Cyllo analytics boost decision-making and drive growth.",
                    "AI-powered Cyllo offers advanced BI for smarter insights.",
                    "Cyllo's modular design customizes ERP for Sales, HR, and more.",
                    "User-friendly Cyllo helps teams adapt quickly, improving productivity."
                ];
                var factIndex = 0;
                if (this.rootRef.el) {
                    $(this.rootRef.el.querySelector('#cy-app-install-cyllo-info')).text(erpFacts[factIndex]).fadeIn(500);
                }
                factIndex++;
                return setInterval(() => {
                    if (this.rootRef.el) {
                        $(this.rootRef.el.querySelector('#cy-app-install-cyllo-info')).fadeOut(500, function () {
                            $(this).text(erpFacts[factIndex]).fadeIn(500);
                        });
                        factIndex = (factIndex + 1) % erpFacts.length;
                    }
                }, 5000);
            }
            var timeSetter;
            if (this.showLoading) {
                timeSetter = showLoading()
            } else {
                clearInterval(timeSetter)
            }
            return () => {
                clearInterval(timeSetter)
            }
        }, () => [this.showLoading])
        this.ormService = useService("orm");
        this.menuService = useService("menu");
        this.notification = useService("notification");
        document.querySelector(".o_main_navbar")?.style.setProperty("display", "none");
        document.querySelector(".cy-menu-sidebar")?.style.setProperty("display", "none");
        // The sidebar element still exists in the DOM (just hidden), so
        // body:has(.cy-menu-sidebar) in sidebar.css still matches and keeps
        // reserving its padding-left on .o_action_manager. Clear it directly
        // to match the sidebar actually being hidden here.
        document.querySelector(".o_action_manager")?.style.setProperty("padding-left", "0", "important");
        this.rpc = useService("rpc");
        this.rootRef = useRef('root')
        this.radioState = useState({
            selectedColor: false
        })
        const storedApps = sessionStorage.getItem('apps');
        const storedAppsToInstall = sessionStorage.getItem('apps_to_install');
        const storedAppDetails = sessionStorage.getItem('app_details');
        let parsedApps;
        let parsedAppsToInstall;
        let parsedAppDetails;
        try {
            parsedApps = storedApps ? JSON.parse(storedApps) : [];
            parsedAppsToInstall = storedAppsToInstall ? JSON.parse(storedAppsToInstall) : [];
            parsedAppDetails = storedAppDetails ? JSON.parse(storedAppDetails) : [];
        } catch (error) {
            parsedApps = [];
            parsedAppsToInstall = [];
            parsedAppDetails = [];
        }
        this.state = useState({
            apps_to_install: parsedAppsToInstall,
            app_details: parsedAppDetails,
            loading: false,
            skipClicked: false,
            country: 0,
            states: [],
            user: false,
            apps: parsedApps,
            all_modules: false,
            moduleSearchTerm: [],
            technicalSearchTerm: [],
            categorySearchTerm: [],
            autoCompleteItems: [],
            updatedCategories: [],
            input_clear: false,
            highlightedId: null,
            image: null,
            imageMimeType: null,
            template: sessionStorage.getItem('template') || 'main_content',
        });
        this.orm = useService("orm");
        this.isHidden = false;
        onWillStart(async () => await this.load_data());
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.getStartedClicked = false
        useBus(this.env.bus, "update_selected_apps", (ev) => {
            this.select_app(ev.detail.app_id);
        });
        useSubEnv({
            get_loading: this.Loading.bind(this),
            skip: this.skip_first.bind(this),
            user_data: this.state.user_data,
            delete_app: this.delete_apps_from_list.bind(this)
        });
        onWillDestroy(() => setTimeout(() => {
            if (this.getStartedClicked) {
                window.location.reload()
            }
        }, 1000)
        )
        if (localStorage.getItem("Reload") === "true") {
            localStorage.setItem("Reload", false)
            sessionStorage.removeItem('template');
            sessionStorage.removeItem('apps');
            sessionStorage.removeItem('apps_to_install');
            sessionStorage.removeItem('app_details');
            document.querySelector(".o_main_navbar")?.style.setProperty("display", "flex");
            document.querySelector(".cy-menu-sidebar")?.style.setProperty("display", "flex");
            document.querySelector(".o_action_manager")?.style.removeProperty("padding-left");
            // Navigate through menuService.selectMenu() like a normal app
            // icon click, instead of actionService.doAction() directly —
            // doAction() bypasses menuService's current-app tracking, so
            // "Home" never shows as the active menu in the navbar/sidebar
            // afterward even though we're effectively on its dashboard.
            const homeApp = this.menuService
                .getApps()
                .find((app) => app.xmlid === "cyllo_dashboard.menu_cyllo_dashboard_root");
            if (homeApp) {
                await this.menuService.selectMenu(homeApp);
            } else {
                await this.action.doAction({
                    type: 'ir.actions.client',
                    name: _t('Dashboard'),
                    tag: 'cyllo_user_dashboard',
                });
            }
            this.env.bus.trigger("RESET_MENUS", {
                mainMenu: true,
            });
        }
    }

    /**
     * Sets the `showLoading` state to true, indicating that loading content should be displayed.
     */
    updateLoadingContent() {
        this.showLoading = true;
    }

    /**
     * Function to remove the deleted app from app_details and apps_to_install from the state.
     */
    delete_apps_from_list(app) {
        const updatedDetails = this.state.app_details.filter(detail => detail.id !== app.id);
        this.state.app_details = updatedDetails
        this.state.apps_to_install = this.state.apps_to_install.filter(value => value !== app.id)
        sessionStorage.setItem('apps_to_install', JSON.stringify(this.state.apps_to_install));
        sessionStorage.setItem('app_details', JSON.stringify(this.state.app_details));
    }

    /**
     * Sets the template in the component state and stores it in the session storage.
     *
     * @param {string} newTemplate - The new template to be set.
     */
    setTemplate(newTemplate) {
        this.state.template = newTemplate;
        sessionStorage.setItem('template', newTemplate);
    }

    /**
     * Navigates back to the main content template and triggers a soft reload.
     */
    back_first() {
        this.setTemplate("main_content");
    }

    /**
     * Signals that loading is in progress by updating the `loading` state.
     */
    Loading() {
        this.state.loading = !this.state.loading;
    }

    /**
     * Function to handle the skip action during the first phase.
     *
     * @param {Object} app - The selected app during the first phase.
     */
    skip_first(apps) {
        sessionStorage.removeItem('apps');
        this.state.loading = false;
        this.state.apps = apps
        sessionStorage.setItem('apps', JSON.stringify(apps));
        this.setTemplate("company");
    }

    /**
     * Navigates back to the "company" template.
     */
    back_second() {
        this.setTemplate("company")
    }

    /**
     * Loads data for the component, including user and company information.
     * Triggers the display of main navigation and left sidebar if it's the user's first time.
     */
    async load_data() {
        try {
            const category = await this.ormService.call(
                "ir.module.module",
                "custom_data",
                [,]
            );
            this.category = category[0]
            this.category_with_all_apps = category[1]
            this.state.category = this.category
            var user_data = await this.ormService.call("res.users", "custom_user_data", [this.ormService.user.userId])
            this.state.name = user_data.company_data[0].name
            this.state.id = user_data.company_data[0].id
            this.state.street = user_data.company_data[0].street
            this.state.street2 = user_data.company_data[0].street2
            this.state.country_state = user_data.company_data[0].state_id[0]
            this.state.city = user_data.company_data[0].city
            this.state.pin = user_data.company_data[0].zip
            this.state.vat = user_data.company_data[0].vat
            this.state.company_registry = user_data.company_data[0].company_registry
            this.state.countries = user_data.countries
            this.state.country = user_data.company_data[0].country_id[0]
            this.state.phone = user_data.company_data[0].phone
            this.state.mobile = user_data.company_data[0].mobile
            this.state.email = user_data.company_data[0].email
            this.state.website = user_data.company_data[0].website
            this.state.color = user_data.company_data[0].color
            this.state.user_data = user_data;
            this.state.states = user_data.country_state_data;
            if (user_data.first_time) {
                document.querySelector(".o_main_navbar")?.style.setProperty("display", "flex");
                document.querySelector(".cy-menu-sidebar")?.style.setProperty("display", "flex");
                document.querySelector(".o_action_manager")?.style.removeProperty("padding-left");
                await this.action.doAction({
                    type: 'ir.actions.act_window',
                    name: _t('User'),
                    res_model: 'res.users',
                    views: [
                        [false, 'form']
                    ],
                    view_mode: 'form',
                    res_id: this.ormService.user.userId,
                    target: 'current',
                })
            }
        } catch (error) {
        }
    }

    /**
     * Updates the search state and triggers autocomplete suggestions based on user input.
     */
    onSearch(ev) {
        if (this.state.highlightedId === null) {
            this.state.highlightedId = 'module'
        }
        if (ev.target && ev.target.value != "") {
            this.state.autoCompleteItems = [];
            this.state.autoCompleteItems.push(ev.target.value)
        } else if (ev.target && ev.target.value == "") {
            this.state.autoCompleteItems = [];
        }
        if (this.state.autoCompleteItems.length > 0) {
            const matchingCategories = [];
            if (!this.state.all_modules) {
                for (const appCategory of this.category) {
                    this.SearchSuggestionConditions(appCategory, matchingCategories);
                }
            } else {
                for (const appCategory of this.category_with_all_apps) {
                    this.SearchSuggestionConditions(appCategory, matchingCategories);
                }
            }
            if (matchingCategories.length == 0) {
                this.state.category = [];
            } else {
                this.state.category = matchingCategories;
            }
        } else {
            if (!this.state.all_modules) {
                this.state.category = this.category;
            } else {
                this.state.category = this.category_with_all_apps;
            }
        }
    }

    /**
     * Function containing the conditions for showing as suggestions based on module name, technical name and category name.
     */
    SearchSuggestionConditions(appCategory, matchingCategories) {
        if ((this.state.highlightedId == 'module') && (this.state.technicalSearchTerm.length == 0) && (this.state.categorySearchTerm.length == 0)) {
            var matchedApps = [];
            if (this.state.moduleSearchTerm.length === 0) {
                if (this.state.autoCompleteItems != "") {
                    matchedApps = appCategory.child_apps.filter(childApp =>
                        childApp.shortdesc.toLowerCase().includes(String(this.state.autoCompleteItems).toLowerCase())
                    );
                }
            } else {
                if (this.state.autoCompleteItems != "") {
                    const autoCompleteItems = String(this.state.autoCompleteItems).toLowerCase();
                    const currentTermApps = appCategory.child_apps.filter(childApp =>
                        childApp.shortdesc.toLowerCase().includes(autoCompleteItems)
                    );
                    for (const app of currentTermApps) {
                        if (!matchedApps.some(matchedApp => matchedApp.id === app.id)) {
                            matchedApps.push(app);
                        }
                    }
                }
                for (const term of this.state.moduleSearchTerm) {
                    const appsForTerm = appCategory.child_apps.filter(childApp =>
                        childApp.shortdesc.toLowerCase().includes(term)
                    );
                    for (const app of appsForTerm) {
                        if (!matchedApps.some(matchedApp => matchedApp.id === app.id)) {
                            matchedApps.push(app);
                        }
                    }
                }
            }
            if (matchedApps.length > 0) {
                const existingCategoryIndex = matchingCategories.findIndex(cat => cat.name === appCategory.name);
                if (existingCategoryIndex !== -1) {
                    const existingCategory = matchingCategories[existingCategoryIndex];
                    for (const app of matchedApps) {
                        if (!existingCategory.child_apps.some(existingApp => existingApp.id === app.id)) {
                            existingCategory.child_apps.push(app);
                        }
                    }
                } else {
                    const updatedCategory = {
                        ...appCategory,
                        child_apps: matchedApps
                    };
                    matchingCategories.push(updatedCategory);
                }
            }
        }
        if (this.state.highlightedId === 'category' &&
            this.state.technicalSearchTerm.length === 0 &&
            this.state.moduleSearchTerm.length === 0) {
            if (this.state.categorySearchTerm.length > 0) {
                for (const term of this.state.categorySearchTerm) {
                    if (appCategory.name.toLowerCase().includes(term)) {
                        const existingCategoryIndex = matchingCategories.findIndex(cat => cat.name === appCategory.name);
                        if (existingCategoryIndex === -1) {
                            matchingCategories.push(appCategory);
                        }
                    }
                }
            }
            if (this.state.autoCompleteItems != "") {
                const autoCompleteItemsLowerCase = String(this.state.autoCompleteItems).toLowerCase();
                if (appCategory.name.toLowerCase().includes(autoCompleteItemsLowerCase)) {
                    const existingCategoryIndex = matchingCategories.findIndex(cat => cat.name.toLowerCase() === appCategory.name.toLowerCase());
                    if (existingCategoryIndex === -1) {
                        matchingCategories.push(appCategory);
                    }
                }
            }
        }
        if ((this.state.highlightedId == 'technical') && (this.state.moduleSearchTerm.length == 0) && (this.state.categorySearchTerm.length == 0)) {
            var matchedApps = [];
            if (this.state.technicalSearchTerm.length === 0) {
                if (this.state.autoCompleteItems != "") {
                    matchedApps = appCategory.child_apps.filter(childApp =>
                        childApp.name.toLowerCase().includes(String(this.state.autoCompleteItems).toLowerCase())
                    );
                }
            } else {
                if (this.state.autoCompleteItems != "") {
                    const autoCompleteItems = String(this.state.autoCompleteItems).toLowerCase();
                    const currentTermApps = appCategory.child_apps.filter(childApp =>
                        childApp.name.toLowerCase().includes(autoCompleteItems)
                    );
                    for (const app of currentTermApps) {
                        if (!matchedApps.some(matchedApp => matchedApp.id === app.id)) {
                            matchedApps.push(app);
                        }
                    }
                }
                for (const term of this.state.technicalSearchTerm) {
                    const appsForTerm = appCategory.child_apps.filter(childApp =>
                        childApp.name.toLowerCase().includes(term)
                    );
                    for (const app of appsForTerm) {
                        if (!matchedApps.some(matchedApp => matchedApp.id === app.id)) {
                            matchedApps.push(app);
                        }
                    }
                }
            }
            if (matchedApps.length > 0) {
                const existingCategoryIndex = matchingCategories.findIndex(cat => cat.name === appCategory.name);
                if (existingCategoryIndex !== -1) {
                    const existingCategory = matchingCategories[existingCategoryIndex];
                    for (const app of matchedApps) {
                        if (!existingCategory.child_apps.some(existingApp => existingApp.id === app.id)) {
                            existingCategory.child_apps.push(app);
                        }
                    }
                } else {
                    const updatedCategory = {
                        ...appCategory,
                        child_apps: matchedApps
                    };
                    matchingCategories.push(updatedCategory);
                }
            }
        }
        if (
            this.state.highlightedId === 'module' &&
            this.state.technicalSearchTerm.length > 0 &&
            this.state.categorySearchTerm.length === 0
        ) {
            let matchedAppsTechnical = [];
            let matchedAppsModule = [];
            if (this.state.moduleSearchTerm.length === 0) {
                matchedAppsModule = appCategory.child_apps.filter(childApp =>
                    childApp.shortdesc.toLowerCase().includes(String(this.state.autoCompleteItems).toLowerCase())
                );
            } else {
                const autoCompleteItems = String(this.state.autoCompleteItems).toLowerCase();
                const currentTermApps = appCategory.child_apps.filter(childApp =>
                    childApp.shortdesc.toLowerCase().includes(autoCompleteItems)
                );
                if (autoCompleteItems.trim() !== "") {
                    matchedAppsModule.push(...currentTermApps);
                }
                for (const term of this.state.moduleSearchTerm) {
                    const appsForTerm = appCategory.child_apps.filter(childApp =>
                        childApp.shortdesc.toLowerCase().includes(term)
                    );
                    for (const app of appsForTerm) {
                        if (!matchedAppsModule.some(matchedApp => matchedApp.id === app.id)) {
                            matchedAppsModule.push(app);
                        }
                    }
                }
            }
            for (const technicalTerm of this.state.technicalSearchTerm) {
                const apps = appCategory.child_apps.filter(childApp =>
                    childApp.name.toLowerCase().includes(technicalTerm)
                );
                matchedAppsTechnical.push(...apps);
            }
            const commonApps = matchedAppsModule.filter(app =>
                matchedAppsTechnical.some(techApp => techApp.id === app.id)
            );
            if (commonApps.length > 0) {
                const updatedCategory = {
                    ...appCategory,
                    child_apps: commonApps
                };
                matchingCategories.push(updatedCategory);
            }
        }
        if ((this.state.highlightedId == 'module') && (this.state.categorySearchTerm.length > 0) && (this.state.technicalSearchTerm.length == 0)) {
            for (const categoryTerm of this.state.categorySearchTerm) {
                if (appCategory.name.toLowerCase().includes(categoryTerm)) {
                    let matchedApps = [];
                    if (this.state.moduleSearchTerm.length === 0) {
                        matchedApps = appCategory.child_apps.filter(childApp =>
                            childApp.shortdesc.toLowerCase().includes(String(this.state.autoCompleteItems).toLowerCase())
                        );
                    } else {
                        const autoCompleteItems = String(this.state.autoCompleteItems).toLowerCase();
                        const currentTermApps = appCategory.child_apps.filter(childApp =>
                            childApp.shortdesc.toLowerCase().includes(autoCompleteItems)
                        );
                        if (autoCompleteItems.trim() !== "") {
                            matchedApps.push(...currentTermApps);
                        }
                        for (const term of this.state.moduleSearchTerm) {
                            const appsForTerm = appCategory.child_apps.filter(childApp =>
                                childApp.shortdesc.toLowerCase().includes(term)
                            );
                            for (const app of appsForTerm) {
                                if (!matchedApps.some(matchedApp => matchedApp.id === app.id)) {
                                    matchedApps.push(app);
                                }
                            }
                        }
                    }
                    if (matchedApps.length > 0) {
                        const existingCategoryIndex = matchingCategories.findIndex(cat => cat.name === appCategory.name);
                        if (existingCategoryIndex !== -1) {
                            const existingCategory = matchingCategories[existingCategoryIndex];
                            for (const app of matchedApps) {
                                if (!existingCategory.child_apps.some(existingApp => existingApp.id === app.id)) {
                                    existingCategory.child_apps.push(app);
                                }
                            }
                        } else {
                            const updatedCategory = {
                                ...appCategory,
                                child_apps: matchedApps
                            };
                            matchingCategories.push(updatedCategory);
                        }
                    }
                }
            }
        }
        if ((this.state.highlightedId == 'technical') && (this.state.categorySearchTerm.length > 0) && (this.state.moduleSearchTerm.length == 0)) {
            for (const categoryTerm of this.state.categorySearchTerm) {
                if (appCategory.name.toLowerCase().includes(categoryTerm)) {
                    let matchedApps = [];
                    if (this.state.technicalSearchTerm.length === 0) {
                        matchedApps = appCategory.child_apps.filter(childApp =>
                            childApp.name.toLowerCase().includes(String(this.state.autoCompleteItems).toLowerCase())
                        );
                    } else {
                        const autoCompleteItems = String(this.state.autoCompleteItems).toLowerCase();
                        const currentTermApps = appCategory.child_apps.filter(childApp =>
                            childApp.name.toLowerCase().includes(autoCompleteItems)
                        );
                        if (autoCompleteItems.trim() !== "") {
                            matchedApps.push(...currentTermApps);
                        }
                        for (const term of this.state.technicalSearchTerm) {
                            const appsForTerm = appCategory.child_apps.filter(childApp =>
                                childApp.name.toLowerCase().includes(term)
                            );
                            for (const app of appsForTerm) {
                                if (!matchedApps.some(matchedApp => matchedApp.id === app.id)) {
                                    matchedApps.push(app);
                                }
                            }
                        }
                    }
                    if (matchedApps.length > 0) {
                        const existingCategoryIndex = matchingCategories.findIndex(cat => cat.name === appCategory.name);
                        if (existingCategoryIndex !== -1) {
                            const existingCategory = matchingCategories[existingCategoryIndex];
                            for (const app of matchedApps) {
                                if (!existingCategory.child_apps.some(existingApp => existingApp.id === app.id)) {
                                    existingCategory.child_apps.push(app);
                                }
                            }
                        } else {
                            const updatedCategory = {
                                ...appCategory,
                                child_apps: matchedApps
                            };
                            matchingCategories.push(updatedCategory);
                        }
                    }
                }
            }
        }
        if ((this.state.highlightedId == 'technical') && (this.state.moduleSearchTerm.length > 0) && (this.state.categorySearchTerm.length == 0)) {
            let matchedAppsTechnical = [];
            let matchedAppsModule = [];
            if (this.state.technicalSearchTerm.length === 0) {
                matchedAppsTechnical = appCategory.child_apps.filter(childApp =>
                    childApp.name.toLowerCase().includes(String(this.state.autoCompleteItems).toLowerCase())
                );
            } else {
                const autoCompleteItems = String(this.state.autoCompleteItems).toLowerCase();
                const currentTermApps = appCategory.child_apps.filter(childApp =>
                    childApp.name.toLowerCase().includes(autoCompleteItems)
                );
                if (autoCompleteItems.trim() !== "") {
                    matchedAppsTechnical.push(...currentTermApps);
                }
                for (const term of this.state.technicalSearchTerm) {
                    const appsForTerm = appCategory.child_apps.filter(childApp =>
                        childApp.name.toLowerCase().includes(term)
                    );
                    for (const app of appsForTerm) {
                        if (!matchedAppsTechnical.some(matchedApp => matchedApp.id === app.id)) {
                            matchedAppsTechnical.push(app);
                        }
                    }
                }
            }
            for (const moduleTerm of this.state.moduleSearchTerm) {
                const apps = appCategory.child_apps.filter(childApp =>
                    childApp.shortdesc.toLowerCase().includes(moduleTerm)
                );
                matchedAppsModule.push(...apps);
            }
            const commonApps = matchedAppsTechnical.filter(app =>
                matchedAppsModule.some(techApp => techApp.id === app.id)
            );
            if (commonApps.length > 0) {
                const updatedCategory = {
                    ...appCategory,
                    child_apps: commonApps
                };
                matchingCategories.push(updatedCategory);
            }
        }
        if ((this.state.highlightedId == 'category') && (this.state.moduleSearchTerm.length > 0) && (this.state.technicalSearchTerm.length == 0)) {
            const autoCompleteItems = this.state.autoCompleteItems ? String(this.state.autoCompleteItems).trim().toLowerCase() : '';
            let searchTerm = [];
            if (this.state.categorySearchTerm.length > 0) {
                searchTerm = [...this.state.categorySearchTerm];
            }
            if (autoCompleteItems !== '') {
                searchTerm.push(autoCompleteItems);
            }
            for (const term of searchTerm) {
                for (const moduleTerm of this.state.moduleSearchTerm) {
                    if (appCategory.name.toLowerCase().includes(term)) {
                        let matchedApps = [];
                        matchedApps = appCategory.child_apps.filter(childApp =>
                            childApp.shortdesc.toLowerCase().includes(moduleTerm)
                        );
                        if (matchedApps.length > 0) {
                            const existingCategoryIndex = matchingCategories.findIndex(cat => cat.name === appCategory.name);
                            if (existingCategoryIndex !== -1) {
                                const existingCategory = matchingCategories[existingCategoryIndex];
                                for (const app of matchedApps) {
                                    if (!existingCategory.child_apps.some(existingApp => existingApp.id === app.id)) {
                                        existingCategory.child_apps.push(app);
                                    }
                                }
                            } else {
                                matchingCategories.push({
                                    ...appCategory,
                                    child_apps: matchedApps
                                });
                            }
                        }
                    }
                }
            }
        }
        if ((this.state.highlightedId == 'category') && (this.state.technicalSearchTerm.length > 0) && (this.state.moduleSearchTerm.length == 0)) {
            const autoCompleteItems = this.state.autoCompleteItems ? String(this.state.autoCompleteItems).trim().toLowerCase() : '';
            let searchTerm = [];
            if (this.state.categorySearchTerm.length > 0) {
                searchTerm = [...this.state.categorySearchTerm];
            }
            if (autoCompleteItems !== '') {
                searchTerm.push(autoCompleteItems);
            }
            for (const term of searchTerm) {
                for (const technicalTerm of this.state.technicalSearchTerm) {
                    if (appCategory.name.toLowerCase().includes(term)) {
                        let matchedApps = [];
                        matchedApps = appCategory.child_apps.filter(childApp =>
                            childApp.name.toLowerCase().includes(technicalTerm)
                        );
                        if (matchedApps.length > 0) {
                            const existingCategoryIndex = matchingCategories.findIndex(cat => cat.name === appCategory.name);
                            if (existingCategoryIndex !== -1) {
                                const existingCategory = matchingCategories[existingCategoryIndex];
                                for (const app of matchedApps) {
                                    if (!existingCategory.child_apps.some(existingApp => existingApp.id === app.id)) {
                                        existingCategory.child_apps.push(app);
                                    }
                                }
                            } else {
                                matchingCategories.push({
                                    ...appCategory,
                                    child_apps: matchedApps
                                });
                            }
                        }
                    }
                }
            }
        }
        if (
            this.state.highlightedId === 'module' &&
            this.state.technicalSearchTerm.length > 0 &&
            this.state.categorySearchTerm.length > 0
        ) {
            let matchedApps = [];
            if (this.state.moduleSearchTerm.length === 0) {
                if (this.state.autoCompleteItems != "") {
                    matchedApps = appCategory.child_apps.filter(childApp =>
                        this.state.autoCompleteItems.some(term => childApp.shortdesc.toLowerCase().includes(term)) &&
                        this.state.technicalSearchTerm.some(term => childApp.name.toLowerCase().includes(term))
                    );
                }
            } else {
                if (this.state.autoCompleteItems != "") {
                    matchedApps = appCategory.child_apps.filter(childApp =>
                        (this.state.moduleSearchTerm.some(term => childApp.shortdesc.toLowerCase().includes(term)) ||
                            this.state.autoCompleteItems.some(term => childApp.shortdesc.toLowerCase().includes(term))) &&
                        this.state.technicalSearchTerm.some(term => childApp.name.toLowerCase().includes(term))
                    );
                } else {
                    matchedApps = appCategory.child_apps.filter(childApp =>
                        this.state.moduleSearchTerm.some(term => childApp.shortdesc.toLowerCase().includes(term)) &&
                        this.state.technicalSearchTerm.some(term => childApp.name.toLowerCase().includes(term))
                    );
                }
            }
            if (matchedApps.length > 0 &&
                this.state.categorySearchTerm.some(term => appCategory.name.toLowerCase().includes(term))) {
                matchingCategories.push({
                    ...appCategory,
                    child_apps: matchedApps
                });
            }
        }
        if ((this.state.highlightedId == 'technical') && (this.state.moduleSearchTerm.length > 0) && (this.state.categorySearchTerm.length > 0)) {
            let matchedApps = [];
            if (this.state.technicalSearchTerm.length === 0) {
                if (this.state.autoCompleteItems != "") {
                    matchedApps = appCategory.child_apps.filter(childApp =>
                        this.state.autoCompleteItems.some(term => childApp.name.toLowerCase().includes(term)) &&
                        this.state.moduleSearchTerm.some(term => childApp.shortdesc.toLowerCase().includes(term))
                    );
                }
            } else {
                if (this.state.autoCompleteItems != "") {
                    matchedApps = appCategory.child_apps.filter(childApp =>
                        (this.state.technicalSearchTerm.some(term => childApp.name.toLowerCase().includes(term)) ||
                            this.state.autoCompleteItems.some(term => childApp.name.toLowerCase().includes(term))) &&
                        this.state.moduleSearchTerm.some(term => childApp.shortdesc.toLowerCase().includes(term))
                    );
                } else {
                    matchedApps = appCategory.child_apps.filter(childApp =>
                        this.state.technicalSearchTerm.some(term => childApp.name.toLowerCase().includes(term)) &&
                        this.state.moduleSearchTerm.some(term => childApp.shortdesc.toLowerCase().includes(term))
                    );
                }
            }

            if (matchedApps.length > 0 &&
                this.state.categorySearchTerm.some(term => appCategory.name.toLowerCase().includes(term))) {
                matchingCategories.push({
                    ...appCategory,
                    child_apps: matchedApps
                });
            }
        }
        if (
            this.state.highlightedId === 'category' &&
            this.state.moduleSearchTerm.length > 0 &&
            this.state.technicalSearchTerm.length > 0
        ) {
            let matchedApps = [];
            matchedApps = appCategory.child_apps.filter(childApp =>
                this.state.moduleSearchTerm.some(term => childApp.shortdesc.toLowerCase().includes(term)) &&
                this.state.technicalSearchTerm.some(term => childApp.name.toLowerCase().includes(term))
            );
            const autoCompleteItems = this.state.autoCompleteItems ? String(this.state.autoCompleteItems).trim().toLowerCase() : '';
            let searchTerms = [];
            if (this.state.categorySearchTerm.length > 0) {
                searchTerms = [...this.state.categorySearchTerm];
            }
            if (autoCompleteItems !== '') {
                searchTerms.push(autoCompleteItems);
            }
            if (matchedApps.length > 0 &&
                searchTerms.some(term => appCategory.name.toLowerCase().includes(term))) {
                matchingCategories.push({
                    ...appCategory,
                    child_apps: matchedApps
                });
            }
        }
    }

    /**
     * Hides the autocomplete dropdown when the search input loses focus.
     */
    onInputBlur() {
        const autoComplete = this.rootRef.el.querySelector("#cy-app-install-autocomplete");
        if (autoComplete) {
            setTimeout(function () {
                autoComplete.style.display = 'none';
                this.state.highlightedId = 'module'
            }.bind(this), 200);
        }
    }

    /**
     * Displays the autocomplete dropdown when the search input gains focus.
     */
    onInputFocus() {
        const autoComplete = this.rootRef.el.querySelector("#cy-app-install-autocomplete");
        if (autoComplete) {
            autoComplete.style.display = 'block';
        }
    }

    /**
     * Sets the highlighted search category and triggers the input click event.
     */
    SuggestionClick(ev, items) {
        this.state.highlightedId = ev
        this.onInputClick();
    }

    /**
     * keydown function of the search input
     */
    onInputKeydown(ev) {
        if (this.state.moduleSearchTerm.length > 0 || this.state.technicalSearchTerm.length > 0 || this.state.categorySearchTerm.length > 0 || (ev && 'key' in ev && ev.key === 'Enter')) {
            if (ev && typeof ev.key !== 'undefined') {
                var searchTerm = ev.target.value.toLowerCase();
            } else {
                var searchTerm = this.state.autoCompleteItems;
            }
            if (ev && 'key' in ev && ev.key === 'Enter') {
                this.state.autoCompleteItems = [];
                if (this.state.highlightedId === 'module' && !this.state.moduleSearchTerm.includes(searchTerm)) {
                    this.state.moduleSearchTerm.push(searchTerm);
                }
                if (this.state.highlightedId === 'technical' && !this.state.technicalSearchTerm.includes(searchTerm)) {
                    this.state.technicalSearchTerm.push(searchTerm);
                }
                if (this.state.highlightedId === 'category' && !this.state.categorySearchTerm.includes(searchTerm)) {
                    this.state.categorySearchTerm.push(searchTerm);
                }
                ev.target.value = ""
            }
            if (ev && 'key' in ev && ev.target.value == "" && ev.key === 'Backspace') {
                if ((this.state.moduleSearchTerm.length > 0) && (this.state.technicalSearchTerm.length == 0) && (this.state.categorySearchTerm.length == 0)) {
                    this.state.moduleSearchTerm = [];
                } else if ((this.state.technicalSearchTerm.length > 0) && (this.state.moduleSearchTerm.length == 0) && (this.state.categorySearchTerm.length == 0)) {
                    this.state.technicalSearchTerm = [];
                } else if ((this.state.categorySearchTerm.length > 0) && (this.state.moduleSearchTerm.length == 0) && (this.state.technicalSearchTerm.length == 0)) {
                    this.state.categorySearchTerm = [];
                } else if ((this.state.technicalSearchTerm.length > 0) && (this.state.moduleSearchTerm.length > 0) && (this.state.categorySearchTerm.length == 0)) {
                    this.state.technicalSearchTerm = [];
                } else if ((this.state.categorySearchTerm.length > 0) && (this.state.moduleSearchTerm.length > 0) && (this.state.technicalSearchTerm.length == 0)) {
                    this.state.categorySearchTerm = [];
                } else if ((this.state.categorySearchTerm.length > 0) && (this.state.technicalSearchTerm.length > 0) && (this.state.moduleSearchTerm.length == 0)) {
                    this.state.categorySearchTerm = [];
                } else if ((this.state.categorySearchTerm.length > 0) && (this.state.technicalSearchTerm.length > 0) && (this.state.moduleSearchTerm.length > 0)) {
                    this.state.categorySearchTerm = [];
                }
            }
            const matchingCategories = [];
            if (!this.state.all_modules) {
                for (const appCategory of this.category) {
                    this.SearchConditions(appCategory, matchingCategories);
                }
            } else {
                for (const appCategory of this.category_with_all_apps) {
                    this.SearchConditions(appCategory, matchingCategories);
                }
            }
            if (matchingCategories.length == 0) {
                this.state.category = [];
            } else {
                this.state.category = matchingCategories;
            }
        }
        if (ev && 'key' in ev && ev.key === 'ArrowUp') {
            if (this.state.highlightedId === 'module') {
                this.state.highlightedId = 'category';
            } else if (this.state.highlightedId === 'technical') {
                this.state.highlightedId = 'module';
            } else if (this.state.highlightedId === 'category') {
                this.state.highlightedId = 'technical';
            }
            this.onSearch(this.state.autoCompleteItems)
        }
        if (ev && 'key' in ev && ev.key === 'ArrowDown') {
            if (this.state.highlightedId === 'module') {
                this.state.highlightedId = 'technical';
            } else if (this.state.highlightedId === 'technical') {
                this.state.highlightedId = 'category';
            } else if (this.state.highlightedId === 'category') {
                this.state.highlightedId = 'module';
            }
            this.onSearch(this.state.autoCompleteItems)
        }
        if (this.state.moduleSearchTerm.length == 0 && this.state.technicalSearchTerm.length == 0 && this.state.categorySearchTerm.length == 0) {
            if (!this.state.all_modules) {
                this.state.category = this.category;
            } else {
                this.state.category = this.category_with_all_apps;
            }
        }
    }

    /**
     * Updates the highlighted search category based on the user's mouseover action.
     */
    onMouseOver(ev) {
        if (ev === 'module') {
            this.state.highlightedId = 'module'
        } else if (ev === 'technical') {
            this.state.highlightedId = 'technical'
        } else if (ev === 'category') {
            this.state.highlightedId = 'category'
        }
        this.onSearch(this.state.autoCompleteItems)
    }

    /**
     * Clears the search terms for module and triggers a keydown event.
     */
    clearSearchModuleTerm() {
        this.state.moduleSearchTerm = [];
        this.onInputKeydown();
    }

    /**
     * Clears the search terms for technical and triggers a keydown event.
     */
    clearSearchTechnicalTerm() {
        this.state.technicalSearchTerm = [];
        this.onInputKeydown();

    }

    /**
     * Clears the search terms for category and triggers a keydown event.
     */
    clearSearchCategoryTerm() {
        this.state.categorySearchTerm = [];
        this.onInputKeydown();
    }

    /**
     * onChange function of the selection field apps and all
     */
    onAllAppsClick(ev) {
        if (ev.target.value == "All") {
            this.state.all_modules = true
            this.state.category = this.category_with_all_apps
        } else {
            this.state.all_modules = false
        }
        this.onInputKeydown();
    }

    /**
     * Click function of the search icon
     */
    onInputClick(ev) {
        if (this.state.keys) {
            var searchTerm = this.state.keys.toLowerCase();
            this.state.autoCompleteItems = [];
            if (this.state.highlightedId === 'module' && !this.state.moduleSearchTerm.includes(searchTerm)) {
                this.state.moduleSearchTerm.push(searchTerm);
            }
            if (this.state.highlightedId === 'technical' && !this.state.technicalSearchTerm.includes(searchTerm)) {
                this.state.technicalSearchTerm.push(searchTerm);
            }
            if (this.state.highlightedId === 'category' && !this.state.categorySearchTerm.includes(searchTerm)) {
                this.state.categorySearchTerm.push(searchTerm);
            }
            this.state.keys = ""
            const matchingCategories = [];
            if (!this.state.all_modules) {
                for (const appCategory of this.category) {
                    this.SearchConditions(appCategory, matchingCategories);
                }
            } else {
                for (const appCategory of this.category_with_all_apps) {
                    this.SearchConditions(appCategory, matchingCategories);
                }
            }
            if (matchingCategories.length == 0) {
                this.state.category = [];
            } else {
                this.state.category = matchingCategories;
            }
        }
        if (this.state.moduleSearchTerm.length == 0 && this.state.technicalSearchTerm.length == 0 && this.state.categorySearchTerm.length == 0) {
            if (!this.state.all_modules) {
                this.state.category = this.category;
            } else {
                this.state.category = this.category_with_all_apps;
            }
        }
    }

    /**
     * Function containing the conditions for searching module name, technical name and category name.
     */
    SearchConditions(appCategory, matchingCategories) {
        if ((this.state.moduleSearchTerm.length > 0) && (this.state.technicalSearchTerm.length == 0) && (this.state.categorySearchTerm.length == 0)) {
            for (const term of this.state.moduleSearchTerm) {
                let matchedApps = [];
                matchedApps = appCategory.child_apps.filter(childApp =>
                    childApp.shortdesc.toLowerCase().includes(term)
                );
                if (matchedApps.length > 0) {
                    const existingCategoryIndex = matchingCategories.findIndex(cat => cat.name === appCategory.name);
                    if (existingCategoryIndex !== -1) {
                        const existingCategory = matchingCategories[existingCategoryIndex];
                        for (const app of matchedApps) {
                            if (!existingCategory.child_apps.some(existingApp => existingApp.id === app.id)) {
                                existingCategory.child_apps.push(app);
                            }
                        }
                    } else {
                        const updatedCategory = {
                            ...appCategory,
                            child_apps: matchedApps
                        };
                        matchingCategories.push(updatedCategory);
                    }
                }
            }
        }
        if ((this.state.technicalSearchTerm.length > 0) && (this.state.moduleSearchTerm.length == 0) && (this.state.categorySearchTerm.length == 0)) {
            for (const term of this.state.technicalSearchTerm) {
                let matchedApps = [];
                matchedApps = appCategory.child_apps.filter(childApp =>
                    childApp.name.toLowerCase().includes(term)
                );
                if (matchedApps.length > 0) {
                    const existingCategoryIndex = matchingCategories.findIndex(cat => cat.name === appCategory.name);
                    if (existingCategoryIndex !== -1) {
                        const existingCategory = matchingCategories[existingCategoryIndex];
                        for (const app of matchedApps) {
                            if (!existingCategory.child_apps.some(existingApp => existingApp.id === app.id)) {
                                existingCategory.child_apps.push(app);
                            }
                        }
                    } else {
                        const updatedCategory = {
                            ...appCategory,
                            child_apps: matchedApps
                        };
                        matchingCategories.push(updatedCategory);
                    }
                }
            }
        }
        if ((this.state.moduleSearchTerm.length > 0) && (this.state.technicalSearchTerm.length > 0) && (this.state.categorySearchTerm.length === 0)) {
            let matchedAppsTechnical = [];
            let matchedAppsModule = [];
            for (const term of this.state.technicalSearchTerm) {
                const appsForTerm = appCategory.child_apps.filter(childApp =>
                    childApp.name.toLowerCase().includes(term)
                );
                for (const app of appsForTerm) {
                    if (!matchedAppsTechnical.some(matchedApp => matchedApp.id === app.id)) {
                        matchedAppsTechnical.push(app);
                    }
                }
            }
            for (const moduleTerm of this.state.moduleSearchTerm) {
                const apps = appCategory.child_apps.filter(childApp =>
                    childApp.shortdesc.toLowerCase().includes(moduleTerm)
                );
                matchedAppsModule.push(...apps);
            }
            const commonApps = matchedAppsTechnical.filter(app =>
                matchedAppsModule.some(techApp => techApp.id === app.id)
            );
            if (commonApps.length > 0) {
                const updatedCategory = {
                    ...appCategory,
                    child_apps: commonApps
                };
                matchingCategories.push(updatedCategory);
            }
        }
        if ((this.state.categorySearchTerm.length > 0) && (this.state.technicalSearchTerm.length > 0) && (this.state.moduleSearchTerm.length == 0)) {
            for (const categoryTerm of this.state.categorySearchTerm) {
                for (const technicalTerm of this.state.technicalSearchTerm) {
                    if (appCategory.name.toLowerCase().includes(categoryTerm)) {
                        let matchedApps = [];
                        matchedApps = appCategory.child_apps.filter(childApp =>
                            childApp.name.toLowerCase().includes(technicalTerm)
                        );
                        if (matchedApps.length > 0) {
                            const existingCategoryIndex = matchingCategories.findIndex(cat => cat.name === appCategory.name);
                            if (existingCategoryIndex !== -1) {
                                const existingCategory = matchingCategories[existingCategoryIndex];
                                for (const app of matchedApps) {
                                    if (!existingCategory.child_apps.some(existingApp => existingApp.id === app.id)) {
                                        existingCategory.child_apps.push(app);
                                    }
                                }
                            } else {
                                const updatedCategory = {
                                    ...appCategory,
                                    child_apps: matchedApps
                                };
                                matchingCategories.push(updatedCategory);
                            }
                        }
                    }
                }
            }
        }
        if ((this.state.categorySearchTerm.length > 0) && (this.state.moduleSearchTerm.length > 0) && (this.state.technicalSearchTerm.length == 0)) {
            for (const categoryTerm of this.state.categorySearchTerm) {
                for (const moduleTerm of this.state.moduleSearchTerm) {
                    if (appCategory.name.toLowerCase().includes(categoryTerm)) {
                        let matchedApps = [];
                        matchedApps = appCategory.child_apps.filter(childApp =>
                            childApp.shortdesc.toLowerCase().includes(moduleTerm)
                        );
                        if (matchedApps.length > 0) {
                            const existingCategoryIndex = matchingCategories.findIndex(cat => cat.name === appCategory.name);
                            if (existingCategoryIndex !== -1) {
                                const existingCategory = matchingCategories[existingCategoryIndex];
                                for (const app of matchedApps) {
                                    if (!existingCategory.child_apps.some(existingApp => existingApp.id === app.id)) {
                                        existingCategory.child_apps.push(app);
                                    }
                                }
                            } else {
                                const updatedCategory = {
                                    ...appCategory,
                                    child_apps: matchedApps
                                };
                                matchingCategories.push(updatedCategory);
                            }
                        }
                    }
                }
            }
        }
        if ((this.state.categorySearchTerm.length > 0) && (this.state.technicalSearchTerm.length == 0) && (this.state.moduleSearchTerm.length == 0)) {
            for (const term of this.state.categorySearchTerm) {
                if (appCategory.name.toLowerCase().includes(term)) {
                    const existingCategoryIndex = matchingCategories.findIndex(cat => cat.name === appCategory.name);
                    if (existingCategoryIndex === -1) {
                        matchingCategories.push(appCategory);
                    }
                }
            }
        }
        if ((this.state.moduleSearchTerm.length > 0) && (this.state.technicalSearchTerm.length > 0) && (this.state.categorySearchTerm.length > 0)) {
            let matchedApps = [];
            matchedApps = appCategory.child_apps.filter(childApp =>
                this.state.moduleSearchTerm.some(term => childApp.shortdesc.toLowerCase().includes(term)) &&
                this.state.technicalSearchTerm.some(term => childApp.name.toLowerCase().includes(term))
            );
            if (matchedApps.length > 0 &&
                this.state.categorySearchTerm.some(term => appCategory.name.toLowerCase().includes(term))) {
                matchingCategories.push({
                    ...appCategory,
                    child_apps: matchedApps
                });
            }
        }
    }

    /**
     * Handles the onchange event for the country dropdown.
     * Updates the states dropdown based on the selected country.
     */
    async CountryOnchange(ev) {
        var countryId = ev.target.value;
        if (countryId) {
            var state = await this.orm.searchRead("res.country.state", [
                ['country_id', '=', parseInt(countryId)]
            ]);
            var country = this.state.countries.find(country => country.id === parseInt(countryId));
        }
        this.state.states = state;
        this.state.country = country.id;
    }

    /**
     * Handles the onchange event for the state dropdown.
     * Updates the selected state in the component state.
     */
    async StateOnchange(ev) {
        var stateId = ev.target.value;
        if (stateId) {
            var state = await this.orm.searchRead("res.country.state", [
                ['id', '=', parseInt(stateId)]
            ]);
        }
        this.state.country_state = state[0].id;
    }

    /**
     * Retrieves the available color options for the UI.
     *
     * @returns {Array} - Array of color options.
     */
    get colors() {
        return COLORPICKER
    }

    /**
     * Handles the click event on a color option.
     * Updates the selected color in the component state.
     */
    colorClick(selectedColor, selectedNum) {
        const colorItemEls = this.rootRef.el.querySelectorAll(".cy-app-install-color");
        this.state.color = selectedNum
        const isSelected = Array.from(colorItemEls).some((colorItemEl) =>
            colorItemEl.classList.contains("cy-app-install-color--selected")
        );
        colorItemEls.forEach((colorItemEl) => {
            if (isSelected) {
                colorItemEl.classList.remove("cy-app-install-color--selected", "cy-app-install-color--excluded");
            } else {
                const label = colorItemEl.querySelector(".cy-app-install-color__label");
                if (label.classList.contains(selectedColor)) {
                    colorItemEl.classList.add("cy-app-install-color--selected");
                } else {
                    colorItemEl.classList.remove("cy-app-install-color--selected");
                    colorItemEl.classList.add("cy-app-install-color--excluded");
                }
            }
        });
    }

    /**
     * Redirects the user after updating the company information.
     */
    async redirectUser() {
        await this.orm.call("res.users", "update_company", [], {
            id: this.state.id,
            name: this.state.name,
            street: this.state.street,
            street2: this.state.street2,
            state_id: this.state.country_state,
            city: this.state.city,
            zip: this.state.pin,
            vat: this.state.vat,
            company_registry: this.state.company_registry,
            country_id: this.state.country,
            phone: this.state.phone,
            mobile: this.state.mobile,
            email: this.state.email,
            website: this.state.website,
            color: this.state.color,
            logo: this.state.image
        })
        this.setTemplate("user")
    }

    /**
     * Triggers the file input element to open for image selection.
     */
    triggerImageInput() {
        document.getElementById('imageInput').click();
    }

    /**
     * Handles the image upload event.
     * Updates the preview image and stores the base64 data in the component state.
     */
    async handleImageUpload(event) {
        const fileInput = event.target;
        const previewImage = document.getElementById('previewImage');
        const file = await fileInput.files[0];
        if (file && !['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(file.type)) {
            this.notification.add(_t("Unsupported image format. Please upload a JPEG, PNG, GIF or WEBP image."), {type: "danger"});
            fileInput.value = '';
            return;
        }
        if (file && previewImage) {
            const reader = new FileReader();
            reader.onload = (e) => {
                previewImage.src = e.target.result;
                var base64Data = e.target.result.split(',')[1];
                this.state.image = base64Data;
                this.state.imageMimeType = file.type;
            };
            reader.readAsDataURL(file);
        }
        const profile_card = this.rootRef.el.querySelector('.cy-app-install-demo-card__hero-profile')
        profile_card.style.border = '2px solid transparent';
    }

    clearImage() {
        this.state.image = null;
        this.state.imageMimeType = null;
        const previewImage = document.getElementById('previewImage');
        if (previewImage) {
            previewImage.src = '';
        }

        const profile_card = this.rootRef.el.querySelector('.cy-app-install-demo-card__hero-profile');
        if (profile_card) {
            profile_card.style.border = 'none';  // Optional: reset border if needed
        }
    }

    /**
     * Sets the component template to "user" when the second step is skipped.
     */
    skip_second() {
        this.setTemplate("user");
    }
    /**
     * Retrieves the language name based on the language code.
     *
     * @param {string} languageCode - Language code to find the corresponding language name.
     * @returns {string} - Language name or "Unknown Language" if not found.
     */
    getLanguageName(languageCode) {
        const language = this.state.user_data.res_lang.find(lang => lang.code === languageCode);
        if (language) {
            return language.name;
        } else {
            return 'Unknown Language';
        }
    }

    /**
     * Redirects to the details view of a specific user.
     *
     * @param {number} userId - ID of the user to navigate to.
     */
    async redirectToUserDetails(userId) {
        const views = await this.env.services.orm.searchRead(
            "ir.ui.view",
            [["name", "=", "res.users.form"]],
            ["name", "model", "type"],
        )
        this.action.doAction({
                type: 'ir.actions.act_window',
                name: _t('User'),
                res_model: 'res.users',
                views: [[views[0].id, "form"]],
                view_mode: 'form',
                res_id: userId,
                target: 'new',
            },
            {
                onClose: async () => {
                    this.state.user_data = await this.ormService.call("res.users", "custom_user_data", [this.ormService.user.userId])
                }
            });
    }

    /**
     * Displays a welcome message by making the corresponding HTML element visible.
     */
    async welcomeMessage() {
        this.rootRef.el.querySelector('#welcomeMessage').style.display = 'block';
    }

    /**
     * Initiates the process of getting started.
     * Displays a welcome message, waits for 3 seconds, cleans up menus, and reloads the main components.
     */
    async getStarted() {
        $('li:contains("Action First Time")').hide();
        this.getStartedClicked = true
        await this.Loading();
        await this.ormService.call("ir.module.module", "app_install", [this.state.apps]);
        await this.Loading();
        await this.welcomeMessage();
        await new Promise(resolve => setTimeout(resolve, 3000));
        await this.orm.call('res.users', 'clean_up_menus', [this.ormService.user.userId]);
        document.querySelector(".cy-menu-sidebar")?.style.setProperty("display", "flex");
        document.querySelector(".o_action_manager")?.style.removeProperty("padding-left");
        sessionStorage.removeItem('template');
        sessionStorage.removeItem('apps');
        sessionStorage.removeItem('apps_to_install');
        sessionStorage.removeItem('app_details');
        localStorage.setItem("Reload", true)
        window.location.reload()
    }

    /**
     * Opens a popup for adding a new user.
     */
    async openAddUserPopup() {
        const views = await this.env.services.orm.searchRead(
            "ir.ui.view",
            [["name", "=", "res.users.form"]],
            ["name", "model", "type"],
        )
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('Add a User'),
            res_model: 'res.users',
            views: [[views[0].id, "form"]],
            view_mode: 'form',
            target: 'new',
        }, {
            onClose: async () => {
                this.state.user_data = await this.ormService.call("res.users", "custom_user_data", [this.ormService.user.userId])
            }
        });
    }

    /**
     * Function to handle app selection.
     * Toggles the selected state and updates the list of apps to install.
     *
     * @param {Object} app_data - Data of the selected app.
     */
    select_app(app_data) {
        if (app_data) {
            const app_id = app_data.id;
            const appsToInstall = this.state.apps_to_install.slice();
            const appDetails = this.state.app_details.slice();
            if (!appsToInstall.includes(app_id)) {
                appsToInstall.push(app_id);
                appDetails.push(app_data);
            } else {
                const indexToRemove = appsToInstall.indexOf(app_id);
                appsToInstall.splice(indexToRemove, 1);
                appDetails.splice(indexToRemove, 1);
            }
            sessionStorage.setItem('apps_to_install', JSON.stringify(appsToInstall));
            sessionStorage.setItem('app_details', JSON.stringify(appDetails));
            this.state.apps_to_install = appsToInstall;
            this.state.app_details = appDetails;
        }
    }
}
registry.category("actions").add("massive_app_install", AppDrawer);