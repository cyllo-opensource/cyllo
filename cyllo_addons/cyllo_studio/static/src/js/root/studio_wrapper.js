/** @odoo-module **/
/**
 * StudioWrapper Component
 *
 * Acts as the central wrapper for Cyllo Studio's view editor in Odoo.
 *
 * Responsibilities:
 *  - Maintains overall state for fields, views, Kanban components, buttons, and notebooks.
 *  - Handles events from Odoo's event bus (useBus and addEventListener) for dynamic updates.
 *  - Updates and propagates view details to subcomponents (AsideBar, MainComponentsContainer, ActivityDialog, StudioMenuSideBar).
 *  - Manages X2Many session states and breadcrumbs.
 *  - Provides utility methods for form handling, validation, and state reloading.
 *  - Observes DOM mutations to adjust modal behavior.
 *
 * Props:
 *  - updateState: Function to propagate state updates.
 *  - info: Optional metadata object.
 *  - viewChanged: Optional boolean indicating if the view has changed.
 *  - edit: Optional boolean indicating if editing mode is active.
 */

import {
    Component,
    useState,
    onMounted,
    onWillUnmount
} from "@odoo/owl";
import {
    useBus
} from "@web/core/utils/hooks";
import {
    AsideBar
} from "@cyllo_studio/js/view_editor/aside_bar/aside_bar";
import {
    StudioMenuSideBar
} from "@cyllo_studio/js/studio_menu_sidebar/studio_menu_sidebar";
import {
    MainComponentsContainer
} from "@web/core/main_components_container";
import {
    ExistingFieldDialog
} from "@cyllo_studio/js/view_editor/aside_bar/dialog/existing_field_dialog";
import {
    useService
} from "@web/core/utils/hooks";
import {
    ActivityDialog
} from "@cyllo_studio/js/views/cyllo_activity/cyllo_activity_dailog";
import { CylloNavBar } from "@cyllo_studio/js/navbar/navbar";
import { RemoveSessions, validateEdit } from "@cyllo_studio/js/root/studio_utils";

// Re-export so existing importers of these helpers from studio_wrapper keep working.
export { RemoveSessions, validateEdit };

export class StudioWrapper extends Component {
    static template = "cyllo_studio.StudioWrapper";
    static props = {
        updateState: {
            type: Function,
            optional: true
        },
        info: {
            type: Object,
            optional: true
        },
        viewChanged: {
            type: Boolean,
            optional: true
        },
        edit: {
            type: Boolean,
            optional: true
        },
        viewProps: {
            type: Object,
            optional: true
        }
    };
    setup() {
        this.state = useState({
            isAnimatingSidebar: false,
            activity_view: false,
            isX2Many: sessionStorage.getItem('CyX2ManyPath') || false,
            x2Manylist: [],
            x2ManyTriggered: sessionStorage.getItem('CyX2ManyTriggered') || false,
            PrevModelName: '',
            FieldName: '',
        });
        this.dialogService = useService("dialog");
        this.action = useService('action');
        this.overall = useState({
            mode: {},
            allFields: {},
            activeFields: {},
            edit: this.props.edit,
            measure: {},
            isMenu: false,
            hasColorPicker: false,
            progressAttributes: {},
            envModel: {},
            ribbonElement: document.querySelectorAll("nonexistent-selector"),
            MetaData: {},
            calendar_info: {},
            model: '',
            isFieldTag: false,
            colorPickerPath: '',
            relational_model: '',
        });
        const savedPanel = sessionStorage.getItem('CyStudioActivePanel');
        this.viewDetails = useState({
            model: "",
            viewId: 0,
            viewType: "",
            type: savedPanel || "",
            allFields: {}
        });


        this.siblingProperties = useState({
            item_type: "",
            field_info: {},
            sibling: false,
        });


        this.fieldProperties = useState({
            attr: {},
            name: "",
            label: "",
            widget: "",
            fieldType: "",
            context: "",
            related_model: "",
            edit: "",
            path: "",
            help: "",
            placeholder: "",
            optional: "",
            column_invisible: "",
            invisible: "",
            readonly: "",
            create: "",
            field_path: "",
            label_path: "",
            widget_types: [],
        });
        this.kanbanComponent = useState({
            properties: "",
            item: "",
            element: "",
        });
        this.buttonInfo = useState({
            type: "",
        });
        this.noteBookProperties = useState({
            properties: "",
            invisible: "",
            type: "",
            autofocus: "",
        });
        this.SmartButtonProperties = useState({
            properties: "",
            path: "",
            type: "",
            addButtonBox: "",
        });
        this.ButtonDetails = useState({
            name: "",
            type: "",
            path: "",
            position: "",
            class_name: "",
            string: "",

        })
        this.KanbanDivProperties = useState({
            type: "",
            path: "",
            div: "",

        })
        const savedSpanProps = sessionStorage.getItem('CyStudioSpanProperties');
        let initialSpanProps = {
            string: "",
            bold: "",
            italic: "",
            underline: "",
            is_edit: "",
            element: "",
            view_id: "",
            model: "",
            view_type: "",
            properties: "",
            item: ""
        };
        if (savedSpanProps) {
            try {
                Object.assign(initialSpanProps, JSON.parse(savedSpanProps));
            } catch (e) { }
        }
        this.KanbanSpanProperties = useState(initialSpanProps);
        this.ActivityDetails = useState({
            archInfo: "",
            fields: "",
            activityResIds: "",
            records: "",
        })
        this.handleFormDetails = this.handleFormDetails.bind(this);
        this.handleListDetails = this.handleListDetails.bind(this);
        this.handlePivotDetails = this.handlePivotDetails.bind(this);
        this.handleKanbanDetails = this.handleKanbanDetails.bind(this);
        this.handleKanbanFieldsDetails = this.handleKanbanFieldsDetails.bind(this);
        this.handleCalendarDetails = this.handleCalendarDetails.bind(this);
        this.handleGraphDetails = this.handleGraphDetails.bind(this);
        this.handleKanbanComponent = this.handleKanbanComponent.bind(this);
        this.handleActivityDetails = this.handleActivityDetails.bind(this);
        this.handleButtonInfo = this.handleButtonInfo.bind(this);
        this.handleClearMenu = this.handleClearMenu.bind(this);
        this.handleKanbanDiv = this.handleKanbanDiv.bind(this);
        this.handleKanbanSpan = this.handleKanbanSpan.bind(this);
        this.handleAsideMenu = this.handleAsideMenu.bind(this);
        this.handleNotebookDetails = this.handleNotebookDetails.bind(this);
        this.handleSmartButtonDetails = this.handleSmartButtonDetails.bind(this);
        this.reload = this.reload.bind(this);
        this.state.PrevModelName = JSON.parse(sessionStorage.getItem("PrevForm"))?.ModelName
        this.state.FieldName = JSON.parse(sessionStorage.getItem("PrevForm"))?.FieldName

        useBus(this.env.bus, 'CLEAR-MENU', this.handleClearMenu.bind(this));
        useBus(this.env.bus, 'ASIDE-MENU', this.handleAsideMenu.bind(this));
        useBus(this.env.bus, 'KANBAN_COMPONENT', this.handleKanbanComponent.bind(this));
        useBus(this.env.bus, "BUTTON_INFO", this.handleButtonInfo);
        useBus(this.env.bus, "PIVOT_DETAILS", this.handlePivotDetails);
        useBus(this.env.bus, "LIST_DETAILS", this.handleListDetails);
        useBus(this.env.bus, "ACTIVITY_DETAILS", this.handleActivityDetails);
        useBus(this.env.bus, "ACTIVITY_REMOVED", this.handleActivityRemoved);
        useBus(this.env.bus, "SEARCH_VIEW_OPENED", this.closeAsideBar.bind(this));
        useBus(this.env.bus, "CY_META_VIEW_OPENED", this.closeAsideBar.bind(this));
        useBus(this.env.bus, "SELECT_NOTEBOOK", this.handleNotebookDetails);
        useBus(this.env.bus, "RENDER_LOAD", this.reload);
        useBus(this.env.bus, "FORM_DETAILS", this.handleFormDetails);
        useBus(this.env.bus, "SMART_BUTTON_DETAILS", this.handleSmartButtonDetails);
        useBus(this.env.bus, "KANBAN_DETAILS", this.handleKanbanDetails);
        useBus(this.env.bus, "KANBAN_FIELD_DETAILS", this.handleKanbanFieldsDetails);
        useBus(this.env.bus, "KANBAN_DIV", this.handleKanbanDiv);
        useBus(this.env.bus, "kanbanSpanDetails", this.handleKanbanSpan);
        useBus(this.env.bus, "CALENDAR_DETAILS", this.handleCalendarDetails);
        useBus(this.env.bus, "GRAPH_DETAILS", this.handleGraphDetails);
        useBus(this.env.bus, "SIBLING_DETAILS", this.handleSiblingDetails);
        this.handleSiblingDetails = this.handleSiblingDetails.bind(this);
        this.handleRelationalModel = this.handleRelationalModel.bind(this);
        useBus(this.env.bus, "SET_MODEL", this.handleRelationalModel);
        useBus(this.env.bus, "SPAN_DETAILS", this.handleSpanDetails);
        this.handleSpanDetails = this.handleSpanDetails.bind(this);

        this.handleFieldDetails = this.handleFieldDetails.bind(this);
        this.handleButtonDetails = this.handleButtonDetails.bind(this);
        this.handleExistingField = this.handleExistingFieldDetails.bind(this);
        useBus(this.env.bus, "FIELDS_DETAILS", this.handleFieldDetails);
        useBus(this.env.bus, "BUTTON_DETAILS", this.handleButtonDetails);
        useBus(this.env.bus, "LIST_EXISTING_FIELDS", this.handleExistingField);

        // Back navigation for the x2many breadcrumb now rendered in the navbar.
        useBus(this.env.bus, "STUDIO_BREADCRUMB_BACK", () =>
            this.handleForm({ preventDefault: () => { } })
        );

        this.env.bus.addEventListener('X2ManyDetails', ({ detail }) => {
            this.state.isX2Many = !!sessionStorage.getItem('CyX2ManyPath');
            this.state.x2Manylist = detail?.x2Manylist || [];
        });
        this.env.bus.addEventListener('X2Many-Breadcrumbs', ({ detail }) => {
            this.state.PrevModelName = detail.ModelName;
            this.state.FieldName = detail.FieldName;
            this.state.x2ManyTriggered = 'true'; // Set to 'true' to show breadcrumbs
            sessionStorage.setItem('CyX2ManyTriggered', 'true'); // Update sessionStorage for persistence
        });

        this.env.bus.addEventListener('resetProperties', (ev) => {
            this.state.appMenu = true;
            this.state.MenuDraggable = true;
            this.state.new_field_property = false;
        });


        onMounted(() => {
            this.props.updateState("viewDetails", this.viewDetails);
        });
        useBus(this.env.bus, 'StudioWrapperUpdateState', ({ detail }) => {
            this.updateState()
        });

        const observer = new MutationObserver(() => {    //adding observer to observe the mutations in dom
            const modalHeader = document.querySelector('.modal-header');
            if (modalHeader) {
                modalHeader.className = 'modal-header-no-drag';
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
        });

        onWillUnmount(() => {
            if (observer) {
                observer.disconnect();
            }
        });
    }
    updateViewDetails(detail) {
        if (detail) {
            Object.assign(this.viewDetails, {
                model: detail.model ?? this.viewDetails.model,
                viewId: detail.viewId ?? this.viewDetails.viewId,
                viewType: detail.viewType ?? this.viewDetails.viewType,
                type: detail.type ?? this.viewDetails.type,
                allFields: (detail.allFields ?? this.viewDetails.allFields) || {}
            });
        }
    }
    /**
     * Reloads the current Studio view.
     * Triggers 'studio_reload' action and resets editing state after 100ms,
     * unless the event asks to keep the aside bar open (e.g. auto-save).
     */
    reload({ detail } = {}) {
        this.action.doAction("studio_reload");
        if (detail?.keepEdit) {
            return;
        }
        setTimeout(() => {
            this.props.updateState("edit", false);
        }, 100);
    }
    /**
     * Closes the aside bar (Studio has no editor panel for the search
     * view, so a currently-open panel would otherwise be left stale).
     */
    closeAsideBar() {
        if (!this.props.edit) {
            return;
        }
        this.state.activity_view = false;
        this.env.bus.trigger("CLEAR-MENU", { fromClose: true });
        this.props.updateState("edit", false);
    }
    /**
     * Handles displaying existing fields dialog.
     * Opens a modal with existing fields for the current model and view.
    */
    handleExistingFieldDetails() {
        this.dialogService.add(ExistingFieldDialog, {
            fields: this.overall.allFields,
            model: this.viewDetails.model,
            viewType: this.viewDetails.viewType,
            viewId: this.viewDetails.viewId,
        });
    }
    handleView(ev) {
        this.viewDetails.type = ev.target.innerText;
    }
    /**
     * Handles form details update from the bus event.
     * Updates overall mode, allFields, activeFields, and viewDetails.
     *
     * @param {Object} param0.detail - Object containing form detail data.
     */
    handleFormDetails({
        detail
    }) {
        if (detail) {
            Object.assign(this.overall, {
                mode: detail.mode,
                allFields: detail.allFields,
                activeFields: detail.activeFields,
            });
            this.updateViewDetails(detail);
            this.viewDetails.type = '';
        }
    }

    handleRelationalModel({ detail }) {
        if (detail) {
            sessionStorage.setItem("RelationalModel", Flatted.stringify(detail.relational_model))
            Object.assign(this.overall, {
                relational_model: detail.relational_model,
            });
        }
    }

    /**
     * Handles updating sibling field details.
     *
     * @param {Object} param0.detail - Object containing sibling field detail data.
     */
    handleSiblingDetails({
        detail
    }) {
        if (detail) {
            this.siblingProperties.sibling_edit = detail.sibling_edit;
            const props = {
                type: detail.type,
                sibling: detail.sibling,
                item_type: detail.item_type,
                field_info: detail.field_info,
                sibling_edit: detail.sibling_edit,
            };

            if (detail.cy_path) {
                props.path = detail.cy_path;  // Add only if path is not empty
            }

            Object.assign(this.siblingProperties, props);
            Object.assign(this.fieldProperties, {
                attr: detail.mode,
                name: detail.name,
                string: detail.label,
                widget: detail.widget,
                options: detail.options,
                fieldType: detail.fieldType,
                context: detail.context,
                related_model: detail.related_model,
                edit: detail.edit || false,
                path: detail.cy_path || "",
                help: detail.help,
                placeholder: detail.placeholder || "",
                dynamic_placeholder: detail.dynamic_placeholder || "",
                invisible: detail.invisible || "",
                readonly: detail.readonly,
                required: detail.required,
                create: detail.create,
                field_path: detail.field_path || "",
                domain: detail.domain || "",

            });
            Object.assign(this.kanbanComponent, {
                bold: detail.bold,
                italic: detail.italic,
                underline: detail.underline,
                path: detail.cy_path,
                type: detail.type,
                classNames: detail.classNames,
                string: detail.string,
                is_edit: detail.is_edit,
                invisible: detail.invisible || '',
            });
            this.updateViewDetails(detail);
        }
    }

    handleSpanDetails({
        detail
    }) {
        if (detail) {
            this.fieldProperties.create = detail.create
            this.siblingProperties.sibling = detail.sibling
            this.siblingProperties.path = detail.path
            this.siblingProperties.sibling_edit = detail.sibling_edit,
                Object.assign(this.kanbanComponent, {
                    bold: detail.bold,
                    italic: detail.italic,
                    underline: detail.underline,
                    element: detail.element,
                    path: detail.path,
                    type: detail.type,
                    classNames: detail.classNames,
                    string: detail.string,
                    is_edit: detail.is_edit,
                    invisible: detail.invisible,
                });
            this.updateViewDetails(detail);
        }
    }


    /**
     * Handles button details update.
     *
     * @param {Object} param0.detail - Object containing button detail data.
     */
    handleButtonDetails({
        detail
    }) {
        if (detail) {
            this.fieldProperties.create = detail.create;
            this.siblingProperties.sibling_edit = false;
            Object.assign(this.ButtonDetails, {
                name: detail.name || "",
                function_type: detail.function_type || "",
                function_name: detail.function_name || "",
                path: detail.path || "",
                style: detail.style || "button",
                newHeader: detail.newHeader || false,
                newButton: detail.newButton || false,
                position: detail.position || "",
                class_name: detail.class || "",
                string: detail?.string || "",
                groupIds: Array.isArray(detail?.groupIds) ? detail.groupIds : [],
                icon: detail?.icon || '',
                invisible: detail.invisible || '',
                element: detail.element || '',
                spanxpath: detail.spanxpath || "",
            });
            this.updateViewDetails(detail);
        }
    }
    /**
     * Handles list view details update.
     *
     * @param {Object} param0.detail - Object containing list view detail data.
     */
    handleListDetails({
        detail
    }) {
        if (detail) {
            this.ButtonDetails.newButton = false;
            Object.assign(this.overall, {
                mode: detail.mode,
                allFields: detail.allFields,
                activeFields: detail.activeFields,
            });
            this.updateViewDetails(detail);
            this.viewDetails.type = '';
        }
    }
    /**
    * Handles activity view details update.
    *
    * @param {Object} param0.detail - Object containing activity detail data.
    */
    handleActivityDetails({
        detail
    }) {
        if (detail) {
            this.state.activity_view = true
            Object.assign(this.ActivityDetails, {
                archInfo: detail.archInfo,
                fields: detail.fields,
                activityResIds: detail.activityResIds,
                records: detail.records,
                model: detail.model,
                viewId: detail.viewId,
                viewType: detail.viewType,
            });
            this.updateViewDetails(detail);
        } else {
            this.state.activity_view = false
        }
    }
    handleActivityRemoved({ detail }) {
        if (detail) {
            this.state.activity_view = detail.activity
        }
    }
    /**
     * Handles graph view details update.
     *
     * @param {Object} param0.detail - Object containing graph view detail data.
     */
    handleGraphDetails({
        detail
    }) {
        if (detail) {
            Object.assign(this.overall, {
                mode: detail.mode,
                allFields: detail.allFields,
                MetaData: detail.envModel,
            });
            this.updateViewDetails(detail);
            this.viewDetails.type = '';
        }
    }
    async handleFieldDetails({
        detail
    }) {
        if (detail) {
            this.props.updateState("editButton", false);
            this.siblingProperties.sibling = false;
            this.siblingProperties.sibling_edit = false;
            this.ButtonDetails.newButton = false;
            Object.assign(this.fieldProperties, {
                attr: detail.mode,
                name: detail.name,
                string: detail.label,
                widget: detail.widget,
                options: detail.options,
                fieldType: detail.fieldType,
                context: detail.context,
                related_model: detail.related_model,
                edit: detail.edit || false,
                path: detail.cy_path || "",
                help: detail.help,
                placeholder: detail.placeholder || "",
                dynamic_placeholder: detail.dynamic_placeholder || "",
                optional: detail?.mode?.optional || "",
                column_invisible: detail.column_invisible || "",
                invisible: detail.invisible || "",
                readonly: detail.readonly,
                required: detail.required,
                create: detail.create,
                field_path: detail.field_path || "",
                label_path: detail.label_path || "",
                domain: detail.domain || "",
                position: detail.position || "",
                recordData: detail.recordData || {},
            });
            this.updateViewDetails(detail);
        }
    }
    // KANBAN VIEW
    /**
     * Handles Kanban view details update.
     *
     * @param {Object} param0.detail - Object containing Kanban view detail data.
     */
    handleKanbanDetails({
        detail
    }) {
        if (detail) {
            Object.assign(this.overall, {
                allFields: detail.allFields,
                mode: detail.attributes,
                isMenu: detail.isMenu,
                hasColorPicker: detail.hasColorPicker,
                colorPickerPath: detail.colorPickerPath,
                progressAttributes: detail.progressAttributes || {},
                ribbonElement: detail.ribbonElement || document.querySelectorAll("nonexistent-selector"),
                fieldNodes: detail.fieldNodes,
                widget: detail.widget,
            });
            this.updateViewDetails(detail);
            this.viewDetails.type = '';
        }
    }
    /**
     * Handles Kanban field-specific details update.
     *
     * @param {Object} param0.detail - Object containing Kanban field detail data.
     */
    handleKanbanFieldsDetails({
        detail
    }) {
        if (detail) {
            Object.assign(this.overall, {
                activeFields: detail.active_fields,
                allFields: detail.allfields,
                mode: detail.attributes || this.overall.mode,
                isMenu: detail.isMenu,
                hasColorPicker: detail.hasColorPicker,
                colorPickerPath: detail.colorPickerPath,
                progressAttributes: detail.progressAttributes || {},
                ribbonElement: detail.ribbonElement || document.querySelectorAll("nonexistent-selector"),
                isFieldTag: detail.isFieldTag,
                invisible: detail.invisible || '',
                widget: detail.widget,
            });
            Object.assign(this.fieldProperties, {
                attr: detail.mode,
                name: detail.name,
                string: detail.label,
                widget: detail.widget,
                options: detail.options,
                fieldType: detail.fieldType,
                context: detail.context,
                related_model: detail.related_model,
                edit: detail.edit || false,
                path: detail.path || "",
                help: detail.help,
                placeholder: detail.placeholder || "",
                dynamic_placeholder: detail.dynamic_placeholder || "",
                invisible: detail.invisible || "",
                readonly: detail.readonly,
                required: detail.required,
                create: detail.create,
                field_path: detail.field_path || "",
                domain: detail.domain || "",
                recordData: detail.recordData || {}
            });
            this.updateViewDetails(detail);
        }
    }
    handleKanbanDiv({ detail }) {
        if (detail) {
            Object.assign(this.KanbanDivProperties, {
                type: detail.type,
                div: detail.div,
                path: detail.path || "",
            });
            this.updateViewDetails(detail);
        }
    }

    handleKanbanSpan({ detail }) {
        if (detail) {
            Object.assign(this.KanbanSpanProperties, {
                string: detail.string,
                bold: detail.bold,
                italic: detail.italic,
                underline: detail.underline,
                is_edit: detail.is_edit,
                element: detail.element,
                view_id: detail.view_id,
                model: detail.model,
                view_type: detail.view_type,
                type: detail.type,
                properties: detail.properties,
                newButton: detail.newButton,
            });
            this.updateViewDetails(detail);
            if (detail.type) {
                sessionStorage.setItem('CyStudioActivePanel', detail.type);
                sessionStorage.setItem('CyStudioSpanProperties', JSON.stringify({
                    string: detail.string,
                    bold: detail.bold,
                    italic: detail.italic,
                    underline: detail.underline,
                    is_edit: detail.is_edit,
                    view_id: detail.view_id,
                    model: detail.model,
                    view_type: detail.view_type,
                    type: detail.type,
                }));
            }
        }
    }

    handleCalendarDetails({
        detail
    }) {
        if (detail) {
            Object.assign(this.overall, {
                mode: detail.mode,
                model: detail.model,
                activeFields: detail.activeFields,
                calendar_info: detail.calendar_info
            });
            this.updateViewDetails(detail);
            this.viewDetails.type = '';
        }
    }
    /**
    * Handles pivot view details update.
    *
    * @param {Object} param0.detail - Object containing pivot detail data.
    */
    handlePivotDetails({
        detail
    }) {
        if (detail) {
            Object.assign(this.overall, {
                activeFields: detail.active_fields,
                measure: detail.measure,
                mode: detail.metaData,
                envModel: detail.envModel,
            });
            this.updateViewDetails(detail);
            this.viewDetails.type = '';
        }
    }
    handleKanbanComponent({
        detail
    }) {
        if (detail) {
            this.siblingProperties.sibling = false;
            this.fieldProperties.create = false;
            Object.assign(this.kanbanComponent, {
                properties: detail.properties,
                type: detail.type,
                element: detail.element,
                newButton: detail.newButton,
                bold: detail.bold,
                italic: detail.italic,
                underline: detail.underline,
                classNames: detail.classNames,
                string: detail.string,
                is_edit: detail.is_edit,
                invisible: detail.invisible || '',
            });
            this.updateViewDetails(detail);
        }
    }
    /**
    * Handles smart button details update.
    *
    * @param {Object} param0.detail - Object containing smart button detail data.
    */
    handleSmartButtonDetails({ detail }) {
        if (detail) {
            Object.assign(this.SmartButtonProperties, {
                properties: detail.properties,
                path: detail.path,
                type: detail.type,
                addButtonBox: detail.addButtonBox,
                new_button: detail.new_button,

            });
            this.updateViewDetails(detail);
        }
    }
    handleButtonInfo({
        detail
    }) {
        if (detail) {
            Object.assign(this.buttonInfo, {
                newViewId: detail.newViewId,
                envModel: detail.envModel,
                newHeader: detail.newHeader,
                path: detail.path,
            });
            this.updateViewDetails(detail);
        }
    }
    handleAsideMenu() {
        this.viewDetails.type = 'View'
    }
    handleClearMenu(params) {
        // Only editable views get the "Edit View" button back. Client actions
        // (dashboards, report viewer, etc.) carry a `componentProps.action` and
        // are not editable — re-showing Edit View there is wrong, and caused it
        // to reappear on dashboards whenever CLEAR-MENU fired.
        const isClientAction = !!this.props.info?.componentProps?.action;
        this.props.updateState("editButton", !isClientAction);
        this.props.edit = false;
        this.viewDetails.type = '';
        sessionStorage.removeItem('KanbanEdit');
        sessionStorage.removeItem("newListElement");
        sessionStorage.removeItem("CyStudioActivePanel");
        sessionStorage.removeItem("CyStudioSpanProperties");
    }
    handleNotebookDetails({
        detail
    }) {

        if (detail) {
            Object.assign(this.noteBookProperties, {
                properties: detail.properties,
                invisible: detail.invisible || '',
                type: detail.type,
                autofocus: detail.autofocus,

            });
            this.updateViewDetails(detail);
        }
    }
    get asideProps() {
        return {
            overall: this.overall,
            viewDetails: this.viewDetails,
            fieldProperties: this.fieldProperties,
            kanbanComponent: this.kanbanComponent,
            noteBookProperties: this.noteBookProperties,
            SmartButtonProperties: this.SmartButtonProperties,
            ButtonDetails: this.ButtonDetails,
            KanbanDivProperties: this.KanbanDivProperties,
            KanbanSpanProperties: this.KanbanSpanProperties,
            type: this.viewDetails.type || (this.props.edit ? "View" : ""),
            handleView: this.handleView.bind(this),
            isAnimatingSidebar: this.state?.isAnimatingSidebar,
            activity_view: this.state?.activity_view,
            isX2Many: this.state?.isX2Many,
            x2Manylist: this.state?.x2Manylist,
            updateState: this.props.updateState,
            editButton: this.props.editButton,
            sibling: this.siblingProperties,
        };
    }
    get asideBarAvailable() {
        return this.props.edit || this.viewDetails.type;
    }
    get activityProps() {
        return {
            ...this.ActivityDetails,
            updateState: this.props.updateState,
        };
    }
    /**
     * Handles form navigation in Studio.
     * Clears sessions and reloads the page or navigates to the previous view.
     */
    handleForm(e) {
        e.preventDefault(); // Prevent default link behavior
        RemoveSessions()
        this.state.x2ManyTriggered = 'false';
        this.state.PrevModelName = '';
        this.state.FieldName = '';
        this.env.bus.trigger('resetProperties');
        if (this.state.isX2Many) {
            // Soft (in-SPA) reload instead of window.location.reload() so the
            // breadcrumb back-nav doesn't trigger a full browser page load.
            // State + sessions are already cleared above, so the current
            // action (the parent form) re-renders without the x2many drill.
            this.action.doAction("studio_reload");
        } else {
            const PrevViewData = JSON.parse(sessionStorage.getItem('PrevForm'));
            if (PrevViewData) {
                window.location.hash = `action=${PrevViewData.ActionId}&model=${PrevViewData.modelId}&view_type=${PrevViewData.ViewId}`;
            }
        }
    }

    updateState() {
        this.state.activity_view = false
    }
    handleReportBack() {
        const parentModel = this.props.info?.componentProps?.action?.context?.parent_model;

        if (parentModel) {
            this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: parentModel,
                views: [[false, 'list'], [false, 'form']],
                target: 'current',
            });
        } else {
            window.history.back();
        }
    }
}
StudioWrapper.components = {
    AsideBar,
    MainComponentsContainer,
    ActivityDialog,
    StudioMenuSideBar,
    CylloNavBar,
};