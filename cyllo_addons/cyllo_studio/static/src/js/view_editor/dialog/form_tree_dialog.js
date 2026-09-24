/** @odoo-module **/
import { Component, onWillStart, useState, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import { CylloMultiRecordSelector } from "@cyllo_studio/js/view_editor/dropdown/multi_record_selector/multi_record_selector";
import { CylloRecordSelector } from "@cyllo_studio/js/view_editor/dropdown/record_selector/record_selector";

/**
 * FormTreeDialog
 *
 * Dialog used in Studio for creating One2many or Many2many fields dynamically.
 * Handles related model selection, technical field name generation,
 * and validation before saving.
 */
export class FormTreeDialog extends Component {
    static template = "cyllo_studio.FormTreeDialog";
    static components = {
        Dialog,
        CylloStudioDropdown,
        CylloMultiRecordSelector,
        CylloRecordSelector,
    };
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            label: null,
            technical_name: null,
            selected_value: 'one2many',
            model: false,
            related_model_field: null,
            field_ids: [],
            model_id: null,
            onetomany: false,
        });
        onWillStart(async () => {
            this.related_model_fields = await this.orm.searchRead('ir.model.fields',
                [
                    ['ttype', '=', 'many2one'],
                    ['relation', '=', this.props.resModel]
                ], ['name', 'field_description', 'model_id'])
        })

        useEffect(() => {
            this.state.field_ids = []
            if (this.state.selected_value == 'one2many') {
                this.state.model_id = this.related_model_fields?.find(field => field.id == this.state.related_model_field)?.model_id[0];
            } else {
                this.state.model_id = this.state.model
            }
        }, () => [this.state.selected_value, this.state.model, this.state.related_model_field])
    }

     /**
     * Computes a technical field name from the label.
     * Example: "My Label" → "x_cyllo_my_label"
     */
    computeTechName() {
        const labelValue = this.state.label.trim();
        this.state.technical_name = 'x_cyllo_' + labelValue.toLowerCase().split(' ').join('_');
    }

    generateRandomLetters(length) {
        const letters = 'abcdefghijklmnopqrstuvwxyz';
        let randomLetters = '';
        for (var i = 0; i < length; i++) {
            var randomIndex = Math.floor(Math.random() * letters.length);
            randomLetters += letters[randomIndex];
        }
        return randomLetters;
    }

     /**
     * Returns dropdown options for related model fields,
     * excluding "Config Settings".
     * Also updates state when no related fields are found.
     *
     * @param {Array} array - related model field records
     * @returns {Array} - formatted dropdown options
     */
    getDictFromArrayRelatedModelField(array) {
        if (!array || array.length === 0) {
            this.state.onetomany = true;
            return [{ value: false, label: 'No compatible fields available' }];
        }
        const result = array
            .filter(item => item.model_id[1] !== "Config Settings")
            .map(item => ({
                value: item.id,
                label: `${item.field_description} (${item.model_id[1]})`
            }));
        if (result.length === 0) {
            this.state.onetomany = true;
            return [{ value: false, label: 'No compatible fields available' }];
        }
        this.state.onetomany = false;
        return result;
    }

    handleRelatedModelFieldChange(value) {
        this.state.related_model_field = value;
    }

    get RelatedModelField() {
        return this.state.related_model_field
    }

    /**
     * Validates user input and confirms creation of the field.
     * If fields are missing, shows a warning notification.
     * Ensures unique technical name by appending random letters if needed.
     */
    async onConfirm() {
        if (this.state.field_ids.length == 0) {
            this.env.services.action.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': "All fields are required!",
                    'type': 'warning',
                    'sticky': false,
                }
            })
        } else {
            if (this.state.label && this.state.field_ids) {
                const result = this.orm.search("ir.model.fields", [
                    ['name', '=', this.state.technical_name],
                    ['model', '=', this.props.resModel]
                ])
                if (result) {
                    this.state.technical_name += this.generateRandomLetters(5)
                }
                var properties = {
                    label: this.state.label,
                    technical_name: this.state.technical_name,
                    selected_value: this.state.selected_value,
                    related_model_id: this.state.model || this.state.model_id,
                    related_model_field: this.related_model_fields.find(field => field.id == this.state.related_model_field),
                    field_ids: this.state.field_ids
                }
                if (this.state.selected_value === 'one2many' && !this.state.related_model_field) {
                    this.env.services.effect.add({
                        title: _t("Validation Error"),
                        message: "Unable to save the record.",
                        description: "A One2many field requires a valid Many2one inverse field on the related model.",
                        type: "notification_panel",
                        notificationType: "error",
                    });
                } else if (this.state.model || this.state.related_model_field) {
                    this.props.onConfirm(properties)
                } else {
                    this.env.services.effect.add({
                        title: _t("Validation Error"),
                        message: "Unable to save the record.",
                        description: "Must provide " + (this.state.selected_value === 'many2many' ? "Related Model" : "Related Model Field"),
                        type: "notification_panel",
                        notificationType: "error",
                    });
                }
            } else {
                this.env.services.action.doAction({
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': "All fields are required!",
                        'type': 'warning',
                        'sticky': false,
                    }
                })
            }
        }
    }
    onDiscard() {
        this.props.onDiscard?.();
        this.props.close();
    }

    onClose() {
        this.props.onDiscard?.();
        this.props.close();
    }
}