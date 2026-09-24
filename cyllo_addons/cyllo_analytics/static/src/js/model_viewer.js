/** @odoo-module **/
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { LinkSelectDialog } from "./LinkSelectDialog";
import { convertToTitleCase } from "./chart_maker"

const { Component, useState, onWillStart, useEffect, onWillUpdateProps } = owl

export class ModelViewer extends Component {
    /** Class for model viewer */
    setup() {
        this.notification = useService("notification")
        this.orm = useService("orm")
        this.dialog = useService("dialog")
        this.limit = 5
        this.state = useState({
            models: this.props.models,
            can_select: true
        })
        // Register a listener for model updates
        useEffect(() => {
            var data = this.state.models.map(model => model.linked_by.join)
            var joinData = this.state.models.map(model => {
                var join = model.linked_by
                join.model_id = model.id
                return join
            })
            this.env.bus.trigger('CY:UPDATE_QUERY', { type: 'join', data })
            this.env.bus.trigger('CY:UPDATE_QUERY', { type: 'joinData', data: joinData })
        }, () => [this.state.models.length])
        onWillUpdateProps((newProps) => {
            this.state.models = newProps.models
        })
    }
    /**
     * Define the domain for model selection.
     * @returns {Array} - The domain for model selection.
     */
    getDomain() {
        var domain = [["transient", "=", false]];
        if (this.state.models && this.state.models.length > 0) {
            var selectedModels = this.state.models.map(m => m.model);
            domain.push(["model", "not in", selectedModels]);
        }
        return domain;
    }
    onRemoveModel(ev) {
        var indexToRemove = this.state.models.findIndex(item => item.id === ev.id)
        if (indexToRemove !== -1) {
            var model = this.state.models[indexToRemove]
            var data = this.props.checkHasLink(model)
            if (data.link) {
                this.constructErrorMessage(data)
            } else {
                if (ev.linked_by.id) {
                    this.env.bus.trigger("CY:UPDATE_UNLINKS", { type: 'tables', id: ev.linked_by.id })
                }
                this.state.models.splice(indexToRemove, 1);
                this.props.setModel(this.state.models)
                this.state.can_select = this.state.models.length < this.limit
            }
        }
    }
    constructErrorMessage(data) {
        var message = `
            Can't delete the model because of the dependencies shown below
            Please remove them first to delete the model
        `
        data.fields.forEach(field => {
            message += '\n'
            message += `${convertToTitleCase(field.type)}: ${field.value}`
        })
        data.models.forEach(model => {
            message += '\n'
            message += `Model: ${model.name}`
        })
        this.showMessage(message, 'danger')
    }
    /**
     * Handle the selection of a model.
     * @param {Object} ev - The selected model's event.
     */
    async onSelect(ev) {
        if (!ev) return
        const data = await this.orm.call('dashboard.sheet', 'get_data', [ev[0].id])
        for (var i in data.fields) {
            data.fields[i].model = data
        }
        // Check if there are already selected models
        if (this.state.models.length) {
            var field_list = []
            var inverse_field_list = []
            var fields = this.state.models.map((model) => model.fields)
            // Find fields related to the selected model
            for (var field of fields) {
                Object.entries(field).forEach(entry => {
                    if (entry[1].relation == data.model && entry[1].type == "many2one") {
                        field_list.push(entry)
                    }
                })
            }
            var models = this.state.models.map((model) => model.model)
            // Find inverse fields related to the selected model
            Object.values(data.fields).forEach((field) => {
                if (models.includes(field.relation) && field.type == "many2one") {
                    var mdl = this.state.models.filter((model) => model.model == field.relation)[0]
                    var field = {
                        name: "id",
                        type: "integer",
                        model: mdl,
                        cur_field: field
                    }
                    inverse_field_list.push(field)
                }
            })
            // Check for the number of possible link fields
            if ((inverse_field_list.length + field_list.length) == 1) {
                if (field_list.length) {
                    var cur_field = field_list[0][1]
                    data.linked_by = {
                        model: data.model,
                        field: cur_field.name,
                        join: `JOIN ${data.table} ON ${data.table}.id = ${cur_field.model.table}.${cur_field.name}`,
                        string: ` Linked by ${cur_field.model.name}.${cur_field.name} on ${data.name}.id`,
                        name: data.name
                    }
                }
                if (inverse_field_list.length) {
                    var cur_field = inverse_field_list[0]
                    data.linked_by = {
                        model: data.model,
                        field: cur_field.cur_field.name,
                        join: `JOIN ${data.table} ON ${cur_field.model.table}.${cur_field.name} = ${data.table}.${cur_field.cur_field.name}`,
                        string: ` Linked by ${cur_field.model.name}.${cur_field.name} on ${data.name}.${cur_field.cur_field.name}`,
                        name: data.name
                    }
                }
                this.state.models.push(data)
                this.props.setModel(this.state.models)
                this.state.can_select = this.state.models.length < this.limit
            }
            else if ((inverse_field_list.length + field_list.length) == 0) {
                this.showMessage('No link field found', 'danger')
                return
            } else {
                this.dialog.add(LinkSelectDialog, {
                    field_list,
                    inverse_field_list,
                    model: data,
                    onConfirm: (new_data) => {
                        this.state.models.push(new_data)
                        this.props.setModel(this.state.models)
                        this.state.can_select = this.state.models.length < this.limit
                    }
                })
            }
        }
        else {
            data.linked_by = {
                model: data.model,
                join: data.table,
                name: data.name
            }
            this.state.models.push(data)
            this.props.setModel(this.state.models)
            this.state.can_select = this.state.models.length < this.limit
        }
    }

    showMessage(message, type) {
        this.notification.add(message, { type })
    }
}
// Define the template for the ModelViewer component
ModelViewer.template = "ModelViewer"
ModelViewer.components = { Dropdown, DropdownItem, Many2XAutocomplete }
