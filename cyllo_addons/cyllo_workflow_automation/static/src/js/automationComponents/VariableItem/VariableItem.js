/** @odoo-module */
import { Component } from "@odoo/owl";

export class VariableItem extends Component {
    /**
     * Component representing a single variable item.
     * Displays the variable's name and type, with optional edit and delete actions.
     */
    onDetailsClick() {
        this.props.selectVariable()
    }

    onEditClick() {
        this.props.edit();
    }

    onDeleteClick() {
        this.props.delete();
    }
}

VariableItem.template = 'VariableItem';
VariableItem.props = {
    name: String,
    type: String,
    showEdit: { type: Boolean, optional: true },
    showDelete: { type: Boolean, optional: true },
    edit: { type: Function, optional: true },
    delete: { type: Function, optional: true },
    selectVariable: { type: Function },
};
