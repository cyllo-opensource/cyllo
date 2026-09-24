/** @odoo-module **/

/**
 * Studio patch for the shared CogMenuList component (cyllo_base).
 *
 * The Reports kanban view (ir.actions.report) has no dedicated create flow —
 * its "+ New" (rendered by CogMenuList, shared by every list/kanban view
 * app-wide) must open the report creation wizard instead of the generic
 * props.create() behavior other views rely on.
 */
import { patch } from "@web/core/utils/patch";
import { useOwnedDialogs } from "@web/core/utils/hooks";
import { CogMenuList } from "@cyllo_base/js/cog_menu_form";
import { ReportCreationDialog } from "@cyllo_studio/js/control_panel/report_creation_dialog";

patch(CogMenuList.prototype, {
    setup() {
        super.setup();
        this.addDialog = useOwnedDialogs();
    },
    handleReportCreate() {
        if (this.props.model?.root?.resModel === "ir.actions.report") {
            this.addDialog(ReportCreationDialog, {});
            return;
        }
        this.props.create?.();
    },
});
