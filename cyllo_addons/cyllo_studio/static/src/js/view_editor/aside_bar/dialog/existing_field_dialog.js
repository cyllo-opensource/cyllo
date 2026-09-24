/** @odoo-module **/
import {
    Component,
    onWillStart,
    useState
} from "@odoo/owl";
import {
    Dialog
} from "@web/core/dialog/dialog";
import {
    CylloStudioDropdown
} from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import {
    _t
} from "@web/core/l10n/translation";
import {
    useService
} from "@web/core/utils/hooks";

const fieldIcons = [{
    fieldType: "integer",
    icon: "ri-numbers-line"
},
{
    fieldType: "char",
    icon: "ri-text"
},
{
    fieldType: "many2one",
    icon: "ri-link"
},
{
    fieldType: "many2many",
    icon: "ri-links-line"
},
{
    fieldType: "one2many",
    icon: "ri-share-box-line"
},
{
    fieldType: "text",
    icon: "ri-file-text-line"
},
{
    fieldType: "selection",
    icon: "ri-arrow-down-s-line"
},
{
    fieldType: "boolean",
    icon: "ri-checkbox-line"
},
{
    fieldType: "binary",
    icon: "ri-file-binary-line"
},
{
    fieldType: "datetime",
    icon: "ri-calendar-line"
},
{
    fieldType: "date",
    icon: "ri-calendar-event-line"
},
{
    fieldType: "html",
    icon: "ri-code-line"
},
{
    fieldType: "float",
    icon: "ri-compass-line"
},
{
    fieldType: "monetary",
    icon: "ri-money-dollar-circle-line"
},
];

/**
 * Dialog component for adding existing fields to a view.
 *
 * Props:
 * - fields: Object containing fields available to add.
 * - model: String, model name.
 * - view_type: String, type of the view (form, tree, etc.).
 * - viewId: Number, ID of the current view.
 * - path: Array, path within the view where fields will be inserted.
 */
export class ExistingFieldDialog extends Component {
    static template = "cyllo_studio.ExistingFieldDialog";

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("effect");
        this.action = useService("action");

        this.state = useState({
            fields: [],
            searchQuery: "",
            selectAll: false,
        });

        if (this.env.dialogData) {
            this.env.dialogData.dismiss = this.onDialogClose.bind(this);
        }

        /**
         * Assign icons to fields based on field type.
         * Runs before component is mounted.
         */
        onWillStart(() => {
            Object.keys(this.props.fields).forEach((key) => {
                const field = this.props.fields[key];
                const matchedIcon = fieldIcons.find(
                    (icon) => icon.fieldType === field.type
                );
                if (matchedIcon) {
                    if (!field.icon) {
                        field.icon = matchedIcon.icon;
                    }
                    if (!field.iconName) {
                        field.iconName = matchedIcon.fieldType;
                    }
                }
            });
        });
    }

    /**
     * Get filtered fields based on search query
     * @returns {Array} Array of field objects with name, type, and icon
     */
    getFilteredFields() {
        const query = this.state.searchQuery.toLowerCase();
        const fieldsArray = Object.keys(this.props.fields).map(key => ({
            name: key,
            type: this.props.fields[key].type,
            icon: this.props.fields[key].icon,
            string: this.props.fields[key].string,
        }));

        if (!query) {
            return fieldsArray;
        }

        return fieldsArray.filter(field =>
            field.string.toLowerCase().includes(query) ||
            field.name.toLowerCase().includes(query) ||
            field.type.toLowerCase().includes(query)
        );
    }

    /**
     * Handle search input
     */
    onSearchInput() {
        // Update selectAll state based on filtered results
        const filteredFields = this.getFilteredFields();
        const allSelected = filteredFields.length > 0 &&
            filteredFields.every(field => this.state.fields.includes(field.name));
        this.state.selectAll = allSelected;
    }

    /**
     * Check if a field is selected
     * @param {String} fieldName - Name of the field
     * @returns {Boolean}
     */
    isFieldSelected(fieldName) {
        return this.state.fields.includes(fieldName);
    }

    /**
     * Toggle field selection
     * @param {Event} ev - The event object
     * @param {String} fieldName - Name of the field to toggle
     */
    toggleField(ev, fieldName) {
        const index = this.state.fields.indexOf(fieldName);
        if (index > -1) {
            this.state.fields.splice(index, 1);
        } else {
            this.state.fields.push(fieldName);
        }

        // Update selectAll state
        const filteredFields = this.getFilteredFields();
        this.state.selectAll = filteredFields.length > 0 &&
            filteredFields.every(field => this.state.fields.includes(field.name));
    }

    /**
     * Toggle select all for filtered fields
     * @param {Event} ev - The event object
     */
    toggleSelectAll(ev) {
        const filteredFields = this.getFilteredFields();

        if (this.state.selectAll) {
            // Deselect all filtered fields
            filteredFields.forEach(field => {
                const index = this.state.fields.indexOf(field.name);
                if (index > -1) {
                    this.state.fields.splice(index, 1);
                }
            });
            this.state.selectAll = false;
        } else {
            // Select all filtered fields
            filteredFields.forEach(field => {
                if (!this.state.fields.includes(field.name)) {
                    this.state.fields.push(field.name);
                }
            });
            this.state.selectAll = true;
        }
    }

    /**
     * Confirms the selection and sends RPC to add fields to the view.
     */
    async onConfirm() {
        if (this.state.fields.length === 0) {
            return;
        }

        try {
            let modelName = this.props.model;

            const storedData = sessionStorage.getItem("RelationalModel");
            if (storedData) {
                try {
                    const parsed = Flatted.parse(storedData);
                    if (Array.isArray(parsed) && parsed[0]?.relation) {
                        modelName = parsed[0].relation;
                    }
                } catch (e) {
                    console.error("Failed to parse RelationalModel:", e);
                }
            }

            await this.rpc("cyllo_studio/add/existing_field", {
                method: "add_existing_field",
                args: [{
                    model: modelName,
                    view_type: this.props.view_type,
                    view_id: this.props.viewId,
                    path: this.props.path,
                    position: "inside",
                }],
                kwargs: {
                    value: this.state.fields,
                },
            });

            this.notification.add({
                title: _t("Success"),
                message: "Changes Added.",
                description: "Exit Studio Mode To View Changes",
                type: "notification_panel",
                notificationType: "success",
                animation: false,
            });

        } finally {
            if (this.props.close) {
                this.props.close();
            }
            if (this.props.onClose) {
                this.props.onClose();
            }
        }
        this.action.doAction("studio_reload");
    }
    /**
     * Handle dialog close
     */
    onDialogClose() {
        if (this.props.close) {
            this.props.close();
        }
        if (this.props.onClose) {
            this.props.onClose();
        }
        this.action.doAction('studio_reload');
    }
}

ExistingFieldDialog.components = {
    Dialog,
    CylloStudioDropdown,
};