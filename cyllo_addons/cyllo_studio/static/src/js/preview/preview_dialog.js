/** @odoo-module **/
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
const { useState, onMounted } = owl;

/**
 * CylloSelectCreateDialog extends the standard Odoo SelectCreateDialog
 * to support Cyllo Studio functionality.
 *
 * Features:
 *  - Automatically hides the control panel in modal dialogs.
 *  - Detects folded columns and allows unfolding them programmatically.
 *  - Passes custom props to the view, including kanban preview mode.
 */

//@Todo:- Refactor it, already patched 'js/select_create_dialog.js'
export class CylloSelectCreateDialog extends SelectCreateDialog{
    setup(){
        super.setup()
        this.state = useState({
            ...this.state,
            hasFolded: false,
        })
        onMounted(()=> {
            const modalBody = document.querySelector("main.modal-body")
            const controlPanel = modalBody.querySelector(".o_control_panel")
            controlPanel?.classList.add('d-none')
            this.foldGroup = modalBody.querySelectorAll(".o_column_folded")
            this.state.hasFolded = !!this.foldGroup.length
        })
    }

    /** Programmatically unfold all folded columns in the dialog. */
    handleUnfold(){
        this.foldGroup.forEach(node => {
            node.click();
        });
        this.state.hasFolded = false
    }

    get viewProps() {
        const type = this.props.view;
        const props = {
            loadIrFilters: true,
            ...this.baseViewProps,
            context: {
                ...this.props.context,
                kanban_preview_mode: true,
            },
            domain: this.props.domain,
            dynamicFilters: this.props.dynamicFilters,
            resModel: this.props.resModel,
            searchViewId: this.props.searchViewId,
            viewId: this.props.viewId,
            type,
        };
        if (type === "n_list") {
            props.allowSelectors = this.props.multiSelect;
        }
        return props;
    }

}

CylloSelectCreateDialog.template = 'cyllo_studio.SelectCreateDialog'

CylloSelectCreateDialog.props = {
    ...SelectCreateDialog.props,
    viewId: {type: Number, optional: true},
    view: String,
}

CylloSelectCreateDialog.defaultProps = {
    ...SelectCreateDialog.defaultProps,
    close: ()=> this.action.doAction('studio_reload'),
}