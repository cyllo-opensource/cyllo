/** @odoo-module **/

/**
 * ProgressBarDialog Component
 * -----------------------------------------
 * This dialog allows configuring and managing progress bars
 * within the Studio Kanban view. It supports:
 *   - Selecting fields and sum fields
 *   - Assigning colors to selection values
 *   - Adding, deleting, and validating mappings
 *   - Persisting configuration via RPC (create/update)
 *   - Displaying notifications and handling validation
 *
 * Dependencies:
 *   - Odoo OWL Component system
 *   - CylloStudioDropdown (custom dropdown component)
 *   - Odoo core services (rpc, action, effect/notification)
 */
import { Dialog } from "@web/core/dialog/dialog";
const { Component, useState, onMounted, onWillUnmount } = owl;
import {useService} from "@web/core/utils/hooks";
import { sortBy } from "@web/core/utils/arrays";
import {_t} from "@web/core/l10n/translation";
import { shallowEqual } from "@web/core/utils/objects";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";

export class ProgressBarDialog extends Component {
    static template = 'cyllo_studio.ProgressBarDialog'
    static components = {
        Dialog,
        CylloStudioDropdown
    }
    static props = [
        'fields',
        'viewDetails',
        'progressAttributes',
        'close',
    ]

    setup(){
        this.action = useService('action')
        this.rpc = useService('rpc')
        this.notification = useService('effect')

        this.state = useState({
            selection : {},
            colors: {
                primary: 'bg-primary',
                secondary: 'bg-secondary',
                success: 'bg-success',
                info: 'bg-info',
                warning: 'bg-warning',
                danger: 'bg-danger',
            },
            dropdown: false,
        })
        this.properties = useState({
            field: '',
            sum_field: '',
            help: '',
            colors: [],
        })

        onMounted(() => {
            document.addEventListener('click', this.handleOutsideClick);
            if (this.props.progressAttributes) {
                const field = this.props.progressAttributes.fieldName

                const fieldDef = this.props.fields?.[field];

                this.properties.field = field;
                this.properties.sum_field = this.props.progressAttributes.sumField?.name;
                this.properties.help = this.props.progressAttributes.help;
                this.properties.colors = this.props.progressAttributes.colors ? Object.entries(this.props.progressAttributes.colors) : [];

                if (fieldDef?.selection) {
                    this.state.selection = fieldDef.selection.reduce((acc, [key, value]) => {
                        acc[key] = value;
                        return acc;
                    }, {});
                } else {
                    this.state.selection = {};
                }
            }
        })
        onWillUnmount(() => {
            document.removeEventListener('click', this.handleOutsideClick);
        });
    }

    handleOutsideClick = ({target}) =>{
        if(!target.classList.contains('cy-studio-click')){
            this.state.dropdown = false
        }
    }
    /**
     * Get fields by type to populate dropdowns.
     * Supports 'monetary' with empty option prepended.
     */
    getField(types){
        let fields = [];
        for (const [fieldName, field] of Object.entries(this.props.fields)) {
            if (types === field.type) {
                fields.push({ value:fieldName, label:field.string + ` (${fieldName})`});
            }
        }
        if(types === 'monetary'){
             if (fields.length > 0) {
            fields = [{value:'', string:''},...fields]

          }
        }
        return sortBy(fields);
    }

    /**
     * Select a field or sum field for the progress bar.
     * Resets colors and updates selection options if a main field is chosen.
     *
     * @param {String} field - The selected field name.
     * @param {Boolean} isSumField - Whether the field is a sum field.
     */
    handleFieldSelect(field, isSumField=false){
        if(isSumField){
            this.properties.sum_field = field
        } else{
            this.properties.field = field
            this.properties.colors = []
            this.state.selection = this.props.fields[field].selection.reduce((acc, [key, value]) => {
              acc[key] = value;
              return acc;
            }, {});
        }
    }

     /**
     * Get remaining selectable values for color assignment.
     * Excludes values already used in `properties.colors`.
     *
     * @param {String} value - Current value being edited (to allow replacement).
     * @returns {Array} - Available selection options.
     */
    getSelectionValues(value){
        let selectedValues = this.properties.colors.filter(val => val[0] !== value).map(val => val[0]);
        let selection = []
        Object.entries(this.state.selection).forEach(([key, value]) => {
            if(!selectedValues.includes(key)){
                selection.push({ value:key, label:value});
            }
        })
        return selection
    }

    /**
     * Update the selection value of a given color mapping.
     *
     * @param {String} value - New selection key.
     * @param {Number} index - Index in the colors array to update.
     */
    handleSelectionValue(value, index){
        this.properties.colors[index][0] = value
    }

    /**
     * Compute whether additional values can be added.
     * Returns:
     *   - "none": if no selections exist
     *   - "hide": if all values/colors are already mapped
     *   - "show": if more mappings can still be added
     */
    get hasValue(){
        const colorsCount = this.properties.colors.length;
        const selectionCount = Object.keys(this.state.selection).length;
        const colorOptionsCount = Object.keys(this.state.colors).length;

        if (selectionCount === 0) {
            return "none";   // clearer than "hee"
        }
        if (colorsCount === selectionCount || colorsCount === colorOptionsCount) {
            return "hide";
        }
        return "show";
    }

     /**
     * Add a new value-color mapping.
     * Picks the first available selection value and color not yet used.
     */
    handleAddValue(){
        const selectedValues = this.properties.colors.map(val => val[0]);
        const selectedColors = this.properties.colors.map(val => val[1]);

        const allValues = Object.keys(this.state.selection)
        const allColors = Object.keys(this.state.colors)

        const filteredValues = allValues.filter(val => !selectedValues.includes(val));
        const filteredColors = allColors.filter(color => !selectedColors.includes(color));

        this.properties.colors.push([filteredValues[0], filteredColors[0]])
    }

    handleDeleteValue(index){
        this.properties.colors.splice(index, 1)
    }

    getColors(color){
        let selectedColors = this.properties.colors.filter(val => val[1] !== color).map(val => val[1]);
        let selection = []
        Object.entries(this.state.colors).forEach(([key, value]) => {
            if(!selectedColors.includes(key)){
                selection.push(key);
            }
        })
        return selection
    }

    /**
     * Save the progress bar configuration.
     * Handles:
     *   - Validation (must have a field selected)
     *   - Updating existing configuration (diff detection)
     *   - Adding new configuration
     *   - RPC persistence with UI blocking/unblocking
     *   - Notifications for success or validation errors
     */
    async handelSave(){
        if(!this.properties.field){
            this.notification.add({
                title: _t("Validation Error"),
                message: "Unable to create the Progressbar.",
                description: "Please select a field",
                type: "notification_panel",
                notificationType: "warning",
            });
            return;
        }
        let properties = { ...this.properties }
        const url = (this.props.progressAttributes && this.props.progressAttributes.fieldName) ? 'update' : 'add'
        if(url === 'update'){
            properties.colors = Object.fromEntries(properties.colors)
            const sumField = this.props.progressAttributes.sumField?.name || ''

            if(this.props.progressAttributes.fieldName === properties.field){
                delete properties.field
            }
            if(sumField ===  properties.sum_field){
                delete properties.sum_field
            }

            if(this.props.progressAttributes.help ===  properties.help){
                delete properties.help
            }

            if(shallowEqual(this.props.progressAttributes.colors, properties.colors)){
                delete properties.colors
            }

            if(Object.keys(properties).length === 0){
                this.props.close()
                return;
            }
        }
        this.env.services.ui.block();
        try {
            await this.rpc(`cyllo_studio/kanban/${url}/progressbar`, {
                ...this.props.viewDetails,
                properties,

            });

           this.notification.add({
                title: _t("Success"),
                message: "Progressbar saved.",
                type: "notification_panel",
                notificationType: "success",
            });
        } finally {
          this.env.services.ui.unblock();
        }
        this.props.close()
        this.action.doAction("studio_reload");
    }

    handelDiscard(){
        this.props.close()
    }
}
