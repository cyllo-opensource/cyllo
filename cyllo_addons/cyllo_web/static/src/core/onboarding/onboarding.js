/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import {
    Component,
    useSubEnv,
    onWillStart,
    onWillDestroy,
    useState,
    useRef,
    useEffect
} from "@odoo/owl";
import { Apps } from "./apps";
import { AppSearchBar } from "./app_search_bar";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { ColorList } from "@web/core/colorlist/colorlist";
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";

const storageKey = (key) => `${key}_${session.db}`;

const COLORPICKER = ['cy_onboarding_color_label_transparent', 'cy_onboarding_color_label_red', 'cy_onboarding_color_label_orange', 'cy_onboarding_color_label_yellow', 'cy_onboarding_color_label_blue', 'cy_onboarding_color_label_sakura', 'cy_onboarding_color_label_beige', 'cy_onboarding_color_label_turquoise', 'cy_onboarding_color_label_purple', 'cy_onboarding_color_label_pink', 'cy_onboarding_color_label_green', 'cy_onboarding_color_label_lavender']



/**
 * Onboarding Component for handling the onboarding flow.
 */
export class Onboarding extends Component {
    static template = "cyllo_web.onboarding";
    static components = {
        Apps,
        AppSearchBar,
        SelectMenu,
        ColorList,
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
                    $(this.rootRef.el.querySelector('#cy_onboarding_cyllo_info')).text(erpFacts[factIndex]).fadeIn(500);
                }
                factIndex++;
                return setInterval(() => {
                    if (this.rootRef.el) {
                        $(this.rootRef.el.querySelector('#cy_onboarding_cyllo_info')).fadeOut(500, function () {
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
        document.querySelector(".o_action_manager")?.style.setProperty("padding-left", "0", "important");
        this.rpc = useService("rpc");
        this.rootRef = useRef('root')
        this.radioState = useState({
            selectedColor: false
        })
        const storedAppsToInstall = sessionStorage.getItem(storageKey('apps_to_install'));
        const storedAppDetails = sessionStorage.getItem(storageKey('app_details'));
        const storedIndustryApps = sessionStorage.getItem(storageKey('industry_apps'));
        let parsedAppsToInstall;
        let parsedAppDetails;
        let parsedIndustryApps;
        try {
            parsedAppsToInstall = storedAppsToInstall ? JSON.parse(storedAppsToInstall) : [];
            parsedAppDetails = storedAppDetails ? JSON.parse(storedAppDetails) : [];
            parsedIndustryApps = storedIndustryApps ? JSON.parse(storedIndustryApps) : [];
        } catch (error) {
            parsedAppsToInstall = [];
            parsedAppDetails = [];
            parsedIndustryApps = [];
        }
        this.state = useState({
            apps_to_install: parsedAppsToInstall,
            app_details: parsedAppDetails,
            loading: false,
            skipClicked: false,
            country: 0,
            states: [],
            industries: [],
            industryVerticals: [],
            industry: false,
            selected_industry_vertical: sessionStorage.getItem(storageKey('selected_industry_vertical'))
                ? Number(sessionStorage.getItem(storageKey('selected_industry_vertical')))
                : false,
            industry_apps: parsedIndustryApps,
            user: false,
            selectedPanelOpen: false,
            all_modules: false,
            image: null,
            imageMimeType: null,
            template: sessionStorage.getItem(storageKey('template')) || 'company',
        });
        this.orm = useService("orm");
        this.isHidden = false;
        this.lastSearchDomain = [];
        this.matchingAppIds = null;
        onWillStart(async () => await this.load_data());
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.getStartedClicked = false
        useBus(this.env.bus, "update_selected_apps", (ev) => {
            this.select_app(ev.detail.app_id);
        });
        useSubEnv({
            get_loading: this.Loading.bind(this),
            user_data: this.state.user_data,
        });
        onWillDestroy(() => setTimeout(() => {
            if (this.getStartedClicked) {
                window.location.reload()
            }
        }, 1000)
        )
        if (localStorage.getItem(storageKey("Reload")) === "true") {
            localStorage.setItem(storageKey("Reload"), false)
            sessionStorage.removeItem(storageKey('template'));
            sessionStorage.removeItem(storageKey('apps'));
            sessionStorage.removeItem(storageKey('apps_to_install'));
            sessionStorage.removeItem(storageKey('app_details'));
            sessionStorage.removeItem(storageKey('industry_apps'));
            sessionStorage.removeItem(storageKey('selected_industry_vertical'));
            document.querySelector(".o_main_navbar")?.style.setProperty("display", "flex");
            document.querySelector(".cy-menu-sidebar")?.style.setProperty("display", "flex");
            document.querySelector(".o_action_manager")?.style.removeProperty("padding-left");
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
     * Sets the template in the component state and stores it in the session storage.
     *
     * @param {string} newTemplate - The new template to be set.
     */
    setTemplate(newTemplate) {
        this.state.template = newTemplate;
        sessionStorage.setItem(storageKey('template'), newTemplate);
    }

    /**
     * Back/Continue button setup for the shared footer bar, keyed off
     * the step currently displayed.
     */
    get footerConfig() {
        if (this.state.template === 'user') {
            return { showBack: true, showReadyHeader: false, continueLabel: 'Continue' };
        }
        if (this.state.template === 'industry') {
            return { showBack: true, showReadyHeader: false, continueLabel: 'Continue' };
        }
        if (this.state.template === 'main_content') {
            return {
                showBack: true,
                showReadyHeader: true,
                continueLabel: this.state.apps_to_install.length > 0 ? 'Continue' : 'Skip',
            };
        }
        return { showBack: false, showReadyHeader: false, continueLabel: 'Continue' };
    }

    /**
     * Handles the shared footer bar's Back button for whichever step
     * is currently displayed.
     */
    onFooterBack() {
        if (this.state.template === 'user') {
            this.back_second();
        } else if (this.state.template === 'industry') {
            this.setTemplate('user');
        } else if (this.state.template === 'main_content') {
            this.back_first();
        }
    }

    /**
     * Handles the shared footer bar's Continue/Skip button for
     * whichever step is currently displayed.
     */
    onFooterContinue() {
        if (this.state.template === 'company') {
            this.redirectUser();
        } else if (this.state.template === 'user') {
            this.setTemplate('industry');
        } else if (this.state.template === 'industry') {
            this.saveIndustryAndContinue();
        } else if (this.state.template === 'main_content') {
            this.getStarted();
        }
    }

    async saveIndustryAndContinue() {
        try {
            if (this.state.id) {
                await this.orm.call("res.users", "update_company", [], {
                    id: this.state.id,
                    industry_id: this.state.industry || false,
                });
            }
        } catch (error) {
            console.error("Onboarding saveIndustryAndContinue failed:", error);
        }
        this.setTemplate("main_content");
    }

    /**
     * Navigates back to the "industry" template.
     */
    back_first() {
        this.setTemplate("industry");
    }

    /**
     * Signals that loading is in progress by updating the `loading` state.
     */
    Loading() {
        this.state.loading = !this.state.loading;
    }

    /**
     * Expands/collapses the floating selected-apps list.
     */
    toggleSelectedPanel() {
        if (this.state.apps_to_install.length === 0) {
            return;
        }
        this.state.selectedPanelOpen = !this.state.selectedPanelOpen;
    }

    /**
     * Removes an app from the selected-apps summary and the install list.
     */
    delete_apps_from_list(app) {
        this.state.app_details = this.state.app_details.filter((detail) => detail.id !== app.id);
        this.state.apps_to_install = this.state.apps_to_install.filter((value) => value !== app.id);
        this.state.industry_apps = (this.state.industry_apps || []).filter((item) => item.id !== app.id);
        sessionStorage.setItem(storageKey('apps_to_install'), JSON.stringify(this.state.apps_to_install));
        sessionStorage.setItem(storageKey('app_details'), JSON.stringify(this.state.app_details));
        sessionStorage.setItem(storageKey('industry_apps'), JSON.stringify(this.state.industry_apps));
    }

    /**
     * Clears every selected app (triggered by the sidebar "Clear All" button).
     * Keeps the industry_apps panel intact.
     */
    clearSelectedApps() {
        this.state.app_details = [];
        this.state.apps_to_install = [];
        sessionStorage.setItem(storageKey('apps_to_install'), JSON.stringify(this.state.apps_to_install));
        sessionStorage.setItem(storageKey('app_details'), JSON.stringify(this.state.app_details));
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
            this.category_all_apps_pool = category[2]
            this.state.category = this.category
            var user_data = await this.ormService.call("res.users", "custom_user_data", [this.ormService.user.userId])
            this.state.name = user_data.company_data[0].name
            this.state.id = user_data.company_data[0].id
            this.state.street = user_data.company_data[0].street
            this.state.street2 = user_data.company_data[0].street2
            this.state.country_state = user_data.company_data[0].state_id ? user_data.company_data[0].state_id[0] : false
            this.state.city = user_data.company_data[0].city
            this.state.pin = user_data.company_data[0].zip
            this.state.vat = user_data.company_data[0].vat
            this.state.company_registry = user_data.company_data[0].company_registry
            this.state.countries = user_data.countries
            this.state.country = user_data.company_data[0].country_id ? user_data.company_data[0].country_id[0] : false
            this.state.industries = user_data.industries
            this.state.industryVerticals = user_data.industry_verticals || []
            this.state.industry = user_data.company_data[0].industry_id ? user_data.company_data[0].industry_id[0] : false
            if (this.state.selected_industry_vertical) {
                const vert = (this.state.industryVerticals).find(v => v.id === Number(this.state.selected_industry_vertical));
                if (vert) {
                    // Only re-apply vertical apps if industry_apps is empty
                    // (i.e. no saved session). If industry_apps is already
                    // populated from sessionStorage the user's manual
                    // deselections are already correct — don't overwrite them.
                    if (!this.state.industry_apps || this.state.industry_apps.length === 0) {
                        this.autoSelectVerticalApps(vert);
                    }
                }
            } else if (this.state.industry) {
                const ind = (this.state.industries || []).find(i => i.id === this.state.industry);
                const vert = ind && (this.state.industryVerticals).find(v => v.base_industry === ind.name);
                if (vert) {
                    this.state.selected_industry_vertical = vert.id;
                    if (!this.state.industry_apps || this.state.industry_apps.length === 0) {
                        this.autoSelectVerticalApps(vert);
                    }
                }
            } else if (this.state.industry_apps && this.state.industry_apps.length > 0) {
                this.clearIndustryApps();
            }
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
            console.error("Onboarding load_data failed:", error);
        }
    }

    async applyCategoryFilter(domain) {
        const baseCategories = this.state.all_modules ? this.category_with_all_apps : this.category;
        if (!domain || domain.length === 0) {
            this.matchingAppIds = null;
            this.state.category = baseCategories;
            return;
        }
        const matchingRecords = await this.orm.searchRead("ir.module.module", domain, ["id"]);
        this.matchingAppIds = new Set(matchingRecords.map((record) => record.id));
        this.state.category = baseCategories
            .map((categ) => ({
                ...categ,
                child_apps: categ.child_apps.filter((app) => this.matchingAppIds.has(app.id)),
            }))
            .filter((categ) => categ.child_apps.length > 0);
    }

    onAppSearchDomainChange(domain) {
        this.lastSearchDomain = domain;
        this.applyCategoryFilter(domain);
    }

    /**
     * Switches the app grid between the curated "Apps" set and every
     * installable module ("All"), keeping the active search applied.
     */
    setAppsFilter(showAll) {
        this.state.all_modules = showAll;
        this.applyCategoryFilter(this.lastSearchDomain);
    }

    /**
     * Choice list for the country SelectMenu.
     */
    get countryChoices() {
        return (this.state.countries || []).map((country) => ({
            value: country.id,
            label: country.name,
        }));
    }

    /**
     * Choice list for the state SelectMenu.
     */
    get stateChoices() {
        return (this.state.states || []).map((countryState) => ({
            value: countryState.id,
            label: countryState.display_name,
        }));
    }

    /**
     * Name of the currently selected industry, if any.
     */
    get selectedIndustryName() {
        if (this.state.selected_industry_vertical) {
            const vertical = (this.state.industryVerticals || []).find((v) => v.id === Number(this.state.selected_industry_vertical));
            if (vertical) {
                return vertical.name;
            }
        }
        const industry = (this.state.industries || []).find((i) => i.id === this.state.industry);
        return industry ? industry.name : '';
    }

    /**
     * Category list with a dynamic category prepended for the current
     * industry's suggested apps.
     */
    get displayCategories() {
        const categories = this.state.category || [];
        if ((!this.state.industry && !this.state.selected_industry_vertical) || this.state.industry_apps.length === 0) {
            return categories;
        }
        const industryIds = new Set(this.state.industry_apps.map((app) => app.id));
        const filteredIndustryApps = this.matchingAppIds
            ? this.state.industry_apps.filter((app) => this.matchingAppIds.has(app.id))
            : this.state.industry_apps;

        const rest = categories
            .map((categ) => ({
                ...categ,
                child_apps: categ.child_apps.filter((app) => !industryIds.has(app.id)),
            }))
            .filter((categ) => categ.child_apps.length > 0);

        if (filteredIndustryApps.length > 0) {
            const industryCategory = {
                id: `industry-${this.state.selected_industry_vertical || this.state.industry}`,
                name: this.selectedIndustryName,
                child_apps: filteredIndustryApps,
            };
            return [industryCategory, ...rest];
        }
        return rest;
    }

    /**
     * Industry vertical packages loaded from the onboarding.industry model.
     */
    get industryVerticals() {
        return this.state.industryVerticals || [];
    }

    /**
     * Choice list for the industry SelectMenu.
     */
    get industryChoices() {
        return (this.state.industries || []).map((industry) => ({
            value: industry.id,
            label: industry.name,
        }));
    }

    /**
     * Fully resets all app selections (apps_to_install, app_details, industry_apps).
     * Called whenever the user switches or deselects an industry so the new
     * vertical always starts from a clean slate with no previously chosen apps.
     */
    clearAllApps() {
        this.state.apps_to_install = [];
        this.state.app_details = [];
        this.state.industry_apps = [];
        sessionStorage.removeItem(storageKey('apps_to_install'));
        sessionStorage.removeItem(storageKey('app_details'));
        sessionStorage.removeItem(storageKey('industry_apps'));
    }

    /**
     * Legacy alias kept for any other call sites — delegates to clearAllApps.
     */
    clearIndustryApps() {
        this.clearAllApps();
    }

    /**
     * Handles selection on the industry grid.
     * Always does a full reset before applying the new vertical's apps so that
     * switching industries never accumulates stale selections.
     */
    onIndustrySelect(verticalId) {
        verticalId = Number(verticalId);
        this.clearAllApps();
        if (this.state.selected_industry_vertical === verticalId) {
            this.state.selected_industry_vertical = false;
            this.state.industry = false;
            sessionStorage.removeItem(storageKey('selected_industry_vertical'));
        } else {
            this.state.selected_industry_vertical = verticalId;
            sessionStorage.setItem(storageKey('selected_industry_vertical'), verticalId);
            const vertical = (this.state.industryVerticals || []).find((v) => v.id === verticalId);
            if (vertical) {
                const dbInd = (this.state.industries || []).find((i) => i.name === vertical.base_industry);
                this.state.industry = dbInd ? dbInd.id : false;
                this.autoSelectVerticalApps(vertical);
            }
        }
    }

    /**
     * Adds the apps suggested for the given vertical to the
     * install list, and sets state.industry_apps to match this vertical.
     */
    autoSelectVerticalApps(vertical) {
        if (!vertical || !vertical.apps) {
            return;
        }
        const allApps = (this.category_all_apps_pool || this.category_with_all_apps || []).flatMap((categ) => categ.child_apps);
        const appsToInstall = this.state.apps_to_install.slice();
        const appDetails = this.state.app_details.slice();
        const industryApps = [];
        const industryIds = new Set();

        for (const name of vertical.apps) {
            const app = allApps.find((a) => a.name === name);
            if (!app) {
                continue;
            }
            if (!appsToInstall.includes(app.id)) {
                appsToInstall.push(app.id);
                appDetails.push(app);
            }
            if (!industryIds.has(app.id)) {
                industryApps.push(app);
                industryIds.add(app.id);
            }
        }
        this.state.apps_to_install = appsToInstall;
        this.state.app_details = appDetails;
        this.state.industry_apps = industryApps;
        sessionStorage.setItem(storageKey('apps_to_install'), JSON.stringify(appsToInstall));
        sessionStorage.setItem(storageKey('app_details'), JSON.stringify(appDetails));
        sessionStorage.setItem(storageKey('industry_apps'), JSON.stringify(industryApps));
    }

    /**
     * Adds the apps suggested for the given industry to the
     * install list using the matching onboarding.industry DB config.
     * Fully resets prior selections before applying the new vertical.
     */
    autoSelectIndustryApps(industryId) {
        const industry = (this.state.industries || []).find((i) => i.id === industryId);
        const vertical = industry && (this.state.industryVerticals || []).find((v) => v.base_industry === industry.name);
        this.clearAllApps();
        if (vertical) {
            this.autoSelectVerticalApps(vertical);
        }
    }

    /**
     * Handles selection on the country dropdown.
     * Updates the states dropdown based on the selected country.
     */
    async onCountrySelect(countryId) {
        if (!countryId) {
            this.state.states = [];
            this.state.country = false;
            this.state.country_state = false;
            return;
        }
        this.state.states = await this.orm.searchRead("res.country.state", [
            ['country_id', '=', countryId]
        ]);
        this.state.country = countryId;
    }

    /**
     * Handles selection on the state dropdown.
     * Updates the selected state in the component state.
     */
    async onStateSelect(stateId) {
        this.state.country_state = stateId || false;
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
     * Color indices for Odoo's default ColorList widget (0 to 11).
     */
    get colorListColors() {
        return [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
    }

    /**
     * Handles color selection from Odoo's standard ColorList widget.
     * Updates the color field in state so it writes directly to res.company.color.
     *
     * @param {number} colorId - The selected color index (0-11).
     */
    onColorSelected(colorId) {
        this.state.color = colorId;
    }

    /**
     * Handles the click event on a color option.
     * Updates the selected color in the component state.
     */
    colorClick(selectedColor, selectedNum) {
        const colorItemEls = this.rootRef.el.querySelectorAll(".cy_onboarding_color");
        this.state.color = selectedNum
        const isSelected = Array.from(colorItemEls).some((colorItemEl) =>
            colorItemEl.classList.contains("cy_onboarding_color_selected")
        );
        colorItemEls.forEach((colorItemEl) => {
            if (isSelected) {
                colorItemEl.classList.remove("cy_onboarding_color_selected", "cy_onboarding_color_excluded");
            } else {
                const label = colorItemEl.querySelector(".cy_onboarding_color_label");
                if (label.classList.contains(selectedColor)) {
                    colorItemEl.classList.add("cy_onboarding_color_selected");
                } else {
                    colorItemEl.classList.remove("cy_onboarding_color_selected");
                    colorItemEl.classList.add("cy_onboarding_color_excluded");
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
            industry_id: this.state.industry,
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

    async handleImageUpload(event) {
        const fileInput = event.target;
        const file = await fileInput.files[0];
        
        if (file && !['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(file.type)) {
            this.notification.add(_t("Unsupported image format. Please upload a JPEG, PNG, GIF or WEBP image."), { type: "danger" });
            fileInput.value = '';
            return;
        }
        
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                var base64Data = e.target.result.split(',')[1];
                this.state.image = base64Data;
                this.state.imageMimeType = file.type;
            };
            reader.readAsDataURL(file);
        }
        
        const profile_card = this.rootRef.el.querySelector('.cy_onboarding_demo_card_hero_profile');
        if (profile_card) {
            profile_card.style.border = '2px solid transparent';
        }
    }

    clearImage() {
        this.state.image = null;
        this.state.imageMimeType = null;
        const previewImage = document.getElementById('previewImage');
        if (previewImage) {
            previewImage.src = '';
        }

        const profile_card = this.rootRef.el.querySelector('.cy_onboarding_demo_card_hero_profile');
        if (profile_card) {
            profile_card.style.border = 'none';
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
        await this.ormService.call("ir.module.module", "app_install", [this.state.apps_to_install]);
        await this.Loading();
        await this.welcomeMessage();
        await new Promise(resolve => setTimeout(resolve, 3000));
        await this.orm.call('res.users', 'clean_up_menus', [this.ormService.user.userId]);
        document.querySelector(".cy-menu-sidebar")?.style.setProperty("display", "flex");
        document.querySelector(".o_action_manager")?.style.removeProperty("padding-left");
        sessionStorage.removeItem(storageKey('template'));
        sessionStorage.removeItem(storageKey('apps'));
        sessionStorage.removeItem(storageKey('apps_to_install'));
        sessionStorage.removeItem(storageKey('app_details'));
        sessionStorage.removeItem(storageKey('industry_apps'));
        sessionStorage.removeItem(storageKey('selected_industry_vertical'));
        localStorage.setItem(storageKey("Reload"), true)
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
            sessionStorage.setItem(storageKey('apps_to_install'), JSON.stringify(appsToInstall));
            sessionStorage.setItem(storageKey('app_details'), JSON.stringify(appDetails));
            this.state.apps_to_install = appsToInstall;
            this.state.app_details = appDetails;
        }
    }
}
registry.category("actions").add("onboarding", Onboarding);