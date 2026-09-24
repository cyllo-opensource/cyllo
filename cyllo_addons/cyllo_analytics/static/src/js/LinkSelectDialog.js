/** @odoo-module **/
import { Dialog } from "@web/core/dialog/dialog";
const { Component, useState } = owl;

export class LinkSelectDialog extends Component {
    /** Class for selecting linked fields in a dialog */

    setup() {
        this.state = useState({
            index: false,
            field: false,
        })
    }
    /**
     * Set the selected index and field.
     * @param {number} index - The index of the selected field.
     * @param {Object} field - The selected field.
     */

    setSelected(index, field){
        this.state.index = index;
        this.state.field = field;
    }
    /**
     * Get the list of fields.
     * @returns {Array} - The list of fields.
     */
    get fields(){
        var fields = []
        var model = this.props.model
        for(var field of this.props.field_list){
            field = field[1]
            var data = {
                ...model,
                linked_by: {
                    model: model.model,
                    field: field.name,
                    join: `JOIN ${model.table} ON ${model.table}.id = ${field.model.table}.${field.name}`,
                    string: ` Linked by ${field.model.name}.${field.name} on ${model.name}.id`,
                    name: model.name
                }
            }
            fields.push(data)
        }
        for(var field of this.props.inverse_field_list){
            var data = {
                ...model,
                linked_by: {
                    model: model.model,
                    field: field.name,
                    join: `JOIN ${model.table} ON ${field.model.table}.${field.name} = ${field.cur_field.name}`,
                    string: ` Linked by ${field.model.name}.${field.name} on ${model.name}.${field.cur_field.name}`,
                    name: model.name
                }
            }
            fields.push(data)
        }
        return fields
    }
    /**
     * Confirm the selected field and close the dialog.
     */
    confirm() {
        var field = this.state.field
        if (field) {
            this.props.onConfirm(field)
            this.props.close()
        }
    }
}
// Define the template for the LinkSelectDialog component
LinkSelectDialog.template = "LinkSelectDialog"
LinkSelectDialog.components = { Dialog }