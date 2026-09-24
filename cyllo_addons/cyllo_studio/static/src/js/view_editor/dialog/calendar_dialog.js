/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Select } from "@web/core/tree_editor/tree_editor_components";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

/**
 * CalendarDialog
 *
 * Dialog component for creating or configuring a calendar view in Studio.
 * Allows the user to select start and stop date fields from the model's fields.
 */

export class CalendarDialog extends Component {
    static template = "cyllo_studio.CalendarDialog";
    static components = {
        Dialog,
        Select,
        CylloStudioDropdown,
        Dropdown,
        DropdownItem
    };
    setup() {
        this.action = useService('action');
        this.rpc = useService('rpc');
        this.orm = useService('orm');

        this.state = useState({
            startDateField: {
                key: false,
                value: "Select an option",
            },
            stopDateField: {
                key: false,
                value: "Select an option",
            },
            fields: {},
            isLoading: true,
        });

        onWillStart(() => {
            this.loadFields();
        });
    }

    /**
     * Load fields from the model if not available in props
     */
    async loadFields() {
        try {
            // Check if props.fields is empty or undefined
            if (!this.props.fields || Object.keys(this.props.fields).length === 0) {

                // Fetch fields using fields_get
                const fields = await this.rpc('/web/dataset/call_kw', {
                    model: this.props.details[0].resModel,
                    method: 'fields_get',
                    args: [],
                    kwargs: {
                        attributes: ['string', 'type', 'required', 'readonly']
                    }
                });

                this.state.fields = fields;
            } else {
                this.state.fields = this.props.fields;
            }
        } catch (error) {
            console.error('Error loading fields:', error);
            this.action.doAction({
                type: 'ir.actions.client',
                tag: 'display_notification',
                params: {
                    message: 'Error loading model fields. Please try again.',
                    type: 'danger',
                    sticky: false,
                }
            });
        } finally {
            this.state.isLoading = false;
        }
    }

    /**
     * Computes available options for start and stop date fields based on the model's fields.
     * If no date/datetime fields exist, displays a warning notification.
     *
     * @returns {Array} Array of [field_name, field_label] for date/datetime fields
     */
    get getOptions() {
        if (this.state.isLoading) {
            return [];
        }

        const dateFields = [];
        const fieldsToUse = this.state.fields;

        for (const [name, field] of Object.entries(fieldsToUse)) {
            if (['date', 'datetime'].includes(field.type)) {
                dateFields.push([name, field.string]);
            }
        }

        if (dateFields.length == 0) {
            this.action.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Unable to add calendar view. This action is not permitted',
                    'type': 'warning',
                    'sticky': false,
                }
            });
            return [];
        }

        return [...dateFields];
    }
    updateDateField(type, value) {
        const fieldMap = {
            start: "startDateField",
            stop: "stopDateField"
        };
        if (fieldMap[type]) {
            this.state[fieldMap[type]].key = value[0];
            this.state[fieldMap[type]].value = value[1];
        }
    }

    /**
     * Confirms the selected start and stop date fields, updates the backend,
     * closes the dialog, reloads Studio, and refreshes the page.
     */
    async onConfirm() {
        if (!this.state.startDateField.key || !this.state.stopDateField.key) {
            this.action.doAction({
                type: "ir.actions.client",
                tag: "display_notification",
                params: {
                    title: "Validation Error",
                    message: "Please select both start date and stop date fields.",
                    type: "warning",
                    sticky: false,
                },
            });
            return;
        }
            await this.rpc("/cyllo_studio/view/active_views", {
            args: [{
                'activeView': this.props.details[0].activeView,
                'actionId': this.props.details[0].actionId,
                'actionType': this.props.details[0].actionType,
                'viewType': this.props.details[0].viewType,
                'resModel': this.props.details[0].resModel,
                'name': this.props.details[0].name,
                'startDateField': this.state.startDateField.key,
                'stopDateField': this.state.stopDateField.key,
            }],
        });
         this.props.close();
         this.action.doAction('studio_reload')
         window.location.reload()
    }
     /**
     * Discards the dialog without saving any changes.
     */
    onDiscard() {
        this.props.close();
    }
}
