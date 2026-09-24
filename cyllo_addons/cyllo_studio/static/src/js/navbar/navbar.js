/** @odoo-module **/
import {
    NavBar
} from "@web/webclient/navbar/navbar";
import {
    useService,
    useBus
} from "@web/core/utils/hooks";
import {
    ViewSelectionDropDown
} from "@cyllo_studio/js/navbar/view_selection_dropdown/view_selection_dropdown";
import {
    useEffect,
    useState,
    useRef,
    onMounted, onPatched, onWillUnmount
} from "@odoo/owl";
import {
    FirstPage
} from '@cyllo_studio/js/new_app/new_app_templates';
import { RemoveSessions } from '@cyllo_studio/js/root/studio_utils';

// Reports that are technical building blocks (label/barcode sheets) rather
// than user-editable documents. They stay fully functional (Print menu,
// rendering) but are hidden from the Studio Reports kanban so the list stays
// focused on real, customizable reports. Matched by report_name (stable
// across databases). Mirrors the blacklist Odoo's own web_studio applies.
const STUDIO_REPORT_BLACKLIST = [
    "product.report_producttemplatelabel_dymo",       // Product Label (PDF)
    "product.report_producttemplatelabel2x7",          // Product Label 2x7 (PDF)
    "product.report_producttemplatelabel4x7",          // Product Label 4x7 (PDF)
    "product.report_producttemplatelabel4x12",         // Product Label 4x12 (PDF)
    "product.report_producttemplatelabel4x12noprice",  // Product Label 4x12 No Price (PDF)
];

/**
 * CylloNavBar extends the standard Odoo NavBar to integrate
 * Cyllo Studio functionality, including undo/redo support,
 * view switching, and studio-specific UI controls.
 */

export class CylloNavBar extends NavBar {
    static template = "cyllo_studio.CylloNavBar";
    setup() {
        this.orm = useService("orm");
        this.root = useRef("cy_nav_bar");
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.dialogService = useService("dialog");
        this.menuService = useService("menu")
        this.notification = useService("notification")
        const prevForm = this._readPrevForm();
        const configBc = this._readConfigBreadcrumb();
        this.state = useState({
            isSystemAdmin: this.env.services.user.hasGroup("base.group_system"),
            studioEditableList: false,
            lightMode: false,
            isStudioEdit: false,
            canUndo: JSON.parse(sessionStorage.getItem('UndoRedo') || '[]').length > 0, //starlin
            canRedo: JSON.parse(sessionStorage.getItem('ReDO') || '[]').length > 0, //starlin
            configOpen: false,
            bcActive: sessionStorage.getItem('CyX2ManyTriggered') === 'true',
            bcPrev: prevForm?.ModelName || "",
            bcField: prevForm?.FieldName || "",
            isSearchView: false,
            configBcActive: !!configBc,
            configBcPrev: configBc?.prev || "",
            configBcField: configBc?.field || "",
        });
        useBus(this.env.bus, 'SEARCH_VIEW_OPENED', () => {
            this.state.isSearchView = true;
        });
        useBus(this.env.bus, 'studio_editable_list', (res) => {
            this.state.studioEditableList = res.detail;
            this.props.updateState("edit", false);
        });
        useBus(this.env.bus, 'X2Many-Breadcrumbs', ({ detail }) => {
            // A drill supersedes any Configuration sub-view trail on screen.
            this._clearConfigBreadcrumb();
            this.state.bcPrev = detail.ModelName || "";
            this.state.bcField = detail.FieldName || "";
            this.state.bcActive = true;
        });
        useBus(this.env.bus, 'ACTION_MANAGER:UI-UPDATED', () => {
            const actionId = this.action.currentController?.action?.jsId;
            const currentResModel = this.action.currentController?.action?.res_model;
            const isFirstEvent = this._lastActionId === null;
            const actionChanged = actionId && this._lastActionId !== actionId;

            if (actionChanged) {
                const configFieldName = this._metaModelToFieldName[currentResModel];
                if (configFieldName) {
                    // _getBusinessContext() tracks the last non-meta view as
                    // the parent regardless of whether it had a res_model, so
                    // this is always fresh — Home/Discuss show up by name,
                    // not a stale unrelated one from an older session.
                    const { name: businessName } = this._getBusinessContext();
                    this._clearX2manyBreadcrumb();
                    this._setConfigBreadcrumb(businessName, configFieldName);
                    // Reports/Access Rights/Record Rules have no field editor
                    // of their own — a Field Customizer left open from the
                    // business view underneath would otherwise linger stale.
                    this.env.bus.trigger('CY_META_VIEW_OPENED');
                } else {
                    // Landed on a real business view. The config breadcrumb
                    // is only ever valid while viewing a meta-view, so any
                    // persisted one here (e.g. re-entering Studio fresh after
                    // Exit, restored from sessionStorage on mount) is stale —
                    // clear it unconditionally, first event or not.
                    this._clearConfigBreadcrumb();
                    // The x2many trail is different: it has no action/history
                    // entry of its own, so a legitimately-restored one (from a
                    // refresh mid-drill) IS expected on the first event and
                    // must survive it — only clear it on later, genuine nav.
                    if (!isFirstEvent) {
                        this._clearX2manyBreadcrumb();
                    }
                    this._getBusinessContext();
                }
                // Stale from the previous action's studio-editable list (if
                // any) — the new action's own renderer re-announces this via
                // 'studio_editable_list' on mount if it's ALSO editable, but
                // meanwhile this must not keep hiding the title/view-switcher.
                this.state.studioEditableList = false;
            }
            if (actionId) {
                this._lastActionId = actionId;
            }
            this.state.isSearchView = false;
            this.render();
        });
        useBus(this.env.bus, 'PREVIEW_MODE_CHANGED', ({ detail }) => {
            this.state.isPreviewMode = detail.isPreviewMode;
        });
        useBus(this.env.bus, "STUDIO_EDIT_BUTTON_HIDE", () => {
            this.props.updateState("editButton", false);
        });

        this.viewChange = this.viewChange.bind(this);
        this._metaModelToFieldName = {
            'ir.model.access': 'Access Rights',
            'ir.rule': 'Record Rules',
            'ir.actions.report': 'Reports',
        };
        this._lastActionId = null;
        this._onPopState = () => this._clearX2manyBreadcrumb();
        // Close the (click-opened) Configuration dropdown on any outside click.
        this._onDocClick = (ev) => {
            if (!this.state.configOpen) {
                return;
            }
            const btn = this.root.el?.querySelector('.cy-nav-Menu-button');
            if (btn && !btn.contains(ev.target)) {
                this.state.configOpen = false;
            }
        };
        onMounted(async () => {
            const count = await this.orm.searchCount("ir.module.module", [
                ["name", "=", "cyllo_studio_ai"],
                ["state", "=", "installed"],
            ]);
            this.state.studioAIInstalled = count > 0;
            this.updateUndoRedoState();
            setInterval(() => this.updateUndoRedoState(), 500);
            window.addEventListener('popstate', this._onPopState);
            document.addEventListener('click', this._onDocClick);
        });
        onWillUnmount(() => {
            window.removeEventListener('popstate', this._onPopState);
            document.removeEventListener('click', this._onDocClick);
        });
        onPatched(() => {
            let studioViews = this.root?.el.querySelector('.cy-studio-views');
            if (studioViews) {
                // Configuration sub-views (Access Rights, Record Rules, Reports)
                // only ever have one view (list) — no view type to switch between.
                studioViews.style.display = (this.state.studioEditableList || this.state.configBcActive) ? 'none' : 'block';
            }
            if (this.state.configOpen) {
                this.ShowMiscellaneousDrop();
            }
        });
    }

    /**
     * Update undo/redo button states based on sessionStorage.
     * Automatically triggers edit mode if 'cyllo_auto_edit' is set.
     */
    updateUndoRedoState() {
        this.state.canUndo = JSON.parse(sessionStorage.getItem('UndoRedo') || '[]').length > 0;
        this.state.canRedo = JSON.parse(sessionStorage.getItem('ReDO') || '[]').length > 0;
        if (sessionStorage.getItem("cyllo_auto_edit") === "1") {
            this.handleEdit();
            sessionStorage.removeItem("cyllo_auto_edit");
        }
    }

    /**
     * Open the Cyllo Studio app creation dialog.
     */
    createApp() {
        this.dialogService.add(FirstPage, {
            title: 'Cyllo Studio',
        })
    }

    /**
     * Resolve the actual business model + display name (e.g. "sale.order" /
     * "Quotations") the Configuration menu actions (Access Rights/Record
     * Rules/Reports) should act on and show as the breadcrumb root.
     *
     * currentController's model/name are wrong once one of those sub-views is
     * already open — chaining Report → Access Rights would otherwise resolve
     * to 'ir.actions.report' / "Reports" instead of the original business
     * view. Whenever we ARE on a real business view, remember it; whenever
     * we're on one of these meta views, fall back to the last remembered one
     * instead — so the breadcrumb always roots at the true starting view,
     * however many Configuration sub-views deep we are.
     */
    _getBusinessContext() {
        const currentAction = this.action.currentController?.action;
        const currentResModel = currentAction?.res_model;
        // The report designer (client action "edit_report") is a sub-tool
        // WITHIN the Reports workflow, not a real navigation away from it —
        // it exposes its own res_model (the report's data source, e.g.
        // account.move.line for "Aged Payable"), which must not overwrite
        // the actual remembered parent when the user later backs out of it.
        const isReportDesigner = currentAction?.tag === 'edit_report';
        const isMetaView = isReportDesigner || (currentResModel && this._metaModelToFieldName[currentResModel]);
        if (!isMetaView) {
            // Any non-meta view is a valid breadcrumb parent, whether it has
            // a real res_model (Quotations) or not (Home, Discuss...). Model
            // presence only matters for RPC scoping below, not for "is this
            // a legitimate parent to show in the trail".
            const viewType = this.action.currentController?.env?.config?.viewType || 'list';
            sessionStorage.setItem('CyConfigBusinessModel', currentResModel || '');
            sessionStorage.setItem('CyConfigBusinessName', this.currentModelName);
            sessionStorage.setItem('CyConfigBusinessViewType', viewType);
            // The action's own id (menu-driven actions, including client
            // actions like Discuss, have one) — lets the breadcrumb "back"
            // link re-dispatch the exact same action directly instead of
            // relying on browser history, which drifts after any detour
            // (e.g. opening/closing the report designer) and can replay the
            // wrong entry.
            if (currentAction?.id) {
                sessionStorage.setItem('CyConfigBusinessActionId', currentAction.id);
            } else {
                sessionStorage.removeItem('CyConfigBusinessActionId');
            }
            return { resModel: currentResModel || null, name: this.currentModelName, viewType };
        }
        // Chaining from one Configuration sub-view to another — reuse the
        // last remembered parent. Its name is always shown in the trail;
        // resModel may be empty (falls back to null) if that parent itself
        // had no model, e.g. Home/Discuss — RPC calls below then correctly
        // scope to "all records" instead of a stale unrelated model.
        return {
            resModel: sessionStorage.getItem('CyConfigBusinessModel') || null,
            name: sessionStorage.getItem('CyConfigBusinessName') || this.currentModelName,
            viewType: sessionStorage.getItem('CyConfigBusinessViewType') || 'list',
        };
    }

    /** Open the Access Rights view for the current model. */
    async AccessRightsClick() {
        if (!this.state.isSystemAdmin) {
            this.notification.add("Contact your System Administrator.", {
                title: "Access Denied",
                type: "danger",
            });
            return;
        }
        this.state.configOpen = false;
        this.env.bus.trigger('CLEAR-MENU', { fromClose: true });
        const { resModel } = this._getBusinessContext();
        const [modelId, viewId] = await this.orm.call("ir.model", "cyllo_get_studio_action_acl", [resModel, 'ir.model.access']);
        await this.action.doAction({
            name: 'Access Rights',
            type: 'ir.actions.act_window',
            res_model: 'ir.model.access',
            views: [[viewId, 'list']],
            target: 'current',
            // No business model to scope to (e.g. opened from the Home
            // dashboard) — omit the default filter entirely rather than
            // passing a falsy model_id, which search_default_* would apply
            // literally and show zero records instead of all of them.
            context: resModel ? {
                default_model_id: modelId,
                search_default_model_id: modelId,
            } : {},
        });
        // The breadcrumb itself is (re)derived centrally by the
        // ACTION_MANAGER:UI-UPDATED handler once this doAction resolves.
    }
    async EmailTemplateClick() { }

    /** Open Record Rules view for the current model. */
    async RecordRuleClick() {
        if (!this.state.isSystemAdmin) {
            this.notification.add("Contact your System Administrator.", {
                title: "Access Denied",
                type: "danger",
            });
            return;
        }
        this.state.configOpen = false;
        this.env.bus.trigger('CLEAR-MENU', { fromClose: true });
        const { resModel } = this._getBusinessContext();
        const model_id = await this.orm.call("ir.model", "cyllo_get_studio_action_acl", [resModel, 'ir.rule']);
        await this.action.doAction({
            name: 'Record Rules',
            type: 'ir.actions.act_window',
            res_model: 'ir.rule',
            views: [[model_id[1], 'list']],
            context: resModel ? {
                default_model_id: model_id[0],
                search_default_model_id: model_id[0],
            } : {},
        });
    }
    /** Show the "Parent > SubView" trail in the navbar for a Configuration sub-view. */
    _setConfigBreadcrumb(parentName, fieldName) {
        this.state.configBcPrev = parentName || "";
        this.state.configBcField = fieldName;
        this.state.configBcActive = true;
        // Persisted so the trail survives a page refresh (in-memory state
        // doesn't) — cleared on any genuine navigation via _clearBreadcrumb.
        sessionStorage.setItem('CyConfigBreadcrumb', JSON.stringify({
            prev: this.state.configBcPrev,
            field: fieldName,
        }));
    }

    /** Toggle the Configuration dropdown (click-driven, not hover). */
    toggleConfig(ev) {
        ev.stopPropagation();
        this.state.configOpen = !this.state.configOpen;
    }
    /** Close the Configuration dropdown. */
    closeConfig() {
        this.state.configOpen = false;
    }
    /** Show the miscellaneous menu dropdown aligned properly. */
    ShowMiscellaneousDrop() {
        const menuContainer = this.root.el?.querySelector('.cy-nav-Menu-button');
        const menuCard = this.root.el?.querySelector('.cy-miscellaneous_card');
        if (!menuContainer || !menuCard) return;
        const containerRect = menuContainer.getBoundingClientRect();
        const cardRect = menuCard.getBoundingClientRect();
        const spaceToRight = window.innerWidth - containerRect.right;
        const spaceToLeft = containerRect.left;
        menuCard.classList.remove('menu-right');
        menuCard.style.left = '0';
        menuCard.style.right = 'auto';
        menuCard.style.zIndex = 999;
        if (spaceToRight < cardRect.width) {
            menuCard.style.left = 'auto';
            menuCard.style.right = '0';
            menuCard.classList.add('menu-right');
        }
    }
    /** Open report view for the current model. */
    async ReportClick() {
        this.state.configOpen = false;
        this.env.bus.trigger('CLEAR-MENU', { fromClose: true });
        // _getBusinessContext() persists {model, name, viewType} for
        // handleClose() to restore on Exit — no need for a separate
        // report-specific origin record here.
        const { resModel } = this._getBusinessContext();
        const [modelId, viewId] = await this.orm.call("ir.model", "cyllo_get_studio_action_acl", [resModel, 'ir.actions.report']);

        const action = {
            name: 'Reports',
            type: 'ir.actions.act_window',
            res_model: 'ir.actions.report',
            target: 'current',
            // Hard filter (not a removable facet): technical label/barcode
            // reports never belong in the Studio Reports list, regardless of
            // the model facet. They remain available in the Print menu.
            domain: [["report_name", "not in", STUDIO_REPORT_BLACKLIST]],
            // A form view is required for the kanban's "+ New"/record-open
            // actions to have somewhere to navigate to — without one they
            // silently do nothing. `false` uses the model's default form view.
            views: [[viewId, 'kanban'], [false, 'form']],
            // No business model to scope to (e.g. opened from the Home
            // dashboard) — omit the default filter so every report shows.
            context: resModel ? {
                default_model: resModel,
                // Removable default filter (shown as a facet pill) — unlike
                // a hard action.domain, clearing it lets the user see every
                // report, not just this model's.
                search_default_model: resModel,
            } : {}
        };

        await this.action.doAction(action);
        // The breadcrumb itself is (re)derived centrally by the
        // ACTION_MANAGER:UI-UPDATED handler once this doAction resolves.
    }

    /** Toggle light/dark mode for studio UI. */
    handleDarkMode() {
        this.state.lightMode = !this.state.lightMode;
        if (this.state.lightMode) {
            document.body.classList.add("light-studio-mode");
            localStorage.setItem("lightModeStudio", this.state.lightMode);
        } else {
            document.body.classList.remove("light-studio-mode");
            localStorage.removeItem("lightModeStudio");
        }
        this.render();
    }

    /** Activate studio edit mode. */
    async handleEdit() {
        this.state.isStudioEdit = true;
        this.env.bus.trigger('STUDIO_EDIT_STARTED', {
            isStudioEdit: this.state.isStudioEdit
        });
        this.props.updateState("edit", true);
        this.props.updateState("editButton", false);
    }

    /** Open the Studio AI (PromptDialog) from the navbar. */
    async openStudioAI() {
        this.env.bus.trigger('TOGGLE_MENU_SIDEBAR', { hideMenu: true });
        const currentUrl = window.location.href;
        const fragment = currentUrl.split('#')[1];
        const params = new URLSearchParams(fragment);
        localStorage.setItem('ExistingStudioPage', [currentUrl, params.get('menu_id')]);
        await this.env.bus.trigger("IS_AI", { isAI: true });
        this.action.doAction({
            type: "ir.actions.client",
            tag: "PromptDialog",
        });
    }

    get viewSelectionProps() {
        return {
            view: this.props.view,
            viewChange: this.viewChange,
        };
    }
    /** Human-readable name of the model/action currently being edited. */
    get currentModelName() {
        const ctrl = this.action.currentController;
        return ctrl?.action?.name || this.props.viewDetails?.model || "";
    }
    /** Safely parse the persisted x2many parent-form descriptor. */
    _readPrevForm() {
        try {
            return JSON.parse(sessionStorage.getItem('PrevForm') || 'null');
        } catch (_) {
            return null;
        }
    }
    /** Safely parse the persisted Configuration sub-view breadcrumb. */
    _readConfigBreadcrumb() {
        try {
            return JSON.parse(sessionStorage.getItem('CyConfigBreadcrumb') || 'null');
        } catch (_) {
            return null;
        }
    }
    /** Reset the x2many drill-down breadcrumb state only. */
    _clearX2manyBreadcrumb() {
        this.state.bcActive = false;
        this.state.bcPrev = "";
        this.state.bcField = "";
    }
    /** Reset the Configuration sub-view breadcrumb state only. */
    _clearConfigBreadcrumb() {
        this.state.configBcActive = false;
        this.state.configBcPrev = "";
        this.state.configBcField = "";
        sessionStorage.removeItem('CyConfigBreadcrumb');
    }
    /** Reset both breadcrumb trails. */
    _clearBreadcrumb() {
        this._clearX2manyBreadcrumb();
        this._clearConfigBreadcrumb();
    }
    /**
     * Navigate back from the Configuration sub-view breadcrumb to the
     * remembered parent action. Re-dispatches it directly by id rather than
     * window.history.back() — browser history drifts after any detour (e.g.
     * opening/closing the report designer) and can replay the wrong entry
     * instead of the parent the breadcrumb link actually names.
     */
    configBreadcrumbBack(e) {
        e.preventDefault();
        const actionId = sessionStorage.getItem('CyConfigBusinessActionId');
        if (actionId) {
            this.action.doAction(parseInt(actionId, 10));
        } else {
            window.history.back();
        }
    }
    /** Navigate back from the x2many breadcrumb (handled by the wrapper). */
    breadcrumbBack(e) {
        e.preventDefault();
        this._clearX2manyBreadcrumb();
        this.env.bus.trigger("STUDIO_BREADCRUMB_BACK");
    }
    viewChange(attr, value) {
        // Switching the top-level view (via the view icons) leaves any x2many
        // drill, so the "Parent > Field" breadcrumb must reset.
        this._clearBreadcrumb();
        this.props.updateState("editButton", false);
        this.props.updateState(attr, value);
    }
    /** Close the studio session and reload the page. */
    async handleClose() {
        const currentApp = this.menuService.getCurrentApp();
        const appId = currentApp ? currentApp.id : false;

        let hasAccess = 0;
        if (appId) {
            // Check if the user has standard access to the app (without Studio's full_list context).
            hasAccess = await this.orm.searchCount("ir.ui.menu", [["id", "=", appId]]);
        }

        localStorage.setItem("cy_selected_app", appId || false)
        sessionStorage.removeItem("invisible");
        const currentUrl = new URL(window.location.href);
        currentUrl.searchParams.delete("studio");

        if (currentApp && !hasAccess) {
            // The user does not have menu access to the current app.
            // Redirect to the Home dashboard to avoid a blank navbar.
            RemoveSessions();
            currentUrl.hash = "#home";
            window.location.href = currentUrl.toString();
            return;
        }

        const currentModel = this.action.currentController?.action?.res_model;
        if (this._metaModelToFieldName[currentModel]) {
            // Exiting from a Configuration sub-view (Access Rights/Record
            // Rules/Reports) — land back on the real business view that was
            // open before it, instead of leaving the user stranded on this
            // meta-view outside Studio.
            const originModel = sessionStorage.getItem('CyConfigBusinessModel');
            const originViewType = sessionStorage.getItem('CyConfigBusinessViewType') || 'list';
            if (originModel) {
                const hashParams = new URLSearchParams(currentUrl.hash.replace(/^#/, ""));
                hashParams.set("model", originModel);
                hashParams.set("view_type", originViewType);
                hashParams.delete("id");
                hashParams.delete("action");
                currentUrl.hash = hashParams.toString();
            }
        }
        RemoveSessions()
        window.location.href = currentUrl.toString();
    }
    async undoChange() {
        const storage = JSON.parse(sessionStorage.getItem('UndoRedo') || '[]');
        if (!storage.length) {
            return; // nothing to undo
        }
        let view_type = this.props.viewDetails?.viewType;
        let view_id = this.props.viewDetails?.viewId;
        const model = this.props.viewDetails?.model;
        const searchViewId = sessionStorage.getItem("searchViewId");
        if (searchViewId) {
            view_type = 'search';
            view_id = searchViewId;
        }
        // Guard: a valid editable view must be open, else the server would try
        // to build a Studio view from an empty model / view id and crash.
        if (!view_id || !view_type || (!model && !searchViewId)) {
            this.notification.add("Open the view you want to undo changes on first.", {
                title: "Nothing to undo here",
                type: "warning",
            });
            return;
        }
        const undoElement = storage[storage.length - 1];
        let xPaths = false;
        const count = (undoElement.match(/<xpath /g) || []).length;
        if (count >= 2) {
            xPaths = true;
        }
        try {
            await this.rpc('cyllo_studio/undo_action', {
                model: model,
                view_type: view_type,
                view_id: view_id,
                xPaths: xPaths,
            });
        } catch (e) {
            this.notification.add("Could not undo the last change.", {
                title: "Undo failed",
                type: "danger",
            });
            return; // keep stacks intact so the action isn't lost
        }
        // Success: move the element from the undo stack onto the redo stack.
        storage.pop();
        sessionStorage.setItem('UndoRedo', JSON.stringify(storage));
        const redoStack = JSON.parse(sessionStorage.getItem('ReDO') || '[]');
        redoStack.push(undoElement);
        sessionStorage.setItem('ReDO', JSON.stringify(redoStack));
        this.action.doAction("studio_reload");
        this.env.bus.trigger('resetProperties');
        // window.location.reload();
    }

    async redoChange() {
        const storage = JSON.parse(sessionStorage.getItem('ReDO') || '[]');
        if (!storage.length) {
            return; // nothing to redo
        }
        let view_type = this.props.viewDetails?.viewType;
        let view_id = this.props.viewDetails?.viewId;
        const model = this.props.viewDetails?.model;
        const searchViewId = sessionStorage.getItem("searchViewId");
        if (searchViewId) {
            view_type = 'search';
            view_id = searchViewId;
        }
        // Guard: a valid editable view must be open (see undoChange).
        if (!view_id || !view_type || (!model && !searchViewId)) {
            this.notification.add("Open the view you want to redo changes on first.", {
                title: "Nothing to redo here",
                type: "warning",
            });
            return;
        }
        const redoElement = storage[storage.length - 1];
        try {
            await this.rpc('cyllo_studio/redo_action', {
                model: model,
                view_type: view_type,
                view_id: view_id,
                arch: redoElement,
            });
        } catch (e) {
            this.notification.add("Could not redo the change.", {
                title: "Redo failed",
                type: "danger",
            });
            return; // keep stacks intact
        }
        // Success: move the element from the redo stack back onto the undo stack.
        storage.pop();
        sessionStorage.setItem('ReDO', JSON.stringify(storage));
        const undoStack = JSON.parse(sessionStorage.getItem('UndoRedo') || '[]');
        undoStack.push(redoElement);
        sessionStorage.setItem('UndoRedo', JSON.stringify(undoStack));
        this.action.doAction("studio_reload");
        this.env.bus.trigger('resetProperties');
        // window.location.reload();
    }

}
CylloNavBar.props = {
    edit: {
        type: Boolean,
        optional: true
    },
    view: {
        type: Boolean,
        optional: true
    },
    editButton: {
        type: Boolean,
        optional: true
    },
    viewChanged: {
        type: Boolean,
        optional: true
    },
    updateState: {
        type: Function,
        optional: true
    },
    isAnimatingSidebar: {
        type: Boolean,
        optional: true
    },
    activity_view: {
        type: Boolean,
        optional: true
    },
    viewDetails: {
        type: Object,
        optional: true
    },
    isAI: {
        type: Boolean,
        optional: true
    },
};
CylloNavBar.components = {
    ViewSelectionDropDown,
};
