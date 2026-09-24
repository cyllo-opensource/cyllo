/** @odoo-module */
import {Component, useState, onWillStart, useRef} from "@odoo/owl";
import {CustomDropdown} from "../Assists/dropdown/CustomDropdown";
import {useService} from "@web/core/utils/hooks";
import {triggerCache} from "../../cache";

export class CustomTrigger extends Component {
    setup() {
        this.state = useState({
            trigger_name: "",
            btnFn: [],
            trigger_value: "",
            icon: null,
        });
        this.orm = useService('orm')
        this.action = useService("action");
        this.fileInputRef = useRef('fileInput');
        onWillStart(async () => {
            await this.loadBtnFn();
            if (this.props.editTriggerId) {
                await this.loadExistingTrigger(this.props.editTriggerId);
            }
        })
    }

    async loadExistingTrigger(id) {
        const records = await this.orm.read('work.function', [id], ['name', 'func_name', 'icon']);
        if (records && records[0]) {
            const rec = records[0];
            this.state.trigger_name = rec.name || "";
            this.state.trigger_value = rec.func_name || "";
            if (rec.icon) {
                this.state.icon = rec.icon;
                this.state.iconType = 'image/svg+xml';
            }
        }
    }

    async loadBtnFn() {
        const modelId = this.props.model
        if (modelId in triggerCache) {
            return this.state.btnFn = triggerCache[modelId];
        }
        const btnFn = await this.orm.call("work.auto", "parse_view_and_fetch_functions", [], {model_id: this.props.model})
        triggerCache[modelId] = this.state.btnFn = this.mapButtonFunctions(btnFn);
    }

    mapButtonFunctions(btnFn) {
        return btnFn.map(fn => ({
            value: fn.button_function,
            label: fn.button_string,
            function_name: fn.button_function
        }));
    }

    onBack() {
        this.props.back();
    }

    updateBtnFn(value) {
        // this.state.trigger_value = this.state.btnFn.filter(item=>item.value === value)
        this.state.trigger_value = value
    }

    get btnTriggers() {
        const currentValue = this.state.trigger_value;
        return this.state.btnFn.filter(item =>
            !this.triggers.includes(item.value) || item.value === currentValue
        );
    }

    get iconSrc() {
        if (!this.state.icon) return null;
        const prefix = this.state.iconType === 'image/svg+xml'
            ? 'data:image/svg+xml;base64,'
            : 'data:image/png;base64,';
        return prefix + this.state.icon;
    }

    uploadIcon() {
        this.fileInputRef.el.click();
    }

    get triggers() {
        return this.props.triggers.map(trigger => trigger.func_name);
    }

    async handleIconUpload(event) {
        const file = event.target.files[0];
        if (file) {
            this.state.icon = await this.fileToBase64(file);
            this.state.iconType = file.type;
        }
    }

    removeIcon() {
        this.state.icon = null;
        this.state.iconPreview = null;
        this.fileInputRef.el.value = '';
    }

    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => resolve(reader.result.split(',')[1]);
            reader.onerror = error => reject(error);
        });
    }

    async onSave() {
        const {trigger_name, trigger_value, icon, iconType} = this.state;
        if (iconType == 'image/png') {
            this.showError('Unable to verify the file. Please ensure its a valid SVG');
            return;
        }
        if (!trigger_name || !trigger_value) {
            this.showError(trigger_name ? 'Please Select a function' : 'Please fill the Name');
            return;
        }

        const isEditMode = Boolean(this.props.editTriggerId);

        if (!isEditMode) {
            const isValue = await this.orm.searchRead("work.function", [["name", "=", trigger_name], ["model_id.id", "=", this.props.model]])
            if (isValue.length) {
                this.showError("Trigger name already exists For This model");
                return;
            }
        }

        try {
            const trigger_type = String(trigger_value || "").startsWith("studio_wf_") ? "button_click" : "other";
            if (isEditMode) {
                await this.orm.write('work.function', [this.props.editTriggerId], {
                    name: trigger_name,
                    func_name: trigger_value,
                    icon,
                    trigger_type,
                });
                this.showEditSuccess();
            } else {
                await this.orm.create('work.function', [{
                    name: trigger_name,
                    func_name: trigger_value,
                    model_id: this.props.model,
                    icon,
                    trigger_type,
                }]);
                this.showSuccess();
            }
            await this.props.updateActions();
            this.props.back();
        } catch (error) {
            this.showError('Failed to save data. Please try again.');
            console.error('Save error:', error);
        }
    }

    getTriggerName(name) {
        this.state.trigger_name = name
    }

    showError(message) {
        this.env.services.effect.add({
            title: "Trigger Creation failed",
            message: "Unable to save the trigger.",
            description: message,
            type: "notification_panel",
            notificationType: "error",
        });
    }

    showSuccess(message) {
        this.env.services.effect.add({
            title: "Success",
            message: "Trigger Successfully created",
            type: "notification_panel",
            notificationType: "success",
        });
    }

    showEditSuccess() {
        this.env.services.effect.add({
            title: "Success",
            message: "Trigger Successfully updated",
            type: "notification_panel",
            notificationType: "success",
        });
    }
}

CustomTrigger.template = 'CustomTrigger';
CustomTrigger.props = {
    back: {type: Function},
    model: {type: Number},
    updateActions: {type: Function},
    triggers: {type: Object},
    editTriggerId: {type: [Number, Boolean], optional: true},
};
CustomTrigger.components = {CustomDropdown};
