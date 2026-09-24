/** @odoo-module */
import {Dialog} from "@web/core/dialog/dialog";
import {useService} from "@web/core/utils/hooks";
const {useState, onWillStart, Component, useRef, onMounted, useEffect} = owl;
import {_t} from "@web/core/l10n/translation";

export class ConfigurationBase extends Component {
    /**
     * ConfigurationBase is a component that serves as a base for configuration forms,
     * handling field data fetching, input validation, and confirmation actions.
     */
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.modalRef = useRef("modal-body");
        this.toastRef = useRef("toast-body");
        this.fieldState = useState({});
        this.modelState = useState({})
        this.state = useState({
            dropdown: false,
            search_vars: [],
            searchInput: "",
            isSelected: null,
            showInfo: false
        });
        onWillStart(async () => {
            await this.fetchData()
        });
    }

    async fetchData() {
        this.props.id && await this.fetchFieldsData();
        this.props.id && this.props.name !== "Search" && await this.setModel();
        this.state.searchInput = this.fieldState.search_variable?.variable_name;
        this.initialVariableName = this.fieldState.search_variable?.variable_name;
    }

    async fetchFieldsData() {
        const fields = this.props.fields.map(field => field.name);
        const data = await this.orm.read("node.struct", [this.props.id], fields);

        if (!data.length) {
            console.warn("No data returned for node.struct:", this.props.id);
            return;
        }

        this.props.fields.forEach(field => {
            const rawValue = data[0][field.name];
            if (field.type === "many2One") {
                this.fieldState[field.name] = Array.isArray(rawValue) ? rawValue[0] : null;
            } else {
                this.fieldState[field.name] = rawValue ?? null;
            }
            field.value = rawValue ?? null;
        });
    }

    onClose(){
        this.props.close();
    }

    toggleInfo() {
        this.state.showInfo = !this.state.showInfo;
    }

    async setModel() {
        const modelId = this.fieldState.model_id;
        if (!modelId) {
            console.warn("No model_id found in fieldState, skipping setModel");
            this.modelState.model = {};
            return;
        }

        const model = await this.orm.read("ir.model", [modelId], []);
        this.modelState.model = model?.[0] || {};
    }

    // ####################################################################################
    // FIXME : Assign to variable
    validateInput(value) {
        let isValid = true;
        if (!value) {
            this.state.errorMessage = "";
            this.state.successMessage = "";
            return false;
        }
        if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(value)) {
            this.state.errorMessage = "Invalid variable name. Use letters, numbers, and underscores only. Must start with a letter or underscore.";
            this.state.successMessage = "";
            isValid = false;
        } else if (this.pythonKeywords.includes(value)) {
            this.state.errorMessage = "This is a Python keyword and cannot be used as a variable name.";
            this.state.successMessage = "";
            isValid = false;
        } else if (this.existingVariables.includes(value)) {
            this.state.errorMessage = "This variable name is already taken.";
            this.state.successMessage = "";
            isValid = false;
        } else {
            this.state.errorMessage = "";
            this.state.successMessage = "Valid variable name!";
            isValid = true;
        }
        return isValid;
    }

    // ####################################################################################

    get confirmText() {
        return this.props.confirmText || _t("Confirm");
    }

    get cancelText() {
        return this.props.cancelText || _t("Cancel");
    }

    get getOptions() {
        const variables = this.variables.map(variable => [variable.id, variable.variable_name])
        return [[false, ""], ...variables]
    }

    get variables() {
        if (this.fieldState.search_variable) {
            return (this.props.variables || []).filter(variable => variable.id !== this.fieldState.search_variable.id);
        }
        return this.props.variables || [];
    }

    generateCode() {
        // TODO : Override this function to generate code for the specific block.
        return ""
    }

    validateForm() {
        // TODO : Override this function to validate form.
        // TODO : Apply your logic here.
        return { isValid: true }
    }

    /**
     * Handles confirmation action, validating the form and executing the confirm callback.
     */
    async onConfirm() {
        this.state.used_variables = {}
        const {isValid, errors} = this.validateForm();
        if (isValid) {
            const code = this.generateCode();
            await this.props.onConfirm(this.fieldState, code, this.state.used_variables);
            this.props.close();
        } else {
            this.env.services.effect.add({
                title: _t("Validation Error"),
                message: "Unable to save the record.",
                description: _t(Object.values(errors).join(" \n")),
                type: "notification_panel",
                notificationType: "warning",
            });
        }
    }

    onDiscard() {
        this.props.close();
    }

    updateUsedVariables(value) {
        if (!this.state.used_variables) {
            this.state.used_variables = {[value]: 1};
        } else {
            if (value in this.state.used_variables) this.state.used_variables[value] += 1;
            else this.state.used_variables[value] = 1;
        }
    }

    // FIXME : create write code generation value processing function
    processValue = (val) => {
        switch (val.selectionType) {
            case "record":
                this.updateUsedVariables(val.value.record);
                const variable = this.variables.find(item => item.id === val.value.record);
                return `var_${variable?.variable_name}.${val.value.pathValue}`;
            case "variable":
                this.updateUsedVariables(val.value.selectedVariable);
                return `var_${val.value.pathValue}`;
            default:
                return val.value === true ? "var_True" : val.value === false ? "var_False" : val.value;
        }
    };
}

ConfigurationBase.template = "ConfigurationBase";
ConfigurationBase.components = {Dialog};
