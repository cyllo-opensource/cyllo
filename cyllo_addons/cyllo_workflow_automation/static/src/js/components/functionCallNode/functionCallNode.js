/** @odoo-module */
import {useState, useEffect} from "@odoo/owl";
import {ConfigurationBase} from "../configurationBase/configurationBase";
import {TypeToggler} from "../Assists/typeToggler/TypeToggler";
import {CustomDropdown} from "../Assists/dropdown/CustomDropdown";
import {cache} from "../../cache";

const DEFAULT_FUNCTION_NAMES = ['On Create', 'On Write', 'On Unlink']

export class FunctionCallNode extends ConfigurationBase {
    setup() {
        super.setup();
        this.state = useState({
            btnFn: [],
            actionFn: []
        });

        useEffect(() => {
            this.fetchFunctions();
        }, () => [this.fieldState.function_record?.modelId]);
    }

    async fetchData() {
        await super.fetchData();
        await this.fetchFunctions();
    }

    async fetchFunctions() {
        const {modelId} = this.fieldState.function_record || {};
        if (!modelId) return;

        const [btnFn, actionFn, windowAction, reportAction] = await this.getCachedOrFetchFunctions(modelId);
        this.state.btnFn = await this.mapButtonFunctions(btnFn);
        this.state.actionFn = this.mapActionFunctions(actionFn);
        this.state.windowActions = this.mapActionFunctions(windowAction);
        this.state.reportActions = this.mapActionFunctions(reportAction);
    }

    async getCachedOrFetchFunctions(modelId) {
        if (modelId in cache) {
            return cache[modelId];
        }
        const settled = await Promise.allSettled([
            this.orm.call("work.auto", "parse_view_and_fetch_functions", [], {model_id: modelId}),
            this.orm.searchRead("ir.actions.server", [["binding_model_id", "=", modelId]], ["id", "name"]),
            this.orm.searchRead("ir.actions.act_window", [["binding_model_id", "=", modelId]], ["id", "name"]),
            this.orm.searchRead("ir.actions.report", [["binding_model_id", "=", modelId]], ["id", "name"]),
        ]);
        const functions = settled.map((result, index) => {
            if (result.status === "fulfilled") {
                return result.value || [];
            }
            console.warn(
                `Button Click node: could not load function source #${index} for model ${modelId}`,
                result.reason,
            );
            return [];
        });

        cache[modelId] = functions;
        return functions;
    }

    async mapButtonFunctions(btnFn) {
        if (DEFAULT_FUNCTION_NAMES.includes(this.props.trigger)) {
            return btnFn.map(fn => ({
                value: fn.button_val,
                label: fn.button_string,
                function_name: fn.button_function
            }));
        }
        const result = await this.orm.searchRead(
            "work.function",
            [["model_id.id", "=", this.fieldState.function_record?.modelId], ["name", "=", this.props.trigger]]
        )
        const val = btnFn.filter((f) => {
            if (f.button_function === result[0]?.func_name) {
                return f.model !== this.fieldState.function_record.modelName;
            }
            return true
        }).map(fn => ({
            value: fn.button_val,
            label: fn.button_string,
            function_name: fn.button_function
        }));
        return val
    }

    mapActionFunctions(actionFn) {
        return actionFn.map(fn => ({
            value: fn.id,
            label: fn.name
        }));
    }

    setType(type) {
        this.fieldState.function_type = type.value;
        this.fieldState.function_name = {}
    }

    get getTogglerOptions() {
        return [
            {label: "Action", value: "server_action",},
            {label: "Button", value: "button_action",},
            {label: "Window", value: "window_action",},
            {label: "Report", value: "report_action",},
        ]
    }

    get selectedFunctionItems() {
        switch (this.fieldState.function_type) {
            case "server_action":
                return this.state.actionFn || []
            case "button_action":
                return this.state.btnFn || []
            case "window_action":
                return this.state.windowActions || []
            case "report_action":
                return this.state.reportActions || []
            default:
                return []
        }
    }

    get records() {
        return this.variables
            .filter(v => ["record", "recordset"].includes(v.variable_type) && v.modelId &&
            v.modelName !== "res.company")
            .map(v => ({value: v.id, label: v.variable_name}));
    }

    onChangeVariable(value) {
        this.fieldState.function_record = this.variables.find(v => v.id === value);
        this.fieldState.function_name = undefined;
    }

    onChangeFunction(value) {
        const selectedFunction = this.selectedFunctionItems.find(fn => fn.value === value);
        this.fieldState.function_name = selectedFunction;
    }

    setLabel(label) {
        this.fieldState.label = label;
        this.env.bus.trigger("CHANGE-LABEL", {label, nodeId: this.props.id});
    }

    generateCode() {
        const {function_record, function_name, function_type} = this.fieldState;
        let code = '';
        if (function_type === "server_action") {
            code = this.generateServerActionCode(function_record, function_name);
        } else if (function_type === "button_action") {
            code = this.generateButtonActionCode(function_record, function_name);
        } else if (function_type === "window_action") {
            code = this.generateActionCode(function_record, function_name, "ir.actions.act_window");
        } else if (function_type === "report_action") {
            code = this.generateActionCode(function_record, function_name, "ir.actions.report");
        }
        return code;
    }
     /**
     * Button code generation
     */
    generateButtonActionCode(record, fn) {
        this.props.updateImports({
            parent: 'import logging\n_logger = logging.getLogger(__name__)',
            nodeId: this.props.id
        })
        const baseCode = `
try:
    cy_w_action = ${record.variable_name}.${fn.function_name}()
    if isinstance(cy_w_action, dict) and cy_w_action.get('type') and cy_w_action.get('type') in ["ir.actions.act_window", "ir.actions.act_url", "ir.actions.client", "ir.actions.report"]:
        if not cy_w_action.get('views'): cy_w_action['views'] = [[False,"form"]]
        cy_w_action['context'] = {'active_ids': ${record.variable_name}.ids, 'active_id': ${record.variable_name}.id, 'active_model': '${record.modelName}'}
        channel = "bus_do_action"
        message = {
            "auth" : {"user": env.user.id},
            "action": cy_w_action,
            "channel": channel
        }
        env["bus.bus"]._sendone(channel, "notification", message)
except (UserError, ValidationError):
    raise
except Exception as e:
    _logger.error("Check Workflow automation rule(ID:${this.props.id}): %s",e)`;
        return record.variable_type === "recordset"
            ? `for rec in ${record.variable_name}:\n${baseCode.split('\n').map(line => '\t' + line).join('\n')}`
            : baseCode;
    }

     /**
     * action code generation
     */
    generateServerActionCode(record, fn) {
        const contextBase = `
    active_model="${this.modelState.model.model}",
    active_ids=${record.variable_name}.ids,
    onchange_self=${record.variable_name},`;
        const additionalContext = record.variable_type === "record"
            ? `\n    active_id=${record.variable_name}.id,`
            : '';

        return `
try:
    server_action = env["ir.actions.server"].browse(${fn.value}) or {}
    server_action_res = server_action.with_context(${contextBase}${additionalContext}
    ).run()
    options = {
            "additionalContext": {
                "active_model":"${record.modelName}",
                "active_ids":${record.variable_name}.ids,
                "onchange_self":${record.variable_name},
                "active_id":${record.variable_name}.id,
            }
        }
    if server_action_res:
        if not server_action_res.get('views'): server_action_res['views'] = [[False,"form"]]
    if isinstance(server_action_res, dict) and server_action_res.get('type') and server_action_res.get('type') in ["ir.actions.act_window", "ir.actions.act_url", "ir.actions.client", "ir.actions.report"]:
        channel = "bus_do_action"
        message = {
            "auth" : {"user": env.user.id},
            "action": server_action_res,
            "channel": channel,
            "options":options,
        }
        env["bus.bus"]._sendone(channel, "notification", message)
except Exception as e:
    _logger.error("Check Workflow automation rule(ID:${this.props.id}): %s",e)
`;
    }

     /**
     * window/report action code generation
     */
    generateActionCode(record, fn, actionType) {
        return `
try:
    action_obj = env["${actionType}"].browse(${fn.value}).read()[0]
    action_obj['context'] = {'active_ids': ${record.variable_name}.ids, 'active_id': ${record.variable_name}.id, 'active_model': '${record.modelName}'}
    options = {
            "additionalContext": {
                "active_model":"${record.modelName}",
                "active_ids":${record.variable_name}.ids,
                "onchange_self":${record.variable_name},
                "active_id":${record.variable_name}.id,
            }
        }
    channel = "bus_do_action"
    message = {
        "auth" : {"user": env.user.id},
        "action": action_obj,
        "channel": channel,
        "options":options,
    }
    env["bus.bus"]._sendone(channel, "notification", message)
except Exception as e:
    _logger.error("Check Workflow automation rule(ID:${this.props.id}): %s",e)`;
    }

    /**
     *  form validation
     */
    validateForm() {
        const {function_record, function_name, label} = this.fieldState

        // Initialize an errors object
        const errors = {};

        if (!function_record) {
            errors.function_record = "A record must be selected.";
        }

        if (!function_name?.value) {
            errors.function_name = "A function must be selected.";
        }

        if (!label || label === "" || label.trim() === "") {
            errors.label = "Set the label.";
        }
        // Return the validation result
        if (Object.keys(errors).length > 0) {
            return {isValid: false, errors};
        }
        return {isValid: true};
    }
}

FunctionCallNode.template = "FunctionCallNode";
FunctionCallNode.components = {
    ...ConfigurationBase.components,
    TypeToggler,
    CustomDropdown
};