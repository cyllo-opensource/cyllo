/** @odoo-module **/

/**
 *
 * Patch for SelectCreateDialog
 *
 * This patch customizes the view properties of the SelectCreateDialog
 * component. Depending on the viewport size, it switches between "kanban"
 * and "n_list" views and adjusts properties like `allowSelectors` and
 * `forceGlobalClick`. It also ensures dynamic filters, domain, context,
 * and other essential props are properly passed to the view.
 */
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { patch } from "@web/core/utils/patch";

patch(SelectCreateDialog.prototype, {
    /**
     * Computes the view properties dynamically based on viewport and dialog props.
     *
     * @returns {Object} props - The properties to initialize the view
     */
    get viewProps() {
        const type = this.env.isSmall ? "kanban" : "n_list";
        const props = {
            loadIrFilters: true,
            ...this.baseViewProps,
            context: this.props.context,
            domain: this.props.domain,
            dynamicFilters: this.props.dynamicFilters,
            resModel: this.props.resModel,
            searchViewId: this.props.searchViewId,
            type,
        };
        if (type === "n_list") {
            props.allowSelectors = this.props.multiSelect;
        } else if (type === "kanban") {
            props.forceGlobalClick = true;
        }
        return props;
    }
})
