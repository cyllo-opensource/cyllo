/** @odoo-module **/

/**
 * CylloKanbanRenderer
 *
 * Extends Odoo's KanbanRenderer to provide enhanced functionality for
 * Cyllo Studio's Kanban view editor.
 *
 * Features:
 * 1. Ribbon & Field Integration:
 *    - Captures ribbon elements and triggers bus events to share Kanban
 *      details such as fields, progress bars, and ribbons.
 *    - Supports dynamic handling of ribbons for editing or customization.
 *
 * 2. Kanban Preview:
 *    - Opens a Kanban preview dialog (CylloSelectCreateDialog) when
 *      triggered via the 'KanbanPreview' bus event.
 *    - Preview dialog provides read-only view with no creation allowed
 *      and supports automatic soft reload on close.
 *
 * 3. Lifecycle Management:
 *    - Uses `onMounted` to initialize bus listeners and trigger initial
 *      Kanban detail events.
 *    - Uses `onWillUnmount` to clean up listeners and prevent memory leaks.
 *
 * 4. Group & Record Handling:
 *    - Overrides `getGroupsOrRecords` to safely return either the first
 *      valid group with records or the first Kanban record when ungrouped.
 *
 * 5. Component Integration:
 *    - Uses CylloKanbanRecord for rendering individual Kanban cards.
 *    - Includes KanbanComponents for additional nested UI elements.
 *
 * 6. Template:
 *    - The component template is defined as "cyllo_studio.CylloKanbanRenderer".
 *
 * Purpose:
 * This renderer provides Cyllo Studio users with a fully interactive
 * Kanban editing experience, including ribbon management, previews,
 * and custom card rendering, integrated seamlessly with Odoo's
 * backend services and bus events.
 */
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { KANBAN_MENU_ATTRIBUTE } from "@web/views/kanban/kanban_arch_parser";
import { CylloKanbanRecord } from "./cyllo_kanban_record";
import { KanbanComponents } from "./kanban_components";
import { CylloSelectCreateDialog } from "@cyllo_studio/js/preview/preview_dialog";


import { _t } from "@web/core/l10n/translation";
export class CylloKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        var self = this
        const openKanbanPreview = () => {
            this.dialog.add(CylloSelectCreateDialog, {
                view: 'n_kanban',
                title: _t('Kanban Preview'),
                viewId: this.env.config.viewId,
                context: this.props.list.context,
                domain: this.props.list.domain,
                resModel: this.props.list.resModel,
                searchViewId: this.env.searchModel.searchViewId,
                multiSelect: false,
                noCreate: true,
            }, {
                onClose: () => this.env.services.action.doAction("soft_reload")
            });
        }

        onMounted(() => {
            const ribbonElement = document.querySelectorAll('div.ribbon[cy-xpath]');  //[data-ribbon="1"]
            this.env.bus.trigger("KANBAN_DETAILS", {
                viewType: this.env.config.viewType,
                model: this.props.list._config.resModel,
                viewId: this.env.config.viewId,
                allFields: this.props.list.model.config.fields,
                isMenu: KANBAN_MENU_ATTRIBUTE in this.props.archInfo.templateDocs,
                progressAttributes: this.props.archInfo.progressAttributes || {},
                ribbonElement: ribbonElement,
                attributes: {
                    create: this.props.archInfo.activeActions.create,
                    quickCreate: this.props.archInfo.activeActions.quickCreate,
                    defaultGroupBy: this.props.archInfo.defaultGroupBy,
                    recordsDraggable: this.props.archInfo.recordsDraggable,
                    groupsDraggable: this.props.archInfo.groupsDraggable,
                },
            });
            this.env.bus.addEventListener('KanbanPreview', openKanbanPreview)
        });

        onWillUnmount(() => {
            this.env.bus.removeEventListener('KanbanPreview', openKanbanPreview)
        })
    }
    getGroupsOrRecords() {
        const { list } = this.props;
        if (list.isGrouped) {
            const validGroup = [...list.groups].map((group, i) => ({
                group,
            })).find(item => item.group.records && item.group.records.length > 0);
            if (validGroup) {
                return validGroup;
            }
        } else {
            return list.records.map((record) => ({ record, key: record.id }))[0];
        }
    }

}

CylloKanbanRenderer.components = {
    ...KanbanRenderer.components,
    CylloKanbanRecord,
    KanbanComponents,
}
CylloKanbanRenderer.template = "cyllo_studio.CylloKanbanRenderer"
