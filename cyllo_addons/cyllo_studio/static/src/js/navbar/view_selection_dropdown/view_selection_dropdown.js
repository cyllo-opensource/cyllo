/** @odoo-module **/
/**
 * ViewSelectionDropDown Component
 *
 * Dropdown for selecting and managing active Odoo Studio views
 * (list, kanban, form, activity, graph, pivot, search, calendar).
 *
 * Props:
 * - viewChange: Callback for view state changes.
 *
 * State:
 * - activatedViews: Active views array.
 * - currentViewType: Currently active view.
 * - defaultView: Default view type.
 * - activity: True if model has mail activity.
 *
 * Key Methods:
 * - onViewClicked: Switch view and update session.
 * - onSearchClick: Handle search view click.
 * - toggleViewDropdown / closeDropdown: Manage dropdown.
 * - onClickBox: Toggle view activation safely.
 * - handleDefaultView: Set default view.
 */
import {
    Component,
    useState,
    onMounted,
    onWillStart,
    useRef
} from "@odoo/owl";
import {
    useService
} from "@web/core/utils/hooks";
import {
    CalendarDialog
} from "@cyllo_studio/js/view_editor/dialog/calendar_dialog";

// Mapping of view types to icon classes
const ICONCLASS = {
    list: "ri-table-line",
    form: "ri-profile-line",
    activity: "ri-time-line",
    search: "ri-search-line",
    kanban: "ri-bar-chart-2-line",
    calendar: "ri-calendar-line",
    pivot: "ri-layout-2-line",
    gantt: "ri-bar-chart-horizontal-line",
    graph: "ri-line-chart-line",
    map_view: "ri-map-pin-line",
};

// Supported view types
const ViewTypes = [
    "list",
    "kanban",
    "form",
    "activity",
    "graph",
    "pivot",
    "search",
    "calendar",
];

export class ViewSelectionDropDown extends Component {
    static template = "cyllo_studio.ViewSelectionDropDown";
    setup() {
        this.state = useState({
            activatedViews: [],
            currentViewType: null,
        });
        this.ViewTypes = ViewTypes;
        this.viewIcons = ICONCLASS;
        this.root = useRef("root");
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.dialogService = useService("dialog");


        onMounted(async () => {
            // Listen for updates on active views
            await this.env.bus.addEventListener("ACTIVE-VIEWS", ({ detail }) => {
                const storedView = sessionStorage.getItem("cyStudioActiveView");

                this.state.activatedViews = (detail.views || []).map(view => view[1]);

                if (storedView === "search") {
                    this.state.currentViewType = 'search';
                    // Force search to stay active even after refresh
                    setTimeout(() => {
                        this.env.bus.trigger("SEARCH_CLICKED");
                        this.props.viewChange("editButton", false);
                    }, 0);
                } else {
                    // Normal behavior
                    this.state.currentViewType = detail.viewType;
                }

                this.state.defaultView =
                    sessionStorage.getItem('CylloDefaultView') || detail.views[0][1];

                sessionStorage.removeItem('CylloDefaultView');
            });

            // Determine if the model has mail activity
            const url = new URL(window.location.href);
            const hashParams = new URLSearchParams(url.hash.slice(1));
            const model = hashParams.get("model");
            const activity = await this.orm.searchRead("ir.model", [
                ["model", "=", model],
                ["is_mail_activity", "=", true],
            ], ["is_mail_activity", "state"]);
            this.state.activity = activity[0] ? true : false
            window.addEventListener("click", (e) => {
                if (this.root.el?.querySelector(".hnk-dropdown--open")) {
                    this.closeDropdown.bind(this)(e);
                }
            });
        });
    }
    getViewIcon(view) {
        const cls = ICONCLASS[view] || '';
        return this.state.currentViewType === view ? cls.replace(/-line$/, '-fill') : cls;
    }

    onViewClicked(view, e) {
        // Trigger studio state update
        this.env.bus.trigger("StudioWrapperUpdateState", {})
        this.state.currentViewType = view;
        document.querySelectorAll('.view-icons').forEach(el => {
            el.classList.remove('active');
        });
        const clickedElement = e.currentTarget;
        clickedElement.classList.add("active")
        this.action.switchView(view);
        const viewFlags = {
            editButton: true,
            edit: false,
            viewChanged: true
        };
        for (const [key, value] of Object.entries(viewFlags)) {
            this.props.viewChange(key, value);
        }
        sessionStorage.removeItem("cyStudioSearch");
        sessionStorage.removeItem('CyX2Many');
        sessionStorage.removeItem('CyX2ManyPath');
        sessionStorage.removeItem("searchViewId");
        sessionStorage.removeItem("cyStudioActiveView");
        const viewData = sessionStorage.getItem("myViewData");
        if (viewData?.trim() !== view?.trim()) {
            sessionStorage.setItem("myViewData", view);
            sessionStorage.setItem('UndoRedo', JSON.stringify([]));
            sessionStorage.setItem('ReDO', JSON.stringify([]));
        }


    }
    onSearchClick(e) {
        this.state.currentViewType = 'search';
        document.querySelectorAll('.view-icons').forEach(el => {
            el.classList.remove('active');
        });

        // Add 'active' class to the clicked one
        const clickedElement = e.currentTarget;
        clickedElement.classList.add('active');
        this.env.bus.trigger("SEARCH_CLICKED");
        this.props.viewChange("editButton", false);
        sessionStorage.setItem("cyStudioActiveView", "search");
        sessionStorage.removeItem('CyX2Many');
        sessionStorage.removeItem('CyX2ManyPath');
        const viewData = sessionStorage.getItem("myViewData");
        if (viewData !== "search") {
            sessionStorage.setItem("myViewData", "search");
            sessionStorage.setItem('UndoRedo', JSON.stringify([]));
            sessionStorage.setItem('ReDO', JSON.stringify([]));
        }
    }
    toggleViewDropdown(e) {
        const parent = document.querySelector(".hnk-dropdown");
        if (!parent) return;
        parent.classList.toggle("hnk-dropdown--open");
    }
    closeDropdown(e) {
        const clickedDropdown = e.target.closest(".hnk-dropdown");
        if (!clickedDropdown) {
            this.root.el?.querySelectorAll(".hnk-dropdown").forEach(dropdown =>
                dropdown.classList.remove("hnk-dropdown--open")
            );
        }
    }
    async onClickBox(e) {
        const activeView = e.target.checked
        const viewType = e.target.attributes.target.value
        if (this.action.currentController.config.actionId) {
            if (this.state.activatedViews.length <= 2 && !activeView && viewType !== 'search') {
                e.target.checked = true;
                return this.action.doAction({
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'At least one view is required.',
                        'type': 'warning',
                        'sticky': false,
                    }
                })
            }
            if (viewType !== 'calendar' || !activeView) {
                await this.rpc("/cyllo_studio/view/active_views", {
                    args: [{
                        activeView,
                        actionId: this.action.currentController.config.actionId,
                        actionType: this.action.currentController.config.actionType,
                        viewType,
                        resModel: this.action.currentController.action.res_model,
                        name: this.action.currentController.action.name,
                    }]
                })
                window.location.reload()
            } else if (activeView) {
                // CalendarDialog.loadFields() fetches fields via fields_get on
                // details[0].resModel when fields is empty — no need to reach
                // into owl internals (brittle, crashed with undefined 'overall').
                this.dialogService.add(CalendarDialog, {
                    fields: {},
                    details: [{
                        activeView,
                        actionId: this.action.currentController.config.actionId,
                        actionType: this.action.currentController.config.actionType,
                        viewType,
                        resModel: this.action.currentController.action.res_model,
                        name: this.action.currentController.action.name,
                    }]
                })
            }
        }
    }

    async handleDefaultView(ev) {
        const parentElement = ev.target.parentElement
        const siblings = Array.from(parentElement.children).filter((child) => child !== ev.target);
        const siblingWithType = siblings.find((sibling) => sibling.hasAttribute('target'));
        const siblingType = siblingWithType.getAttribute('target')
        this.result = await this.rpc("/cyllo_studio/view/active_views/set_default_view", {
            args: [{
                'actionId': this.action.currentController.config.actionId,
                'siblingType': siblingType,
            }]
        })
        this.state.defaultView = siblingType
        sessionStorage.setItem('CylloDefaultView', this.state.defaultView);
        this.action.doAction('studio_reload')
    }
}