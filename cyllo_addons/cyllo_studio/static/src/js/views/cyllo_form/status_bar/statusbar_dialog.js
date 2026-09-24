/** @odoo-module **/

/**
 * StatusBarDialog
 *
 * Component for adding or editing a Status Bar in Odoo Studio.
 * Allows selecting an existing field or creating a new field with selection values,
 * setting visibility rules, and configuring default values.
 *
 * Props:
 *   - fields: Object containing available fields for status bar selection.
 *   - path: XPath of the status bar container.
 *   - viewId: Current view ID.
 *   - model: Model name of the form.
 *   - header: Status bar header label.
 *   - activeFields: Object indicating currently active fields.
 *   - close: Function to close the dialog.
 *
 * State:
 *   - field: "existing" or "new", indicating the type of field.
 *   - selectedField: Name of the currently selected existing field.
 *   - values: Array of selection values for the field.
 *   - selectionValues: Array of new selection values for custom fields.
 *   - newFieldLabel: Label for the new field.
 *   - newFieldTechName: Technical name for the new field.
 *   - SelectedOptions: Currently selected values.
 *   - existingFieldTech: Technical name of the selected existing field.
 */
import { Component, useState, useEffect, useRef, onMounted } from "@odoo/owl";
import { useService, useOwnedDialogs } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { ExpressionEditorDialog } from "@web/core/expression_editor_dialog/expression_editor_dialog";
import { TagsList } from "@web/core/tags_list/tags_list";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import { MultiSelectDropDown } from "@cyllo_studio/js/view_editor/dropdown/multi_select_dropdown/multi_select_dropdown";
import { SelectionFieldValue } from "@cyllo_studio/js/view_editor/components/selection_field_widget_values/selection_field_value_widget";

export class StatusBarDialog extends Component {
    static template = "cyllo_studio.StatusBarDialog";
    static components = {
        Dialog,
        MultiRecordSelector,
        TagsList,
        Dropdown,
        DropdownItem,
        CylloStudioDropdown,
        MultiSelectDropDown,
        SelectionFieldValue,
    };
    setup() {
        this.rpc = useService('rpc');
        this.action = useService('action');
        this.dialog = useService('dialog');
        this.addDialog = useOwnedDialogs();
        this.state = useState({
            field: "existing",
            selectedField: '',
            values: [],
            isManualField: '',
            SelectedOptions: [],
            newFieldLabel: '',
            selectionValues: [''],
            existingFieldTech: "",
        })
        this.StatusBarValues = useState({
            clickable: false,
            foldField: '',
            statusbarVisible: '',
            group_ids: [],
            invisible: 'False',
            defaultValue: ' ',
        })
        this.selectionValuesRef = useRef('cy-SelectionValues')
        this.existingSelectionRef = useRef('cy-existingSelection')

        useEffect(() => {
            this.state.SelectedOptions = []

            if (this.state.selectedField) {
                const field = this.props.fields[this.state.selectedField]
                this.state.values = [...field.selection] || []
                const manual = field?.manual

            }
        }, () => [this.state.selectedField])

        useEffect(() => {
            const self = this;
            const container = this.selectionValuesRef.el;
            if (!container) return;
            const existingSortable = Sortable.get(container);
            if (existingSortable) existingSortable.destroy();

            Sortable.create(container, {
                animation: 150,
                ghostClass: 'sortable-ghost',
                handle: '.handle-drag',

                onEnd: function (evt) {
                    let selectionValuesArr = self.state.selectionValues;
                    const currentIndex = evt.oldIndex;
                    const targetIndex = evt.newIndex;
                    const currentValue = selectionValuesArr[currentIndex];
                    const updated = [...selectionValuesArr];
                    updated.splice(currentIndex, 1);
                    updated.splice(targetIndex, 0, currentValue);
                    self.state.selectionValues = updated;
                },
            });
        }, () => [this.state.selectionValues]);
    }
    /**
     * Converts an array of selection field objects to a dropdown-friendly format.
     *
     * @param {Array} array - Array of objects with `name` and `string`.
     * @returns {Array} - Array of objects with `value` and `label` for dropdown.
     */
    ExistingField(array) {
        const result = array.map(item => ({ value: item.name, label: item.string }));
        return result
    }

    /**
     * Handles selection of an existing field.
     *
     * @param {String} value - The technical name of the selected field.
     */
    handleExistingFieldChange(value) {
        this.state.selectedField = value;
    }

    /**
     * Opens the ExpressionEditorDialog to configure the invisible domain of the status bar.
     */
    invisibleDomain() {
        const filteredObj = {};
        for (const key in this.props.fields) {
            if (this.props.activeFields[key]) {
                filteredObj[key] = this.props.fields[key];
            }
        }
        this.addDialog(ExpressionEditorDialog, {
            resModel: this.props.model,
            fields: filteredObj,
            expression: this.StatusBarValues.invisible,
            onConfirm: (domain) => this.StatusBarValues.invisible = domain,
        });
    }
    clickOptionVisible() {
        if (!this.state.selectionValues.length || this.state.selectionValues[0] === '') {
            this.state.isOptionEmpty = true
        }
    }

    get multiSelectDropDown() {
        const values = this.state.field == 'existing' ? this.state.values : this.state.selectionValues
        let allValues = values.reduce((acc, item) => {
            if (this.state.field == 'existing') {
                acc[item[0]] = item[1];
            } else {
                acc[item] = item;
            }
            return acc;
        }, {});
        return {
            selectedValues: [...new Set(this.state.SelectedOptions)],
            allValues,
            onUpdate: (value) => {
                this.state.SelectedOptions = value
                this.StatusBarValues.statusbarVisible = value.join(', ')
            },
        }
    }

    /**
     * Handles new field label input and updates technical field name automatically.
     *
     * @param {Event} ev - Input event containing the new field label.
     */
    onInputLabel(ev) {
        this.state.newFieldLabel = ev.target.value
        this.onInputTechName(ev)
    }
    /**
   * Converts a string to a valid technical name format.
   *
   * @param {String} inputValue - Original field label.
   * @returns {String} - Lowercase, sanitized technical name.
   */
    onInputTechName(ev) {
        let inputValue = ev.target.value;
        this.state.newFieldTechName = this.processTechName(inputValue);
    }
    /**
    * Converts a string to a valid technical name format.
    *
    * @param {String} inputValue - Original field label.
    * @returns {String} - Lowercase, sanitized technical name.
    */
    processTechName(inputValue) {
        inputValue = inputValue.replace(/ /g, "_");
        inputValue = inputValue.replace(/[^a-zA-Z0-9_]/g, "");
        return inputValue.toLowerCase()
    }
    /**
     * Adds a new selection value to the current field.
     */
    addSelectionValue() {
        if (this.state.field === 'existing') {
            return this.state.values = [...this.state.values, ['', '']]
        }
        return this.state.selectionValues = [...this.state.selectionValues, '']
    }
    /**
    * Updates a selection value at the specified index.
    *
    * @param {Number} index - Index of the selection value to update.
    * @param {String} value - New value to replace the existing one.
    */
    changeSelectionValue(index, value) {

        this.state.isOptionEmpty = false
        let optionsIndex = -1
        if (this.state.field === "existing") {
            optionsIndex = this.state.SelectedOptions.indexOf(this.state.values[index][0])
        } else {
            optionsIndex = this.state.SelectedOptions.indexOf(this.state.selectionValues[index])
        }
        if (optionsIndex !== -1) {
            this.state.SelectedOptions[optionsIndex] = value
        }
        if (this.state.field === "existing") {
            this.state.values[index][1] = value
            const field = this.props.fields[this.state.existingFieldTech]

            if (!field.selection.some((item) => item[0] === this.state.values[index][0])) {
                this.state.values[index][0] = value.toLowerCase()
                //                   this.state.values[index] = [value.toLowerCase(), value];
            }
        } else {
            this.state.selectionValues[index] = value
            let lowerCaseArray = []
            lowerCaseArray = this.state.selectionValues.map(element => element.toLowerCase());
            let setValues = new Set(lowerCaseArray);
            const isSameElement = setValues.size != lowerCaseArray.length
            const isEmpty = lowerCaseArray.some(str => str === null || str.match(/^ *$/) !== null);
            if (isSameElement || isEmpty) {
                this.state.isDefaultOk = "False"

            }
            else {
                this.state.isDefaultOk = "True"
            }

        }
    }
    /**
     * Deletes a selection value at the specified index.
     *
     * @param {Number} index - Index of the selection value to delete.
     */
    async deleteSelectionValue(index) {
        const optionsIndex = this.state.SelectedOptions.indexOf(
            this.state.field === "existing" ? this.state.values[index][0] : this.state.selectionValues[index])
        if (this.state.field === "existing") {
            const field = this.props.fields[this.state.existingFieldTech]
            if (field.selection.some((item) => item[0] === this.state.values[index][0])) {
                const confirm = await new Promise((resolve) => {
                    this.dialog.add(ConfirmationDialog, {
                        title: _t("Are you sure ?"),
                        body: _t("The value will be removed from all records"),
                        confirmLabel: _t("Yes"),
                        confirm: resolve.bind(null, true),
                    }, {
                        onClose: resolve.bind(null, false),
                    });
                })
                if (!confirm) {
                    return false
                }
            }
            this.state.values.splice(index, 1)
        } else {
            const matchKey = this.state.selectionValues?.[index]
            this.state.selectionValues.splice(index, 1)
            if (matchKey == this.StatusBarValues.defaultValue) {
                this.StatusBarValues.defaultValue = ''
            }
        }
        if (optionsIndex !== -1) {
            this.state.SelectedOptions.splice(optionsIndex, 1)
        }
    }

    get existingFields() {
        const selectionFields = Object.entries(this.props.fields)
            .filter(([key, field]) => field.type === "selection" && field.store)
            .map(([key, field]) => ({ name: field.name, string: field.string }));
        return selectionFields
    }

    DefaultValueExistingField(array) {
        const result = array.map(item => ({ value: item[0], label: item[1] }));
        return result
    }

    handleDefaultValueExisting(value) {
        this.StatusBarValues.defaultValue = value
        this.StatusBarValues.defaultValue = value.toLowerCase();
    }
    get defaultExistingField() {
        return this.state.existingFieldTech
    }
    get DefaultValueNewField() {
        const arr = []
        for (let value in this.state.selectionValues) {
            const obj = { value: this.state.selectionValues[value], label: this.state.selectionValues[value] }
            arr.push(obj)
        }
        return arr
    }
    handleDefaultValueNewField(value) {
        this.StatusBarValues.defaultValue = value.toLowerCase();
    }

    /**
     * Confirms the dialog, creates or updates the status bar via RPC,
     * updates undo/redo stacks, and reloads the form view.
     */
    async onConfirm() {

        if (!this.StatusBarValues.defaultValue || this.StatusBarValues.defaultValue.trim() === '') {
            this.StatusBarValues.defaultValue = false;
        }
        // Prepare the initial values object
        let values = {
            path: this.props.path,
            view_id: this.props.viewId,
            is_new: false,
            model: this.props.model,
            view_type: 'form',
            header: this.props.header,
            field: this.state.selectedField, // Default field
        };

        let kwargs = { ...this.StatusBarValues };

        // Handle the case when a new field is being added
        if (this.state.field === 'new') {
            const { newFieldLabel, newFieldTechName, selectionValues } = this.state;

            if (!newFieldLabel || !newFieldTechName) {
                return this.actionWarning('Both fields are required');
            }

            // Update values for the new field
            values = {
                ...values,
                field: `x_cy_${newFieldTechName}`, // Construct field name
                label: newFieldLabel, // Use label separately
                is_new: true,
            };

            kwargs.values = selectionValues;
        }

        // Block the UI to prevent further actions while processing
        this.env.services.ui.block();

        try {
            // Make the RPC call to add the status bar
            const response = await this.rpc("cyllo_studio/add/statusbar", { args: { ...values }, kwargs });

            if (response) {
                const cleanedResponse = response.replace(/\s+/g, ' ').trim();
                const storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];

                // Append the cleaned response to the undo stack
                storedArray.push(cleanedResponse);
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([])); // Reset redo stack
            }
        } catch (error) {
            console.error("Error while adding status bar:", error);
            // Optionally handle the error (e.g., show a user-friendly message)
        } finally {
            // Unblock the UI after processing
            this.env.services.ui.unblock();
        }

        // Perform the action and close the dialog
        this.action.doAction('studio_reload');
        this.props.close();
    }
    /**
        * Shows a warning notification.
        *
        * @param {String} message - Warning message to display.
        */
    actionWarning(message) {
        return this.action.doAction({
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'warning',
                'sticky': false,
            }
        })
    }


    onDiscard() {
        this.props.close();
    }

}