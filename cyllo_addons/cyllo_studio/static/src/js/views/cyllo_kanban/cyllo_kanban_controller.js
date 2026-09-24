/** @odoo-module **/

/**
 * CylloKanbanController
 *
 * Extends Odoo's KanbanController to provide custom behavior for Cyllo Studio Kanban views.
 *
 * Key Features:
 * - Handles automatic creation of a Kanban view if it does not exist.
 * - Emits detailed information about the Kanban view to the bus for other components.
 * - Supports ribbon elements, color pickers, and foldable groups.
 * - Integrates with Odoo services: rpc, dialog, and action.
 */
import {KanbanController} from "@web/views/kanban/kanban_controller";
import {
    KANBAN_BOX_ATTRIBUTE,
    KANBAN_MENU_ATTRIBUTE,
    KANBAN_TOOLTIP_ATTRIBUTE,
} from "@web/views/kanban/kanban_arch_parser";
import { Layout } from "@web/search/layout";
import {onWillStart, onMounted, onWillDestroy, useRef} from "@odoo/owl";
import {useService, useOwnedDialogs} from "@web/core/utils/hooks";
import { serializeXML } from "@web/core/utils/xml";
import { session } from "@web/session";
import { addFieldDependencies, extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { ReportCreationDialog } from "@cyllo_studio/js/control_panel/report_creation_dialog";


export class CylloKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.rpc = useService('rpc')
        this.dialogService = useService("dialog");
        this.action = useService("action");
        this.addDialog = useOwnedDialogs();
        onWillStart(async ()=>{
        if(!this.env.config.viewId){
                await this.rpc('cyllo_studio/form/add/kanban_view',{
                    arch: serializeXML(this.props.arch),
                    model: this.props.resModel,
                })
                await this.action.doAction('studio_reload')
            }
        })
        onMounted(async () => {
            if (this.props.resModel === 'ir.actions.report') {
                document.body.classList.add('cy-report-kanban-view-active');
            }
            const ribbonElement = document.querySelectorAll('[data-ribbon="1"]')
            const colorPickerEL = this.props.arch.querySelector("templates .oe_kanban_colorpicker[data-field]")
            const hasColorPicker = !!colorPickerEL
            const colorPickerPath = colorPickerEL ? colorPickerEL.getAttribute('cy-xpath') : ''
            this.env.bus.trigger('KANBAN_DETAILS', {
                viewType: this.env.config.viewType,
                model: this.model.env.searchModel.resModel,
                viewId: this.env.config.viewId,
                fields: this.props.fields,
                isMenu: KANBAN_MENU_ATTRIBUTE in this.props.archInfo.templateDocs,
                hasColorPicker,
                activeFields: this.model.config.activeFields,
                colorPickerPath,
                progressAttributes: this.props.archInfo.progressAttributes,
                ribbonElement: ribbonElement.length == 0 ? false : ribbonElement,
                fieldNodes: this.props.archInfo.fieldNodes,
                attributes: {
                    create: this.props.archInfo.activeActions.create,
                    quickCreate: this.props.archInfo.activeActions.quickCreate,
                    defaultGroupBy: this.props.archInfo.defaultGroupBy,
                    recordsDraggable: this.props.archInfo.recordsDraggable,
                    groupsDraggable: this.props.archInfo.groupsDraggable,
                }
            });
            const { root } = this.model;
            if(root.groups){
                const firstGroup = root.groups[0];
                if (firstGroup?.isFolded) {
                    await firstGroup.toggle();
                }
            }

        })

        onWillDestroy(() => {
            if (this.props.resModel === 'ir.actions.report') {
                document.body.classList.remove('cy-report-kanban-view-active');
            }
        });
    }

    /**
     * The Reports kanban has no dedicated create flow of its own (no form
     * view worth showing) — route "+ New" (from every entry point: the
     * kanban's own button, and CogMenuList's) through the same report
     * creation wizard the control panel's separate "+ New" button opens.
     */
    createRecord() {
        if (this.props.resModel === 'ir.actions.report') {
            this.addDialog(ReportCreationDialog, {});
            return;
        }
        return super.createRecord();
    }

     /**
     * Get model parameters for the Kanban view.
     *
     * Extracts fields and activeFields, adds field dependencies, and returns
     * a configuration object for the Kanban model.
     *
     * @returns {Object} modelParams - Configuration parameters for the Kanban model.
     */
    get modelParams() {
    const { resModel, archInfo, limit, defaultGroupBy } = this.props;
    const { activeFields, fields } = extractFieldsFromArchInfo(archInfo, this.props.fields);
    addFieldDependencies(activeFields, fields, this.progressBarAggregateFields);
    const modelConfig = {
        resModel,
        activeFields,
        fields,
        openGroupsByDefault: true,
    } || this.props.state?.modelState?.config;
    return {
        config: modelConfig,
        state: this.props.state?.modelState,
        limit: archInfo.limit || limit || 40,
        groupsLimit: Number.MAX_SAFE_INTEGER,
        countLimit: archInfo.countLimit,
        defaultGroupBy,
        defaultOrderBy: archInfo.defaultOrder,
        maxGroupByDepth: 1,
        activeIdsLimit: session.active_ids_limit,
        hooks: {
            onRecordSaved: this.onRecordSaved.bind(this),
        },
    };
}
}

CylloKanbanController.components = {
    ...KanbanController.components,
    Layout
}
CylloKanbanController.template = "studio.CylloKanbanController"
