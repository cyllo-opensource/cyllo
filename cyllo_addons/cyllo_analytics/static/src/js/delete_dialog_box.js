/** @odoo-module **/
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";


export class DeleteDialog extends Component {
    // This is a class for delete dialog box that is used in dashboard view to delete the dashboard
    setup(){
        // Initialize necessary services and references
        this.orm = useService("orm")
        this.action = useService("action")
    }
    /**
     * Handle the cancel action.
     */
    async _cancel() {
         this.props.close();
    }
    /**
     * Handle the confirm action for deleting the dashboard.
     */
    async _confirm() {
        var model = this.props.model || 'dashboard.config'
        await this.orm.unlink(model, [this.props.id]);
        this.props.removeManually && this.props.removeManually()
        // Perform an action to navigate to the Dashboard sheet view
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: this.props.model || 'dashboard.sheet',
            name: 'Dashboard sheet',
            view_mode: 'tile',
            views:[[false,"tile"]],
        });
        // Close the dialog box
        await this.props.close();
    }
}
// Define the template for the DeleteDialog component
DeleteDialog.template = "cyllo_analytics.DeleteDialog"
// Define the components used in the DeleteDialog
DeleteDialog.components = { Dialog }
// Define default properties for the DeleteDialog component
DeleteDialog.defaultProps = {
    confirmLabel: _t("Confirm"),
    cancelLabel: _t("Cancel"),
    confirmClass: "btn-primary",
    title: _t("Delete"),
    body: _t("Are you sure you want to delete this dashboard ?"),
    onConfirm: () => {}
};