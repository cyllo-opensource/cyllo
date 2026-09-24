/** @odoo-module */
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class AnnotateDialog extends Component {
/**
 * AnnotateDialog component for handling annotation dialogs.
 */
    setup() {
        this.state = useState({
            message: this.props.message
        })
    }


    async onConfirm() {
    /**
     * Handle the onClick event for the Save button in the dialog.
     */
        if(this.state.message && this.state.message !== this.props.message){
            this.props.onConfirm(this.state.message)
        }
        this.props.close()
    }
}
AnnotateDialog.template = "AnnotateDialog";
AnnotateDialog.components = { Dialog };
AnnotateDialog.props = {
    close: Function,
    title: {type: String,optional: true},
    message: {type: String,optional: true},
    onConfirm: { type: Function, optional: true },
};
AnnotateDialog.defaultProps = {
    title: _t("Annotate"),
};
