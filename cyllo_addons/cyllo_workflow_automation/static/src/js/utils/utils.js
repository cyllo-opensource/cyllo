/** @odoo-module */

export function removeNodeIdFromVariables(contextVariables, nodeId) {
    contextVariables.forEach(variable => {
        if (variable && variable.usedIn) {
            const index = variable.usedIn.indexOf(nodeId);
            if (index !== -1) {
                variable.usedIn.splice(index, 1);
            }
        }
    });
}

export async function settingInitialContext() {
    // Fetch all fields we need from node.struct for every node in this automation.
    // else_setup_code  - Condition cron complement OR Try Catch except header.
    // try_catch_error_variable / try_catch_error_types - needed to derive the
    //   except header on page-reload when else_setup_code wasn't stored yet.
    const codeArray = await this.orm.searchRead(
        "node.struct",
        [["work_auto_id", "=", this.id]],
        ["code", "else_setup_code", "try_catch_error_variable", "try_catch_error_types",
         "loop_variable_name", "loop_source_type", "loop_collection", "warning", "warning_type"]
    );

    // Guard: flow_data may be null on a brand-new workflow (no nodes saved yet).
    const homeData = this.editorValue[0]?.flow_data?.drawflow?.Home;
    const data = homeData?.data || null;
    const nodes = data ? Object.values(data) : [];

    const contextNodes = nodes.map(node => {
        const isParent = node.name === "Condition" || node.name === "Loop" || node.name === "Try Catch";
        const isLoop = node.name === "Loop";
        const isTryCatch = node.name === "Try Catch";
        const nodeStruct = codeArray.find(item => item.id === node.data.nodeId);
        const code = nodeStruct?.code || "";
        const type = nodeStruct?.type || node.data.type || "node";
        const trigger_type = nodeStruct?.trigger_type || node.data.trigger_type || null;
        const ttype = nodeStruct?.ttype || node.data.ttype || null;

        // Derive else_setup_code:
        // - For Try Catch: reconstruct from stored error variable + types if the
        //   DB value is empty (backwards-compat with records saved before this fix).
        // - For Condition cron nodes: use the stored value directly.
        let else_setup_code = nodeStruct?.else_setup_code || null;
        if (isTryCatch && !else_setup_code) {
            const errVar  = (nodeStruct?.try_catch_error_variable || 'error').trim();
            const errTypes = (nodeStruct?.try_catch_error_types || 'Exception').trim();
            const types = errTypes.split(',')
                .map(t => t.trim()).filter(Boolean).join(', ');
            const typesPart = types && types !== 'Exception' ? `(${types})` : (types || 'Exception');
            else_setup_code = `except ${typesPart} as ${errVar}:`;
        }

        return {
            nodeId: node.data.nodeId,
            parent: null,
            left: null,
            right: null,
            child1: isParent ? { left: null, right: null, code: "pass" } : null,
            child2: null,
            isParent,
            isLoop,
            isTryCatch,
            code,
            else_setup_code,
            type,
            trigger_type,
            ttype,
        };
    });

    contextNodes.forEach(node => {
        const dNode = nodes.find(item => item.data.nodeId === node.nodeId);
        if (dNode.outputs) {
            Object.entries(dNode.outputs).forEach(([outputName, output]) => {
                const connections = output.connections || [];
                if (connections.length > 0) {
                    const outputIdx = outputName.split('_')[1];
                    let propName = 'right';
                    if (node.isParent) {
                        propName = outputIdx === '3' ? 'right' : `child${outputIdx}`;
                    }

                    const targets = connections.map(conn => {
                        const targetDNode = nodes.find(item => item.id == conn.node);
                        return targetDNode ? contextNodes.find(item => item.nodeId === targetDNode.data.nodeId) : null;
                    }).filter(Boolean);

                    if (targets.length > 0) {
                        node[propName] = targets.length === 1 ? targets[0] : targets;
                    }
                }
            });
        }

        if (dNode.inputs?.input_1?.connections?.length > 0) {
            const inputId = dNode.inputs.input_1.connections[0].node;
            const inPutNode = nodes.find(item => item.id == inputId);
            if (inPutNode) {
                const inPutNodeCtx = contextNodes.find((item => item.nodeId === inPutNode.data.nodeId));
                node.left = inPutNodeCtx || null;
            }
        }
    });

    this.env.context.setContext({ nodes: [...contextNodes] });

    // ── Bug 4 fix: re-register Try Catch error variables after page reload ────
    // On reload onConfirm never fires, so we must seed env.variables here.
    const existingVars = this.env.variables.context.variables || [];
    const newVars = [];
    const BUTTON_CLASSES = ['btn-info', 'btn-primary', 'btn-warning', 'btn-secondary', 'btn-success', 'btn-danger'];

    nodes.forEach(node => {
        if (node.name !== 'Try Catch') return;
        const nodeId = node.data.nodeId;
        const nodeStruct = codeArray.find(item => item.id === nodeId);
        const rawVarName = (nodeStruct?.try_catch_error_variable || '').trim();
        if (!rawVarName) return;

        // Bug 1 fix: register as var_<name> so processValue("variable") output
        // (which emits "var_<varName>") matches the Python variable name generated
        // by traverse(). The except clause writes "except ... as <rawVarName>:"
        // which means we also need to store var_<rawVarName> as the Python identifier.
        // We handle this by keeping the raw except clause name (no var_ prefix) in
        // else_setup_code and exposing the var_ prefixed version to UI pickers.
        const varId = `${nodeId}_error`;
        const alreadyRegistered = existingVars.find(v => v.id === varId);
        const displayVarName = `var_${rawVarName}`;

        if (alreadyRegistered) {
            alreadyRegistered.variable_name = displayVarName;
        } else {
            const randomClass = BUTTON_CLASSES[Math.floor(Math.random() * BUTTON_CLASSES.length)];
            newVars.push(owl.reactive({
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
            }));
        }
    });

    if (newVars.length > 0) {
        this.env.variables.setContext({ variables: [...existingVars, ...newVars] });
        this.env.bus.trigger("UPDATE-VARIABLE-STATE");
    }

    // Re-register loop iteration variables after page reload.
    // On reload, onConfirm never fires so loop variables disappear from env.variables.
    // We reconstruct them from the saved loop_variable_name field, and look up the
    // model from ir.model.fields using loop_collection (for field-based loops).
    const loopNodes = nodes.filter(node => node.name === 'Loop');
    if (loopNodes.length > 0) {
        const loopVarsToAdd = [];
        const currentVars = this.env.variables.context.variables || [];

        for (const loopNode of loopNodes) {
            const nodeId = loopNode.data.nodeId;
            const nodeStruct = codeArray.find(item => item.id === nodeId);
            const loopVarName = (nodeStruct?.loop_variable_name || '').trim();
            if (!loopVarName) continue;

            const varId = `loop_var_${nodeId}`;
            const alreadyRegistered = currentVars.find(v => v.id === varId);

            let modelId = null;
            let modelName = null;

            if (nodeStruct?.loop_source_type === 'field' && nodeStruct?.loop_collection && this.state.model_id) {
                // Resolve relation model from field metadata
                try {
                    const fieldData = await this.orm.searchRead(
                        "ir.model.fields",
                        [['model_id', '=', this.state.model_id], ['name', '=', nodeStruct.loop_collection]],
                        ['relation']
                    );
                    if (fieldData && fieldData.length > 0 && fieldData[0].relation) {
                        modelName = fieldData[0].relation;
                        const modelData = await this.orm.searchRead(
                            "ir.model",
                            [['model', '=', modelName]],
                            ['id']
                        );
                        if (modelData && modelData.length > 0) {
                            modelId = modelData[0].id;
                        }
                    }
                } catch (_e) {
                    // Non-critical: model info stays null if lookup fails
                }
            } else if (nodeStruct?.loop_source_type === 'variable' && nodeStruct?.loop_collection) {
                // Source is a variable — find its model info from existing vars
                const sourceVar = currentVars.find(v => v.id === nodeStruct.loop_collection);
                if (sourceVar) {
                    modelId = sourceVar.modelId || null;
                    modelName = sourceVar.modelName || null;
                }
            }

            if (alreadyRegistered) {
                alreadyRegistered.variable_name = loopVarName;
                if (modelId) alreadyRegistered.modelId = modelId;
                if (modelName) alreadyRegistered.modelName = modelName;
            } else {
                const randomClass = BUTTON_CLASSES[Math.floor(Math.random() * BUTTON_CLASSES.length)];
                loopVarsToAdd.push(owl.reactive({
                    id: varId,
                    variable_name: loopVarName,
                    variable_type: 'record',
                    modelId,
                    modelName,
                    scopeId: nodeId,
                    usedIn: [],
                    class: randomClass,
                }));
            }
        }

        if (loopVarsToAdd.length > 0) {
            const latest = this.env.variables.context.variables || [];
            this.env.variables.setContext({ variables: [...latest, ...loopVarsToAdd] });
            this.env.bus.trigger("UPDATE-VARIABLE-STATE");
        }
    }

    const warningNodes = nodes.filter(node => node.name === 'Warning');
    warningNodes.forEach(node => {
        const nodeId = node.data.nodeId;
        const nodeStruct = codeArray.find(item => item.id === nodeId);
        if (nodeStruct?.warning_type === 'error' && nodeStruct?.warning) {
            this.updateImportStatements({
                parent: 'from odoo.exceptions import',
                child: nodeStruct.warning,
                nodeId,
            });
        }
    });
}