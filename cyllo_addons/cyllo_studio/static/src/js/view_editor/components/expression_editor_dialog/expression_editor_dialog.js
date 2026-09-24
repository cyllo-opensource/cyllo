/** @odoo-module **/
import {ExpressionEditorDialog} from "@web/core/expression_editor_dialog/expression_editor_dialog";

/**
 * CylloExpressionEditorDialog
 *
 * Extends Odoo's standard ExpressionEditorDialog to add a custom callback
 * for validation when the dialog is discarded.
 */
export class CylloExpressionEditorDialog extends ExpressionEditorDialog {
    static props = {
        ...ExpressionEditorDialog.props,
        setValidation: {type: Function, optional: true, default: () => {}}
    }
    onDiscard(){
        this.props.setValidation()
        this.props.close();
    }
}