/** @odoo-module */
import { Component, xml, useState, onWillStart, onMounted, useRef, onWillUnmount, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import {
    conditionFields,
    warningFields,
    searchFields,
    createFields,
    writeFields,
    functionCallFields,
    variableFields,
    codeFields,
    mailFields,
    FollowerFields,
    smsFields,
    whatsappFields,
    ActivityFields,
    MappedFields,
    AssignmentFields,
    loopFields,
    reusableAutomationFields,
    windowFields,
    duplicateFields,
    webhookFields,
    tryCatchFields,
} from "./fields";
import {
    icons,
} from "./icons";
import { SearchNode } from "./components/searchNode/searchNode";
import { jsonrpc } from "@web/core/network/rpc_service";
import { _t } from "@web/core/l10n/translation";
import { WarningNode } from "./components/warningNode/warningNode";
import { CreateNode } from "./components/createNode/createNode";
import { FunctionCallNode } from "./components/functionCallNode/functionCallNode";
import { CodeNode } from "./components/xCodeNode/codeNode";
import { WriteNode } from "./components/writeNode/writeNode";
import { MailNode } from "./components/mailNode/mailNode";
import { FollowerNode } from "./components/FollowerNode/followerNode";
import { SmsNode } from "./components/xsmsNode/smsNode";
import { WhatsAppNode } from "./components/whatsappNode/whatsappNode";
import { ConditionNode } from "./components/xconditionNode/conditionNode";
import { ActivityNode } from "./components/ActivityNode/activityNode";
import { PYTHON_KEYWORDS } from "./components/Assists/utils/utils";
import { removeNodeIdFromVariables } from "./utils/utils"
import { LoopNode } from "./components/loopNode/loopNode";
import { ReusableAutomationNode } from "./components/reusableAutomationNode/reusableAutomationNode";
import { WindowNode } from "./components/windowNode/windowNode";
import { DuplicateNode } from "./components/DuplicateNode/duplicateNode";
import { WebhookNode } from "./components/webhookNode/webhookNode";
import { TryCatchNode } from "./components/tryCatchNode/tryCatchNode";

const MODAL_CONFIGS = {
    'Warning': {
        component: WarningNode,
        fields: warningFields,
    },
    'Create': {
        component: CreateNode,
        fields: createFields,
    },
    'Write': {
        component: WriteNode,
        fields: writeFields,
    },
    'Button Click': {
        component: FunctionCallNode,
        fields: functionCallFields,
    },
    'Code': {
        component: CodeNode,
        fields: codeFields,
    },
    'Search': {
        component: SearchNode,
        fields: searchFields,
    },
    'Condition': {
        component: ConditionNode,
        fields: conditionFields,
    },
    'Mail': {
        component: MailNode,
        fields: mailFields,
    },
    'SMS': {
        component: SmsNode,
        fields: smsFields,
    },
    'WhatsApp': {
        component: WhatsAppNode,
        fields: whatsappFields,
    },
    'Follower': {
        component: FollowerNode,
        fields: FollowerFields,
    },
    'Activity': {
        component: ActivityNode,
        fields: ActivityFields
    },
    'Loop': {
        component: LoopNode,
        fields: loopFields,
    },
    'Reuse Automation': {
        component: ReusableAutomationNode,
        fields: reusableAutomationFields,
    },
    'Window': {
        component: WindowNode,
        fields: windowFields,
    },
    'Duplicate': {
        component: DuplicateNode,
        fields: duplicateFields,
    },
    'Webhook': {
        component: WebhookNode,
        fields: webhookFields,
    },
    'Try Catch': {
        component: TryCatchNode,
        fields: tryCatchFields,
    },
};


/**
 * _registerWebhookResponseVariables
 *
 * Registers any webhook `store_variable` response actions as workflow
 * variables so they appear in the Variables panel and are selectable
 * in all following nodes (Code, Mail, SMS, etc.).
 *
 * Called from the webhook node's onConfirm handler in the two
 * workflow_nodes.js Webhook branches.
 *
 * @param {object} fieldState   - The confirmed field state from the webhook node
 * @param {object} variableCtx  - The result of this.variableContext
 * @param {object} env          - The OWL environment (this.env)
 * @param {string|number} nodeId - The nodeId of the webhook node (this.props.nodeId)
 */
function _registerWebhookResponseVariables(fieldState, variableCtx, env, nodeId) {
    const actions = Array.isArray(fieldState.webhook_actions) ? fieldState.webhook_actions : [];
    const storeActions = actions.filter(a => a && a.action_type === 'store_variable');
    if (!storeActions.length) return;

    const BUTTON_CLASSES = ['btn-info', 'btn-primary', 'btn-warning', 'btn-secondary', 'btn-success', 'btn-danger'];
    const randomClass = BUTTON_CLASSES[Math.floor(Math.random() * BUTTON_CLASSES.length)];

    const existingVars = (variableCtx && variableCtx.variables) ? variableCtx.variables : [];

    const newVars = [];
    for (let idx = 0; idx < storeActions.length; idx++) {
        const action = storeActions[idx];
        const varName = (action.variable_name || '').trim();
        if (!varName) continue;

        // Build a stable ID so re-confirming the node updates in-place
        const varId = `wh_var_${nodeId}_${varName}`;
        const existing = existingVars.find(v => v.id === varId);

        if (existing) {
            // Update in-place (name may have changed for existing slot)
            existing.variable_name = varName;
            existing.webhook_extract_path = action.extract_path || '';
        } else {
            newVars.push(owl.reactive({
                id: varId,
                variable_name: varName,
                variable_type: 'string',
                variable_value: '',
                // Metadata — used for cleanup and display
                source: 'webhook',
                webhook_node_id: nodeId,
                webhook_extract_path: action.extract_path || '',
                // Required by the variable context / selector UI
                scopeId: nodeId,
                usedIn: [],
                class: randomClass,
                delete: false,
            }));
        }
    }

    // Remove stale webhook vars from THIS node that no longer have a matching action
    const activeVarNames = new Set(storeActions.map(a => (a.variable_name || '').trim()).filter(Boolean));
    const withoutStale = existingVars.filter(v => {
        if (v.source !== 'webhook' || String(v.webhook_node_id) !== String(nodeId)) return true;
        return activeVarNames.has(v.variable_name);
    });

    if (newVars.length > 0 || withoutStale.length !== existingVars.length) {
        try {
            env.variables.setContext({ variables: [...withoutStale, ...newVars] });
            env.bus.trigger("UPDATE-VARIABLE-STATE");
        } catch (err) {
            console.error("WebhookNode: failed to register response variables:", err);
        }
    }
}

export class ModelComponent extends Component {
    setup() {
        this.action = useService("action");
        this.dialogService = useService("dialog");
        this.root = useRef("root");
        this.notification = useService("notification");
        this.handleUpdateMe = this.updateMe.bind(this);
        this.handlePrimaryUpdate = ({ detail }) => {
            this.props.primary_model_id = detail.model_id
        };
        this.handleVariableUsage = ({ detail: { variable, node } }) => {
            const updatedVariable = this.env.variables.context.variables.find(item => item.id === variable);
            !updatedVariable.usedIn.includes(node) && updatedVariable.usedIn.push(node);
            this.env.bus.trigger("UPDATE-VARIABLE-STATE");
        };
        this.handleChangeLabel = ({ detail: { label, nodeId } }) => {
            if (this.props.nodeId === nodeId) {
                this.state.label = label
            }
        };
        this.handleOpenModal = ({ detail }) => {
            if (this.props.nodeId === detail.nodeId) {
                this.openConfigModal()
            }
        };
        this.handleFlowValidation = ({ detail: { nodeIds } }) => {
            if (nodeIds.includes(this.props.nodeId)) {
                this.state.error = true;
            }
            setTimeout(() => {
                if (owl.status(this) !== "destroyed") {
                    this.state.error = false;
                }
            }, 5000)
        };
        this.handleTestResult = ({ detail }) => {
            if (detail.node_id !== this.props.nodeId) {
                return;
            }
            this.state.testStatus = detail.status || 'pending';
            this.state.testMessage = detail.message || "";
            this.applyTestStatusToParent();
        };
        this.handleTestReset = () => {
            this.state.testStatus = 'pending';
            this.state.testMessage = "";
            this.applyTestStatusToParent();
        };
        this.env.context.addEventListener("UPDATE-ME", this.handleUpdateMe)
        this.env.bus.addEventListener("UPDT-PRIMARY", this.handlePrimaryUpdate);
        this.env.bus.addEventListener("UPDATE-VARIABLE-USAGE", this.handleVariableUsage);
        this.env.bus.addEventListener("CHANGE-LABEL", this.handleChangeLabel)
        this.env.bus.addEventListener("OPEN:MODAL", this.handleOpenModal)
        this.env.bus.addEventListener("FIND:NODE:VARIABLE:USED", this.handleFindNodeVariableUsed)
        this.env.bus.addEventListener("FLOW:VALIDATION", this.handleFlowValidation);
        this.env.bus.addEventListener("FLOW:TEST:RESULT", this.handleTestResult);
        this.env.bus.addEventListener("FLOW:TEST:RESET", this.handleTestReset);
        this.state = useState({
            model: {},
            resId: 0,
            context: {},
            error: false,
            label: "",
            findUsage: false,
            testStatus: 'pending',
            testMessage: "",
        })
        this.orm = useService("orm");
        onWillStart(this.manageNodeData);
        onMounted(async () => {
            const label = await this.orm.read("node.struct", [this.props.nodeId], ["label"])
            if (label && label[0]) {
                this.state.label = label[0].label
            }
            this.state.context = this.context;
        })
        onWillUnmount(() => {
            this.env.context.removeEventListener("UPDATE-ME", this.handleUpdateMe);
            this.env.bus.removeEventListener("UPDT-PRIMARY", this.handlePrimaryUpdate);
            this.env.bus.removeEventListener("UPDATE-VARIABLE-USAGE", this.handleVariableUsage);
            this.env.bus.removeEventListener("CHANGE-LABEL", this.handleChangeLabel);
            this.env.bus.removeEventListener("OPEN:MODAL", this.handleOpenModal);
            this.env.bus.removeEventListener("FIND:NODE:VARIABLE:USED", this.handleFindNodeVariableUsed);
            this.env.bus.removeEventListener("FLOW:VALIDATION", this.handleFlowValidation);
            this.env.bus.removeEventListener("FLOW:TEST:RESULT", this.handleTestResult);
            this.env.bus.removeEventListener("FLOW:TEST:RESET", this.handleTestReset);
        })
    }

    handleFindNodeVariableUsed = (event) => {
        const { detail } = event;
        const isCondition = this.props.name === "Condition";
        const parentDiv = this.getParentDiv();
        this.state.findUsage = false;
        this.toggleParentClass(parentDiv, false);
        if (this.props.nodeId === detail.nodeId) {
            if (isCondition) {
                this.toggleParentClass(parentDiv, true);
            } else {
                this.state.findUsage = true;
            }
            this.scheduleReset(parentDiv);
        }
    }
    getParentDiv() {
        return this.root.el?.closest('.drawflow-node') || null;
    }
    toggleParentClass(parentDiv, add) {
        if (parentDiv) {
            parentDiv.classList[add ? 'add' : 'remove']('cy-find-usage');
        }
    }
    scheduleReset(parentDiv) {
        setTimeout(() => {
            if (owl.status(this) !== "destroyed") {
                this.state.findUsage = false;
                this.toggleParentClass(parentDiv, false);
            }
        }, 5000);
    }

    applyTestStatusToParent() {
        const parentDiv = this.getParentDiv();
        if (!parentDiv) {
            return;
        }
        ['cy-test-running', 'cy-test-success', 'cy-test-warning', 'cy-test-error'].forEach(className => {
            parentDiv.classList.remove(className);
        });
        const className = this.testStatusClass;
        if (className) {
            parentDiv.classList.add(className);
        }
    }

    async nameGet() {
        const [resId, modelName] = this.props.model
        this.state.resId = resId
        return await this.orm.read(modelName, [resId], ["display_name"])
    }

    async manageNodeData() {
        if (this.props.model.length) {
            const data = await this.nameGet()
            this.state.model = data[0]
        }
        else {
            this.state.model.display_name = this.props.name;
        }
    }
    updateMe() {
        this.state.context = this.context;
    }

    get automationIdentifiers() {
        const allVariables = [...(this.variableContext.variables || []), ...(this.env.globalVariables.context.variables || [])]
        const identifiers = allVariables.map(item => item.variable_name)
        return { pythonKeywords: [...PYTHON_KEYWORDS], variableNames: [...identifiers] };
    }
    /**
     * Determines whether the current node is inside an IF or ELSE branch
     * of a cron-mode Condition node. Returns the branch label and the
     * corresponding recordset variable objects so the caller can filter
     * the variable list shown in action modals.
     *
     * @returns {{ isCronBranch: boolean, branch?: 'if'|'else',
     *             cronVariable?: object, complementVariable?: object }}
     */
    getCronBranchInfo() {
        const currentContext = this.context;
        const currentNode = currentContext.nodes.find(n => n.nodeId === this.props.nodeId);
        if (!currentNode) return { isCronBranch: false };

        // Checks whether `target` is reachable from `root` by following .right links.
        const isInBranch = (root, target, visited = new Set()) => {
            if (!root || visited.has(root.nodeId)) return false;
            if (root === target) return true;
            visited.add(root.nodeId);
            return isInBranch(root.right, target, visited);
        };

        // Walk up ancestor chain to find the nearest cron-mode Condition parent.
        let walker = currentNode;
        while (walker && walker.left) {
            const parent = walker.left;
            if (parent.isParent && parent.else_setup_code) {
                // Derive variable names: else_setup_code = "<complement> = env[...].search(...)"
                const complementVarName = parent.else_setup_code.split('=')[0].trim();
                const cronVarName = complementVarName.replace(/_complement$/, '');
                const allVars = this.variableContext.variables || [];
                const cronVariable = allVars.find(v => v.variable_name === cronVarName) || null;
                const complementVariable = allVars.find(v => v.variable_name === complementVarName) || null;

                if (isInBranch(parent.child1, currentNode)) {
                    return { isCronBranch: true, branch: 'if', cronVariable, complementVariable };
                }
                if (isInBranch(parent.child2, currentNode)) {
                    return { isCronBranch: true, branch: 'else', cronVariable, complementVariable };
                }
            }
            walker = walker.left;
        }
        return { isCronBranch: false };
    }

    /**
     * Reads the technical model name of an ir.model id.
     * Returns undefined when the id is missing or no longer exists, which is the
     * case for reusable automations that have no primary model node.
     */
    async readModelName(modelId) {
        if (!modelId) {
            return undefined;
        }
        const [model] = await this.orm.read('ir.model', [modelId], ['model']);
        return model?.model || undefined;
    }

    async openConfigModal() {
        const runBusy = this.env.canvasBusy;
        if (!runBusy) {
            return this._openConfigModal();
        }
        return runBusy(`Opening ${this.props.name}...`, async () => {
            const openBefore = document.querySelectorAll('.o_dialog').length;
            await this._openConfigModal();
            await this._waitForDialog(openBefore);
        });
    }

    /**
     * Resolves once a new `.o_dialog` is in the DOM, or after `maxWait` ms so a
     * modal that never opens can't leave the canvas locked.
     */
    _waitForDialog(openBefore, maxWait = 8000) {
        return new Promise((resolve) => {
            const start = performance.now();
            const check = () => {
                const opened = document.querySelectorAll('.o_dialog').length > openBefore;
                if (opened || performance.now() - start > maxWait) {
                    resolve();
                    return;
                }
                requestAnimationFrame(check);
            };
            requestAnimationFrame(check);
        });
    }

    async _openConfigModal() {
        const modalConfig = MODAL_CONFIGS[this.props.name];
        if (modalConfig) {
            const { component, fields } = modalConfig;

            const cronInfo = this.getCronBranchInfo();
            let filteredVariables = this.getVariables;
            if (cronInfo.isCronBranch) {
                // In cron branches, only expose the relevant recordset variable:
                // IF → the search result var; ELSE → the complement var.
                // Date/scalar variables (e.g. current_date) are always preserved.
                const nonRecordsetVars = filteredVariables.filter(
                    v => v.variable_type !== 'recordset' && v.variable_type !== 'record'
                );
                const branchVar = cronInfo.branch === 'if' ? cronInfo.cronVariable : cronInfo.complementVariable;
                filteredVariables = branchVar ? [...nonRecordsetVars, branchVar] : filteredVariables;
            } else {
                // Outside cron branches, hide internally-generated _complement variables.
                filteredVariables = filteredVariables.filter(v => !v.variable_name?.endsWith('_complement'));
            }

            const props = {
                title: this.props.name,
                name: this.props.name,
                id: this.props.nodeId,
                fields,
                onConfirm: this.onConfirm.bind(this),
                updateImports: this.props.updateImports,
                position: "end",
                width: "65%",
                backdrop: true,
                identifiers: this.automationIdentifiers,
                variables: filteredVariables
            };
            if (this.props.name === 'Create') {
                props.primaryModelId = this.props.primary_model_id;
                props.trigger = this.triggerName()
                props.nodeName = this.props.name.toLowerCase()
                props.onConfirm = (fieldState, code, usedVariables) => {
                    this.onConfirm(fieldState, code, usedVariables);
                    this.updateVariable(fieldState);
                }
                props.display_name = "The Create Modal helps users effortlessly create records within the model using dynamic content."

            } else if (this.props.name === 'Write') {
                props.display_name = "The Write node updates field values on the current record using the selected model."
            } else if (this.props.name === 'Button Click') {
                const resModelName = await this.readModelName(this.props.primary_model_id);
                const functions = resModelName ? await this.fetchFunctions(resModelName) : [];
                props.resModel = resModelName;
                props.functions = functions;
                props.trigger = this.allTriggerName()
                props.display_name = "The Button Click Modal lets users quickly access and manage all button and cog menu functions."
            } else if (this.props.name === 'Code') {
                props.display_name = "The Code Modal provides an interface for users to write and execute Python code directly"
            } else if (this.props.name === 'Search') {
                const fields = searchFields.map(field => field.name);
                const searchFieldData = await this.orm.read('node.struct', [this.props.nodeId], fields)
                const modelIdToSearch = searchFieldData[0].model_id ? searchFieldData[0].model_id[0] : this.props.primary_model_id;
                props.resModel = modelIdToSearch ? await this.readModelName(modelIdToSearch) : undefined;
                props.onConfirm = (fieldState, code, usedVariables) => {
                    this.onConfirm(fieldState, code, usedVariables);
                    this.updateVariable(fieldState);
                }
                props.display_name = "The Search Modal helps users quickly find and retrieve specific nodes by using dynamic search criteria."
            } else if (this.props.name === "Condition") {
                props.resModel = await this.readModelName(this.props.primary_model_id);
                props.triggerType = this.env.globalContext().triggerType;
                props.display_name = "The Condition Modal lets users add and apply different conditions to customize and control functionality"
            } else if (this.props.name === "Mail") {
                props.primaryModelId = this.props.primary_model_id;
                props.display_name = "The Mail Modal provides an interface for users to compose and send emails easily"
            }
            else if (this.props.name === "SMS") {
                props.primaryModelId = this.props.primary_model_id;
                props.display_name = "The SMS Modal allows users to compose and send text messages efficiently."
            } else if (this.props.name === "Follower") {
                props.primaryModelId = this.props.primary_model_id;
                props.display_name = "The Followers Modal enables users to manage followers to records or entities"
            }
            else if (this.props.name === "Warning") {
                props.display_name = "The Warning Modal allows users to configure and display warning messages to alert users about important information"
            } else if (this.props.name === "Activity") {
                props.primaryModelId = this.props.primary_model_id;
                props.display_name = "The Activity Modal enables users to manage Activity"
            } else if (this.props.name === 'Webhook') {
                props.display_name = "The Webhook Node allows you to send data to external APIs via HTTP requests.";
                props.onConfirm = (fieldState, code, usedVariables) => {
                    this.onConfirm(fieldState, code, usedVariables);
                    _registerWebhookResponseVariables(
                        fieldState,
                        this.variableContext,
                        this.env,
                        this.props.nodeId,
                    );
                };
            } else if (this.props.name === 'Loop') {
                props.primaryModelId = this.props.primary_model_id;
                props.display_name = "The Loop Node iterates over a recordset field or variable, executing child nodes for each record in turn.";
                props.onConfirm = (fieldState, code, usedVariables, modelInfo) => {
                    this.onConfirm(fieldState, code, usedVariables);
                    this.updateLoopVariable(fieldState, modelInfo || {});
                };
            } else if (this.props.name === 'Reuse Automation') {
                props.work_auto_id = this.props.work_auto_id;
                props.primary_model_id = this.props.primary_model_id;
                props.primary_model_name = this.props.primary_model_name;
                props.display_name = "Select a reusable automation to call from this node. The selected automation will run using the record you choose and continue when it finishes.";
                props.onEditReusableFlow = async () => {
                    await this.editReusableAutomationFlow();
                };
            } else if (this.props.name === 'Duplicate') {
                props.primaryModelId = this.props.primary_model_id;
                props.display_name = "The Duplicate Node copies a record and optionally overrides specific fields on the copy. Use the result variable to pass the copy to downstream nodes.";
                props.onConfirm = (fieldState, code, usedVariables) => {
                    this.onConfirm(fieldState, code, usedVariables);
                    if (fieldState.duplicate_result_variable && fieldState.duplicate_record) {
                        const recVar = (this.variableContext.variables || []).find(v => v.id === fieldState.duplicate_record.value);
                        if (recVar) {
                            const varName = fieldState.duplicate_result_variable.trim();
                            const varId = `dup_var_${this.props.nodeId}`;
                            const existingVars = this.variableContext.variables || [];
                            const alreadyRegistered = existingVars.find(v => v.id === varId);
                            if (!alreadyRegistered) {
                                this.env.variables.setContext({
                                    variables: [
                                        ...existingVars,
                                        owl.reactive({
                                            id: varId,
                                            variable_name: varName,
                                            variable_type: recVar.variable_type,
                                            modelId: recVar.modelId,
                                            modelName: recVar.modelName,
                                            scopeId: this.props.nodeId,
                                            usedIn: [],
                                            class: this.buttonClass,
                                        })
                                    ]
                                });
                            } else {
                                alreadyRegistered.variable_name = varName;
                                alreadyRegistered.variable_type = recVar.variable_type;
                                alreadyRegistered.modelId = recVar.modelId;
                                alreadyRegistered.modelName = recVar.modelName;
                            }
                            this.env.bus.trigger("UPDATE-VARIABLE-STATE");
                        }
                    }
                };
            } else if (this.props.name === 'Webhook') {
                props.display_name = "The Webhook Node allows you to send data to external APIs via HTTP requests.";
                props.onConfirm = (fieldState, code, usedVariables) => {
                    this.onConfirm(fieldState, code, usedVariables);
                    _registerWebhookResponseVariables(
                        fieldState,
                        this.variableContext,
                        this.env,
                        this.props.nodeId,
                    );
                };
            } else if (this.props.name === 'Try Catch') {
                props.display_name = "The Try Catch Node handles exceptions during execution, allowing you to gracefully catch errors and continue the workflow.";
                props.onConfirm = (fieldState, code, usedVariables) => {
                    this.onConfirm(fieldState, code, usedVariables);
                    this.updateTryCatchVariable(fieldState);
                };
            }
            this.dialogService.add(component, props);
        } else {
            // TODO: Handle unknown modal type
        }
    }

    /**
     * Registers the loop iteration variable into the frontend variable context
     * so nodes inside the loop body can select it from their variable dropdowns.
     */
    updateLoopVariable(fieldState, modelInfo = {}) {
        const varName = fieldState.loop_variable_name;
        if (!varName) return;
        const existingVars = this.env.variables.context.variables || [];
        const nodeId = this.props.nodeId;
        const varId = `loop_var_${nodeId}`;
        const alreadyRegistered = existingVars.find(v => v.id === varId);
        if (!alreadyRegistered) {
            this.env.variables.setContext({
                variables: [
                    ...existingVars,
                    owl.reactive({
                        id: varId,
                        variable_name: varName,
                        variable_type: 'record',
                        modelId: modelInfo.modelId || null,
                        modelName: modelInfo.modelName || null,
                        scopeId: nodeId,
                        usedIn: [],
                        class: this.buttonClass,
                    })
                ]
            });
        } else {
            alreadyRegistered.variable_name = varName;
            alreadyRegistered.scopeId = nodeId;
            alreadyRegistered.class = this.buttonClass;
            if (modelInfo.modelId) alreadyRegistered.modelId = modelInfo.modelId;
            if (modelInfo.modelName) alreadyRegistered.modelName = modelInfo.modelName;
        }
        this.env.bus.trigger("UPDATE-VARIABLE-STATE");
    }

    /**
     * Registers the Try Catch error variable into the frontend variable context
     * so nodes inside the catch branch can select it from their variable dropdowns.
     * The variable is stored as "var_<rawName>" matching processValue() output.
     */
    updateTryCatchVariable(fieldState) {
        const rawVarName = (fieldState.try_catch_error_variable || '').trim();
        if (!rawVarName) return;
        const existingVars = this.env.variables.context.variables || [];
        const nodeId = this.props.nodeId;
        const varId = `${nodeId}_error`;
        const displayVarName = `var_${rawVarName}`;
        const alreadyRegistered = existingVars.find(v => v.id === varId);
        if (!alreadyRegistered) {
            this.env.variables.setContext({
                variables: [
                    ...existingVars,
                    owl.reactive({
                        id: varId,
                        variable_name: displayVarName,
                        variable_type: 'string',
                        variable_value: '',
                        delete: false,
                        modelName: '',
                        modelId: '',
                        scopeId: nodeId,
                        usedIn: [],
                        class: '',
                    })
                ]
            });
        } else {
            alreadyRegistered.variable_name = displayVarName;
        }
        this.env.bus.trigger("UPDATE-VARIABLE-STATE");
    }

    async fetchFunctions(model) {
        return await jsonrpc('cyllo_auto_work/find/functions', {
            model,
        });
    }

    updateContext(code) {
        const context = this.context;
        const currentNode = context.nodes.find(node => node.nodeId === this.props.nodeId);
        if (!currentNode) {
            // The node was removed from the context (e.g. an Undo/Redo ran while
            // this node's configuration wizard was still open) -- there is
            // nothing left to update.
            console.warn(`updateContext: node ${this.props.nodeId} no longer exists in context.`);
            return;
        }
        currentNode.code = code;
        this.env.bus.trigger("UPDATE-CODE")
    }
    updateVariableUsage(usedVariables) {
        const nodeId = this.props.nodeId;
        const contextVariables = this.variableContext.variables || [];
        removeNodeIdFromVariables(contextVariables, nodeId)
        // Add nodeId to newly used variables
        Object.keys(usedVariables).forEach(varId => {
            const variable = contextVariables.find(v => v.id === varId);
            if (variable && variable.usedIn) {
                if (!variable.usedIn.includes(nodeId)) {
                    variable.usedIn.push(nodeId);
                }
            }
        });
    }

    updateVariable(fieldState) {
        const { model_id, search_variable } = fieldState;
        if (!search_variable) return;
        const existingVars = this.env.variables.context.variables || [];
        const variable = existingVars.find(item => item.id === search_variable.id);
        if (variable) {
            variable.modelId = model_id;
            variable.variable_type = search_variable.variable_type;
            variable.variable_name = search_variable.variable_name;
        } else {
            this.env.variables.setContext({ variables: [...existingVars, owl.reactive({ ...search_variable, scopeId: this.props.nodeId, class: this.buttonClass })] })
        }
        this.env.bus.trigger("UPDATE-VARIABLE-STATE");
    }

    async updateNode(fieldState, code) {
        await this.orm.call('node.struct', 'save_data', [this.props.nodeId, { ...fieldState, code }]);
    }

    async editReusableAutomationFlow() {
        if (this.props.name !== 'Reuse Automation') {
            return;
        }
        const result = await this.orm.call(
            'node.struct',
            'create_editable_reuse_copy',
            [[this.props.nodeId]]
        );

        if (!result?.id) {
            return;
        }

        this.state.label = result.label || result.name || this.state.label;

        const currentNode = this.context.nodes.find(
            (node) => node.nodeId === this.props.nodeId
        );
        if (currentNode) {
            currentNode.reused_work_auto_id = result.id;
            currentNode.code = result.code || currentNode.code;
            currentNode.label = result.label || currentNode.label;
        }

        this.action.doAction({
            type: "ir.actions.client",
            tag: "automation_view",
            target: "current",
            context: {
                rec_id: result.id,
            },
        });
    }

    raiseNotification(text, type) {
        this.env.services.effect.add({
            title: "Success",
            message: _t(text),
            type: "notification_panel",
            notificationType: type,
        });
    }

    async onConfirm(fieldState, code, usedVariables) {
        this.updateContext(code);

        // Sync else_setup_code onto the in-memory context node so updateCode()
        // can inject the complement search line at the start of the else block.
        if (fieldState.else_setup_code !== undefined) {
            const ctx = this.context;
            const ctxNode = ctx.nodes.find(n => n.nodeId === this.props.nodeId);
            if (ctxNode) ctxNode.else_setup_code = fieldState.else_setup_code || null;
        }

        // Register the complement variable in the frontend variable context so
        // nodes in the ELSE branch can select it as their record source.
        if (fieldState.condition_tree_value?.cronMode) {
            const { variableName, modelName } = fieldState.condition_tree_value;
            if (variableName && modelName) {
                const complementName = `${variableName}_complement`;
                const complementId = `${this.props.nodeId}_complement`;
                const existingVars = this.env.variables.context.variables || [];
                const alreadyRegistered = existingVars.find(v => v.id === complementId);
                if (!alreadyRegistered) {
                    this.env.variables.setContext({
                        variables: [
                            ...existingVars,
                            owl.reactive({
                                id: complementId,
                                variable_name: complementName,
                                variable_type: 'recordset',
                                modelName: modelName,
                                modelId: modelName,
                                scopeId: this.props.nodeId,
                                usedIn: [],
                                class: this.buttonClass,
                            })
                        ]
                    });
                } else {
                    // Update variable name/model if the user changed the selection.
                    alreadyRegistered.variable_name = complementName;
                    alreadyRegistered.modelName = modelName;
                }
                this.env.bus.trigger("UPDATE-VARIABLE-STATE");
            }
        }

        await this.updateNode(fieldState, code);

        // Sync the newly saved fieldState back into the Drawflow editor's internal
        // node data. This ensures that editor.export() (called by saveData) uses
        // the latest configuration even if the flow hasn't been reloaded yet.
        //
        // Guard: this.env.editor is injected by WorkFlowAuto via useSubEnv as a
        // getter function (() => this.editor). We call it safely here. If for any
        // reason it is not available (e.g. component rendered outside the main
        // automation view), we skip the sync gracefully instead of throwing.
        try {
            const editor = typeof this.env.editor === 'function' ? this.env.editor() : null;
            const internalId = this.props.id; // Drawflow internal numeric ID passed as prop
            if (editor && internalId) {
                const node = editor.getNodeFromId(internalId);
                if (node && node.data.nodeId === this.props.nodeId) {
                    editor.updateNodeDataFromId(internalId, { ...node.data, ...fieldState, code });
                }
            }
        } catch (editorSyncErr) {
            // Non-critical: the data is already persisted to the DB via updateNode().
            // A failure here only means the in-memory Drawflow state isn't patched,
            // which will be corrected on the next reload.
            console.warn('Could not sync fieldState into Drawflow editor:', editorSyncErr);
        }

        this.updateVariableUsage(usedVariables);
        this.raiseNotification("Record Saved...!", "success");
    }

    getCurrentNodeContext() {
        const nodes = this.context?.nodes || [];
        return nodes.find((node) => node.nodeId === this.props.nodeId) || null;
    }

    resolveTriggerContext() {
        const globalContext = this.env.globalContext?.() || {};
        const normalizedGlobalTrigger = typeof globalContext.trigger === "string" ? globalContext.trigger : "";
        const normalizedGlobalTriggerType = typeof globalContext.triggerType === "string" ? globalContext.triggerType : "";

        if (normalizedGlobalTrigger || normalizedGlobalTriggerType) {
            return {
                trigger: normalizedGlobalTrigger,
                triggerType: normalizedGlobalTriggerType,
            };
        }

        let walker = this.getCurrentNodeContext();
        while (walker?.left) {
            const parent = walker.left;
            if (parent?.type === "action" || parent?.trigger_type || parent?.ttype) {
                return {
                    trigger: typeof parent.ttype === "string" ? parent.ttype : "",
                    triggerType: typeof parent.trigger_type === "string" ? parent.trigger_type : "",
                };
            }
            walker = parent;
        }

        return {
            trigger: "",
            triggerType: "",
        };
    }

    triggerName() {
        const { trigger, triggerType } = this.resolveTriggerContext();
        if (triggerType) {
            return triggerType.toLowerCase();
        }
        if (!trigger) {
            return "";
        }
        const [, triggerWord] = trigger.split(" ");
        return (triggerWord || trigger).toLowerCase();
    }

    allTriggerName() {
        const { trigger, triggerType } = this.resolveTriggerContext();
        return (trigger || triggerType || "").toLowerCase();
    }

    get isCustomTrigger() {
        const BUILTIN = new Set(['create', 'write', 'unlink', 'time', 'field_change', 'onchange']);
        return this.props.type === 'action' && !BUILTIN.has(this.props.trigger_type);
    }

    openTriggerEdit() {
        const functionId = this.props.model?.[0];
        if (functionId) {
            this.env.bus.trigger("OPEN:TRIGGER:EDIT", { functionId });
        }
    }

    deleteNode() {
        this.env.bus.trigger("DELETE:NODE:BY:CLICK", { nodeId: this.props.nodeId, });
    }

    get getVariables() {
        const getScopeIds = (node, nodeIds = [], visited = new Set()) => {
            if (!node || visited.has(node.nodeId)) return nodeIds;
            visited.add(node.nodeId);
            nodeIds.push(node.nodeId);
            if (node.left) {
                getScopeIds(node.left, nodeIds, visited);
            }
            return nodeIds;
        };

        const currentContext = this.context;
        const allVariables = this.variableContext.variables || [];
        let currentNode = currentContext.nodes.find(item => item.nodeId === this.props.nodeId);

        const scopeIds = getScopeIds(currentNode, []);
        const filteredVariables = allVariables.filter(variable => scopeIds.includes(variable.scopeId));

        return [...(this.env.globalVariables.context.variables || []), ...filteredVariables];
    }

    get context() {
        return this.env.context.context;
    }
    getIconSrc() {
        if (this.props.type !== 'action') {
            if (this.props.type == 'model') {
                return icons['Model']
            }
            const displayName = this.state.model.display_name;
            return icons[displayName] || '';
        }

        else {
            return icons['Action']
        }
    }
    get variableContext() {
        return this.env.variables.context;
    }

    get testStatusClass() {
        return {
            pending: '',
            running: 'cy-test-running',
            success: 'cy-test-success',
            error: 'cy-test-error',
            warning: 'cy-test-warning',
        }[this.state.testStatus] || '';
    }

    static template = xml`
        <div t-ref="root" t-attf-class="node-container {{this.state.findUsage ? 'cy-find-usage' : ''}}" style="position: relative">
            <t t-if="this.state.label">
                <div class="cy-w-info-node">
                    <span class="">
                        <t t-out="this.state.label"/>
                    </span>
                </div>
            </t>
            <div class="title-box d-flex align-items-center justify-content-center p-2 position-relative">
                 <span class="w-auto-node-icon">
                 <img t-att-src="getIconSrc()" draggable="false"/>

                 </span>
                <t t-if="state.model.display_name === 'Condition'">
                    Condition
                </t>
                <t t-else="">
                    <t t-out="state.model.display_name"/>
                </t>
                <span
                    t-if="props.type === 'action_to_do'"
                    class="settings-icon"
                    t-on-click="openConfigModal"
                >
                    <i class="ri-edit-2-fill"></i>
                </span>
                <span
                    t-if="isCustomTrigger"
                    class="settings-icon"
                    t-on-click="openTriggerEdit"
                >
                    <i class="ri-edit-2-fill"></i>
                </span>
                <div class="delete-icon position-absolute" t-on-click="deleteNode">
                    <i class="ri-close-line delete-icon" aria-hidden="true"></i>
                </div>
            </div>
            <div t-attf-class="cy-validation-tooltip {{this.state.error ? 'show' : ''}}">
                <span class="tooltip-text">
                    Not configured!
                </span>
            </div>
            <div t-if="this.state.testMessage" t-attf-class="cy-test-tooltip {{this.state.testStatus !== 'pending' ? 'show' : ''}}">
                <span class="tooltip-text">
                    <t t-esc="this.state.testMessage"/>
                </span>
            </div>
            <t t-if="state.model.display_name === 'Condition'">
                <div class="condition-tooltip-container">
                    <span>Success</span>
                    <span>Failed</span>
                    <span>Default</span>
                </div>
            </t>
            <t t-if="state.model.display_name === 'Try Catch'">
                <div class="condition-tooltip-container" style="right: -100%; top: -50%;">
                    <span>TRY Branch</span>
                    <span>CATCH Branch</span>
                    <span>Continue</span>
                </div>
            </t>
        </div>`;
}
