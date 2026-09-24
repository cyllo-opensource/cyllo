/** @odoo-module */
import {Many2XAutocomplete} from "@web/views/fields/relational_utils";
import {registry} from '@web/core/registry';
import {useService} from "@web/core/utils/hooks";
import {Many2OneField} from "@web/views/fields/many2one/many2one_field";

const {
    useState,
    onWillStart,
    Component,
    onMounted,
    useRef,
    App,
    useEffect,
    onWillUnmount
} = owl;
import {useSaveContext} from './useSaveContext'
import {ModelComponent} from "./workflow_nodes";
import {Record} from "@web/model/record";
import Context from "./context";
import {variableFields} from "./fields.js";
import {VariableNode} from "./components/variableNode/variableNode.js";
import {
    Many2ManyTagsField
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import {_t} from "@web/core/l10n/translation";
import {jsonrpc} from "@web/core/network/rpc_service";
import {ConfirmationPopup} from "@cyllo_web/js/popups/popups";
import {PYTHON_KEYWORDS} from "./components/Assists/utils/utils";
import {FoldOut} from "./automationComponents/FoldOut/FoldOut";
import {VariableItem} from "./automationComponents/VariableItem/VariableItem";
import {
    VariableDetails
} from "./automationComponents/VariableDetails/VariableDetails";
import {removeNodeIdFromVariables, settingInitialContext} from "./utils/utils"
import {CustomTrigger} from "./components/customTriggers/customTriggers";
import {WorkPager} from "./components/Assists/workPager/workPager";
import {SaveLoading} from "./components/Assists/effect/saveLoading/saveLoading";
import {TestResultPanel} from "./components/testResultPanel/testResultPanel";
import {HistoryManager} from "./utils/historyManager";
import {cloneState} from "./utils/stateClone";

const BUTTON_CLASSES = [
    'btn-info', 'btn-primary', 'btn-warning', 'btn-secondary', 'btn-success', 'btn-danger'
]

const AUTO_OPEN_CONFIG_FIELDS = {
    Warning: ['label', 'warning_text', 'notification_title', 'notification_type'],
    Search: ['label', 'search_variable', 'search_domain_tree', 'search_domain'],
    Create: ['label', 'search_variable', 'create_required_field', 'create_tree_fields_values', 'create_model_field_value'],
    Write: ['label', 'write_selected_record', 'write_field_value'],
    'Button Click': ['label', 'function_name', 'function_record', 'function_args'],
    Code: ['label', 'code_code', 'code'],
    Mail: ['label', 'mail_record', 'mail_to', 'mail_subject', 'mail_body', 'mail_template'],
    SMS: ['label', 'sms_record', 'sms_partner_ids', 'sms_message', 'sms_template'],
    WhatsApp: ['label', 'wa_record', 'wa_partner_path', 'wa_free_message', 'wa_template'],
    Follower: ['label', 'followers', 'follower_record'],
    Activity: ['label', 'activity_record', 'activity_summary', 'activity_user', 'activity_deadline', 'activity_type'],
    Condition: ['label', 'condition_tree_value', 'else_setup_code'],
    Loop: ['label', 'loop_collection', 'loop_variable_name'],
    'Reuse Automation': ['label', 'reused_work_auto_id', 'reused_variable'],
    Window: ['label', 'window_action_id'],
    Duplicate: ['label', 'duplicate_record', 'duplicate_field_overrides'],
    Webhook: ['label', 'webhook_url', 'webhook_method', 'webhook_headers', 'webhook_payload', 'webhook_actions'],
    'Try Catch': ['label', 'try_catch_error_variable', 'try_catch_error_types'],
};

const GLOBAL_IMPORTS = [{
    "childStatement": [
        {
            "statement": "fields"
        }
    ],
    "importStatement": "from odoo import"
}, {
    "childStatement": [
        {
            "statement": "request"
        }
    ],
    "importStatement": "from odoo.http import"
}]

function errorVibration() {
    if ('vibrate' in navigator) {
        // Try to vibrate
        navigator.vibrate([100, 50, 100]);
        // Check if vibration actually occurred
        setTimeout(() => {
            if (navigator.vibrate && !navigator.vibrate(0)) {
            } else {
                // fallbackVibration();
            }
        }, 300);
    } else {
        // fallbackVibration();
    }
}

function playErrorSound() {
    return new Promise((resolve) => {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();

        // Use a triangle wave for a softer but still distinctive sound
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(440, audioCtx.currentTime); // Start at A4

        // Reduce the gain for lower volume
        gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);

        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        oscillator.start();

        // Subtle frequency modulation
        oscillator.frequency.exponentialRampToValueAtTime(330, audioCtx.currentTime + 0.2); // Drop to E4
        oscillator.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.4); // Back to A4

        setTimeout(() => {
            oscillator.stop();
            resolve();
        }, 500);
    });
}


export class WorkFlowAuto extends Component {

    setup() {
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.action = useService("action");
        this.uiService = useService("ui");
        this.menuService = useService("menu");
        this.restoreCurrentApp();
        this.data = {};
        this.nodeApps = new Map();
        owl.useSubEnv({
            globalContext: this.getContext.bind(this),
            // Expose the Drawflow editor instance as a lazy getter function.
            // Child components (e.g. ModelComponent.onConfirm) call this.env.editor()
            // AFTER the editor is initialised in onMounted. Using a function reference
            // (not the value directly) avoids the "editor is undefined" race condition
            // at useSubEnv call time (which runs in setup(), before onMounted).
            editor: () => this.editor,
            canvasBusy: (...args) => this.withCanvasBusy(...args),
            context: new Context({}),
            variables: new Context({}),
            globalVariables: new Context({
                variables: [
                    owl.reactive({
                        id: "global/variable/current/rec",
                        variable_name: "current_record",
                        variable_value: "records",
                        variable_type: "record"
                    }),
                ]
            })
        })


        this.env.bus.addEventListener("UPDATE-CODE", this.updateCode.bind(this));
        this.env.bus.addEventListener("UPDATE-VARIABLE-STATE", () => {
            this.state.variables = [...(this.env.variables.context.variables || [])]
        });

        this.env.bus.addEventListener("OPEN:TRIGGER:EDIT", ({detail}) => {
            this.state.editTriggerId = detail.functionId;
            this.state.customTrigger = true;
        });

        this.env.bus.addEventListener("DELETE:NODE:BY:CLICK", ({detail}) => {
            const data = this.getCurrentFlowData();
            if (!Object.keys(data).length) {
                return;
            }
            const node = Object.values(data).find(item => item.data?.nodeId === detail.nodeId);
            if (node && owl.status(this) !== 'destroyed') {
                this.deleteNode(node);
            }
        });

        this.state = useState({
            actions: [],
            model_id: 0,
            model: '',
            secondary_model: "",
            sec_model_id: "",
            nodeDetails: [],
            modelState: [],
            selectedNodeID: undefined,
            variables: [],
            code: "",
            imports: [],
            block: true,
            modelSelectable: false,
            trigger: "",
            other_blk: false,
            name: "",
            nameError: false,
            selectedVariable: undefined,
            customTrigger: false,
            editTriggerId: null,
            recordList: [],
            saveLoading: false,
            // Cron schedule fields (used when trigger is time-based)
            cronMode: '',
            cronTime: 0,
            cronDay: 1,
            cronMonth: 1,
            cronWeekday: '0',
            // Reusable flag: marks this automation as callable from Reuse Automation nodes
            isReusable: false,
            // Generic reusable: no fixed model, accepts any record from calling workflow
            isGenericReusable: false,
            triggerType: "",
            // Field change fields (used when trigger is field_change)
            watchedFieldId: false,
            watchedFieldName: "",
            canUndo: false,
            canRedo: false,
            hasWhatsappModule: false,
            testRunning: false,
            testResult: null,
            runNowLoading: false,
            zoomPercent: 100,
            canvasBusy: false,
            canvasBusyMessage: "",
        })

        this.branchInputMap = {};
        this.connectionBranchMap = {};
        this.branchDefaultPrefix = "branch";
        this.history = new HistoryManager(100);
        this.isRestoring = false;
        this.refreshWhatsappModuleVisibility = async () => {
            this.state.hasWhatsappModule = await this.checkModuleInstalled('cyllo_whatsapp');
        };

        this.initialLoad = true;
        this.testResetTimer = null;
        this.testAnimationRunId = 0;
        this.activeTestConnections = new Set();
        this.completedTestConnections = new Set();
        this.canvasPanFrame = null;
        this.pendingCanvasPan = {x: 0, y: 0};
        this.canvasFocusFrame = null;
        this.initialViewport = null;
        this.handleWindowClickForTestReset = this.onWindowClickForTestReset.bind(this);
        this.handleCanvasWheel = this.onCanvasWheel.bind(this);
        this.handleKeyDown = this.onKeyDown.bind(this);
        const saveContext = useSaveContext();
        this.saveManually = saveContext.saveManually;
        this.id = saveContext.id;
        this.editorState = useState({
            value: []
        });
        this.drawBoardState = useState({
            edit: true,
        });
        this.mainBtn = useRef("mainBtn");
        this.root = useRef("root");
        this.drawBoard = useRef("drawBoard");
        this.inputNameRef = useRef("inputNameRef")
        this.mainBlk = useRef("mainBlk");

        useEffect((value) => {
            if (value) {
                !this.initialLoad && this.write({
                    variables: this.getSerializableVariables(),
                    imports: this.getSerializableImports()
                });
                this.initialLoad = false;
            }
        }, () => [this.state.variables, this.imports]);

        useEffect((modelId) => {
            const cur_rec = this.env.globalVariables.context.variables.find(item => item.variable_name === "current_record")
            cur_rec.modelId = this.state.model_id;
            cur_rec.modelName = this.state.model_name;
        }, () => [this.state.model_id, this.state.model_name])

        useEffect((nodeId) => {
            this.state.block = true;
//  if (nodeId) {
//      if (this.currentNode.data.type === "action_to_do") this.state.block = false;
//  }
        }, () => [this.state.selectedNodeID])

        useEffect(() => {
            this.env.bus.trigger("TOGGLE_NAVBAR:HIDE", {show: false})
            return () => {
                this.env.bus.trigger("TOGGLE_NAVBAR:HIDE", {show: true})
            }
        });

        onWillStart(async () => {
            await this.refreshWhatsappModuleVisibility();
            this.state.recordList = await this.orm.search("work.auto", [])
            this.state.actions = await this.orm.searchRead('work.function', [], ['name', 'id', 'icon', 'model_id', 'func_name', 'trigger_type'])
            const recordId = this.id;
            if (recordId) {
                const data = await this.orm.read('work.auto', [recordId], ['name', 'variables', 'imports', 'code', 'trigger_type', 'is_reusable', 'reuse_scope']);
                if (data.length > 0) {
                    let [{
                        name,
                        variables,
                        imports,
                        code,
                        trigger_type,
                        is_reusable,
                        reuse_scope
                    }] = data

                    imports = imports || GLOBAL_IMPORTS

                    this.state.variables = variables ? variables : [];
                    this.state.name = name;
                    this.state.imports = [...imports];
                    this.state.code = code;
                    this.state.triggerType = trigger_type || "";
                    this.state.isReusable = Boolean(is_reusable);
                    this.state.isGenericReusable = Boolean(is_reusable && reuse_scope === 'generic');
                    this.env.variables.setContext({variables: [...this.state.variables]});
                }
            } else {
                this.state.imports = [...GLOBAL_IMPORTS];
            }
            await this.loadData();
            await this.setModelState();
            await settingInitialContext.call(this);

            if (this.editorState.value.length > 0 && this.editorState.value[0].flow_data) {
                Object.entries(this.editorState.value[0].flow_data.drawflow?.Home?.data || {}).forEach(([key, value]) => {
                    if (value.data.ttype) {
                        this.state.trigger = value.data.ttype
                    }
                    if (value.data.trigger_type) {
                        this.state.triggerType = value.data.trigger_type;
                    }
                });
            }

            if (recordId) {
                // Load cron schedule fields so the inline panel shows existing values
                const cronData = await this.orm.read('work.auto', [recordId],
                    ['time_trigger_mode', 'time_trigger_time', 'time_trigger_day', 'time_trigger_month', 'time_trigger_weekday']);
                if (cronData.length) {
                    const {
                        time_trigger_mode,
                        time_trigger_time,
                        time_trigger_day,
                        time_trigger_month,
                        time_trigger_weekday
                    } = cronData[0];
                    this.state.cronMode = time_trigger_mode || '';
                    this.state.cronTime = time_trigger_time || 0;
                    this.state.cronDay = time_trigger_day || 1;
                    this.state.cronMonth = time_trigger_month || 1;
                    this.state.cronWeekday = time_trigger_weekday || '0';
                }

                // Load watched field for field_change workflows
                const fieldChangeData = await this.orm.read('work.auto', [recordId], ['field_id']);
                if (fieldChangeData.length && fieldChangeData[0].field_id) {
                    const [id, name] = fieldChangeData[0].field_id;
                    this.state.watchedFieldId = id;
                    this.state.watchedFieldName = name;
                }
            }

            this.env.bus.trigger("onclickMenuBar", {isCollapse: true})
            window.addEventListener('keydown', this.handleKeyDown);
        });

        onWillUnmount(() => {
            window.removeEventListener('keydown', this.handleKeyDown);
            this.destroyNodeApps();
            window.removeEventListener('focus', this.refreshWhatsappModuleVisibility);
            window.removeEventListener('click', this.handleWindowClickForTestReset);
            if (this.drawBoard?.el) {
                this.drawBoard.el.removeEventListener('wheel', this.handleCanvasWheel);
            }
            if (this.testResetTimer) {
                clearTimeout(this.testResetTimer);
            }
            if (this.canvasPanFrame) {
                cancelAnimationFrame(this.canvasPanFrame);
            }
            if (this.canvasFocusFrame) {
                cancelAnimationFrame(this.canvasFocusFrame);
            }
        });

        onMounted(async () => {
            window.addEventListener('focus', this.refreshWhatsappModuleVisibility);
            const globalVariables = await this.getGlobalVariables()
            this.env.globalVariables.setContext({variables: [...this.env.globalVariables.context.variables, ...globalVariables]});
            this.inputNameRef.el.focus();
            this.uiService.block();
            setTimeout(() => {
                if (owl.status(this) !== "destroyed") {
                    this.uiService.unblock()
                }
            }, 1000);

            const preRender = (component, props, options) => {
                return {
                    component, props, options
                };
            };

            const renderFunc = (obj, ref) => {
                const {component, props, options} = obj;
                this.state.nodeDetails.push({...obj, ref});
                this.data = {...obj, ref};
            };
            const owlC = {version: 3, h: preRender, render: renderFunc};
            this.editor = new Drawflow(this.drawBoard.el, owlC);
            this.drawBoard.el.addEventListener('wheel', this.handleCanvasWheel, {passive: false});

            this.editor.contextmenu = (e) => {
                if (
                    this.editor.dispatch("contextmenu", e),
                        e.preventDefault(),
                    "fixed" === this.editor.editor_mode || "view" === this.editor.editor_mode
                ) {
                    return false;
                }

                if (this.editor.precanvas.getElementsByClassName("drawflow-delete").length) {
                    this.editor.precanvas.getElementsByClassName("drawflow-delete")[0].remove();
                }

                if (this.editor.connection_selected && this.editor.connection_selected.parentElement.classList.length > 1) {
                    const deleteDiv = document.createElement("div");
                    deleteDiv.classList.add("drawflow-delete", "ri-delete-bin-6-line");
                    // deleteDiv.innerHTML = "x";
                    const precanvasRect = this.editor.precanvas.getBoundingClientRect();
                    const precanvasHeight = this.editor.precanvas.clientHeight / (this.editor.precanvas.clientHeight * this.editor.zoom);
                    const precanvasWidth = this.editor.precanvas.clientWidth / (this.editor.precanvas.clientWidth * this.editor.zoom);

                    deleteDiv.style.top = `${e.clientY * precanvasHeight - precanvasRect.y * precanvasHeight}px`;
                    deleteDiv.style.left = `${e.clientX * precanvasWidth - precanvasRect.x * precanvasWidth}px`;
                    this.editor.precanvas.appendChild(deleteDiv);
                }

            }

            this.isRestoring = true;
            try {
                if (this.editorState.value[0] && this.editorState.value[0].flow_data) {
                    this.registerNodes();
                    this.editor.start();
                    this.manageData();
                    this.rebuildBranchConnections();

                    // Critical: Initialize history with the loaded state directly from the database
                    // to ensure S0 (initial state) is never empty or corrupted.
                    const initialState = cloneState({
                        drawflow: this.editorState.value[0].flow_data,
                        variables: this.state.variables,
                        context: this.env.context.context,
                        imports: this.state.imports,
                    });
                    this.history.init(initialState);
                } else {
                    this.editor.start();
                    this.rebuildBranchConnections();
                    this.history.init(this.getHistorySnapshot());
                }
                this.updateHistoryState();
            } finally {
                this.isRestoring = false;
            }

            this.editor.on('nodeRemoved', async (id) => {
                this.state.selectedNodeID = undefined;
                this.destroyNodeApps(true);
                const flowData = this.editor.drawflow.drawflow.Home.data;
                const node = Object.values(flowData).find(node => node.id === +id);
                if (this._pendingNodeRemoval?.has(+id)) {
                    const nodeId = this._pendingNodeRemoval.get(+id);
                    this._pendingNodeRemoval.delete(+id);
                    this.env.context.deleteNode(nodeId);
                } else if (node) {
                    this.env.context.deleteNode(node.data.nodeId);
                    this.removeVariables(node.data.nodeId);
                    this.removeImports(node.data.nodeId);
                    this.removeNodeIdFromVariables(node.data.nodeId);
                    await this.orm.unlink("node.struct", [node.data.nodeId]);
                }
                this.saveHistory();
                await this.autoSaveDrawFlow();
                this.rebuildBranchConnections();
            });

            this.editor.on('nodeCreated', async (id) => {
                this.contextUpdateNodeCreation(id);
                this.saveHistory();
                await this.autoSaveDrawFlow();
            });

            this.editor.on('nodeMoved', async (id) => {
                this.saveHistoryDebounced();
                if (this.moveDbTimeout) clearTimeout(this.moveDbTimeout);
                this.moveDbTimeout = setTimeout(async () => {
                    await this.autoSaveDrawFlow();
                }, 1000);
            });
            this.editor.on('connectionCreated', async (data) => {
                const {input_class, input_id, output_class, output_id} = data;
                const inputId = +input_id;
                const outputId = +output_id;

                if (!this.canConnect(inputId, outputId, output_class)) {
                    this.editor.removeSingleConnection(outputId, inputId, output_class, input_class, true);
                    return;
                }
                this.contextUpdateConnection(data, true);
                this.saveHistory();
                await this.autoSaveDrawFlow();
                const node = Object.values(this.editor.drawflow.drawflow.Home.data).find(
                    (item) => item.id === parseInt(input_id)
                );
                if (node && (node.data.name === 'Webhook' || node.data.name === 'Try Catch' || await this.shouldAutoOpenConfigModal(node))) {
                    const name = node.data.name;
                    const nodeId = node.data.nodeId;
                    this.env.bus.trigger("OPEN:MODAL", {name, nodeId});
                }
            });

            this.editor.on('connectionRemoved', async (data) => {
                this.contextUpdateConnection(data, false)
                this.saveHistory();
                await this.autoSaveDrawFlow();
            });

            this.editor.on('zoom', () => {
                // Drawflow's own wheel/pinch handling on the canvas (ctrl-scroll,
                // trackpad pinch) changes editor.zoom directly without going
                // through our zoomIn()/zoomOut() wrappers, so the displayed
                // percentage only stayed in sync when the +/- buttons were used.
                this._updateZoomPercent();
            });

            this.editor.on('nodeSelected', (id) => {
                this.state.selectedNodeID = id;
            });

            this.editor.on('nodeUnselected', (val) => {
                this.state.selectedNodeID = undefined
            });

            this.editor.on('keydown', (e) => {
                if (e.key === "Delete") {
                    if (this.currentNode) {
                        this.deleteNode(this.currentNode);
                    }
                }
            });

        })
    }

    async checkModuleInstalled(moduleName) {
        try {
            const count = await this.orm.searchCount('ir.module.module', [
                ['name', '=', moduleName],
                ['state', '=', 'installed'],
            ]);
            return count > 0;
        } catch {
            return false;
        }
    }

    _hasSavedConfigValue(value) {
        if (value === null || value === undefined || value === false) {
            return false;
        }
        if (typeof value === 'string') {
            const trimmed = value.trim();
            return trimmed !== '' && trimmed !== '[]' && trimmed !== '{}' && trimmed !== 'null';
        }
        if (Array.isArray(value)) {
            return value.length > 0;
        }
        if (typeof value === 'object') {
            return Object.keys(value).length > 0;
        }
        return true;
    }

    async shouldAutoOpenConfigModal(node) {
        if (!node?.data?.nodeId || node.data.type !== 'action_to_do') {
            return false;
        }

        const configFields = AUTO_OPEN_CONFIG_FIELDS[node.data.name];
        if (!configFields?.length) {
            return true;
        }

        try {
            const [savedNode] = await this.orm.read('node.struct', [node.data.nodeId], configFields);
            if (!savedNode) {
                return true;
            }
            return !configFields.some((fieldName) => this._hasSavedConfigValue(savedNode[fieldName]));
        } catch (error) {
            console.warn('Could not determine whether node is already configured:', error);
            return true;
        }
    }

    removeNodeIdFromVariables(nodeId) {
        const contextVariables = this.env.variables.context.variables
        removeNodeIdFromVariables(contextVariables, nodeId);
    }

    async getGlobalVariables() {
        const models = ["res.users", "res.company"]
        const modelData = await this.orm.searchRead("ir.model", [["model", "in", models]], ["model"])
        const variables = modelData.map(item => {
            if (item.model === "res.users") {
                return {
                    id: "global/variable/current/user",
                    variable_name: "current_user",
                    modelId: item.id,
                    modelName: item.model,
                    variable_type: "record",
                    variable_value: "env.user"
                }
            } else if (item.model === "res.company") {
                return {
                    id: "global/variable/current/company",
                    variable_name: "current_company",
                    modelId: item.id,
                    modelName: item.model,
                    variable_type: "record",
                    variable_value: "env.company"
                }
            }
        })
        const dateVars = [
            {
                id: "global/variable/current/date",
                variable_name: "current_date",
                variable_type: "date",
                variable_value: "fields.date.today()"
            },
            {
                id: "global/variable/current/datetime",
                variable_name: "current_datetime",
                variable_type: "datetime",
                variable_value: "fields.Datetime.now()"
            },
        ]
        return [...variables, ...dateVars];
    }

    get recordList() {
        return this.state.recordList
    }

    get currentRecord() {
        return this.id || 0;
    }

    /** True when at least one trigger fires on a field-value change. */
    get isFieldChangeTrigger() {
        return this.usedTriggerTypes.includes('field_change');
    }

    /**
     * True when at least one trigger is time-based.
     * Used by the XML template to hide Create/Write blocks and show the
     * inline Cron Schedule configuration panel.
     */
    get isTimeTrigger() {
        return this.usedTriggerTypes.includes('time');
    }

    get model_blk() {
        // Generic reusable automations don't need a model -- never show the glow prompt
        if (this.state.isGenericReusable) return false;
        const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
        const modelNode = Object.values(flowData).find(node => node.data?.type === "model");
        return !modelNode;
    }

    get trigger_blk() {
        // Generic reusable automations: triggers are always available (no model node needed)
        if (this.state.isGenericReusable) return true;
        const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
        const modelNode = Object.values(flowData).find(node => node.data?.type === "model");
        return !!modelNode;
    }

    get other_blk() {
        // For generic reusable: enable as soon as any node exists
        if (this.state.isGenericReusable) {
            const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
            return Object.keys(flowData).length > 0;
        }
        // For normal automations: enable Builtin/Logic/Functional blocks as soon as
        // the model node is placed (same condition as trigger_blk).
        // This lets users place "Reuse Automation" or any action node immediately
        // after selecting the model, without needing to add a trigger node first.
        const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
        const modelNode = Object.values(flowData).find(node => node.data?.type === "model");
        return !!modelNode;
    }

    getNodeBranchId(node) {
        if (!node || !node.data) return null;
        if (node.data.branchId) {
            return node.data.branchId;
        }
        const branchIds = node.data.branchIds || [];
        if (branchIds.length) {
            return branchIds[0];
        }
        return `${this.branchDefaultPrefix}-${node.data.nodeId}`;
    }

    assignNodeBranch(node, branchId) {
        if (!node || !branchId) return;
        const branchIds = node.data.branchIds || [];
        if (!branchIds.includes(branchId)) {
            branchIds.push(branchId);
        }
        node.data.branchIds = branchIds;
        node.data.branchId = branchId;
    }

    removeNodeBranch(node, branchId) {
        if (!node || !branchId || !node.data.branchIds) return;
        const filtered = node.data.branchIds.filter(id => id !== branchId);
        if (filtered.length) {
            node.data.branchIds = filtered;
            node.data.branchId = filtered[0];
        } else {
            delete node.data.branchIds;
            delete node.data.branchId;
        }
    }

    recordBranchConnection(branchId, inputId) {
        const key = Number(inputId);
        if (!this.branchInputMap[key]) {
            this.branchInputMap[key] = new Set();
        }
        this.branchInputMap[key].add(branchId);
        this.connectionBranchMap[`${branchId}-${key}`] = true;
    }

    removeBranchConnection(branchId, inputId) {
        const key = Number(inputId);
        const set = this.branchInputMap[key];
        if (set) {
            set.delete(branchId);
            if (!set.size) {
                delete this.branchInputMap[key];
            }
        }
        delete this.connectionBranchMap[`${branchId}-${key}`];
    }

    rebuildBranchConnections() {
        this.branchInputMap = {};
        this.connectionBranchMap = {};
        const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
        Object.values(flowData).forEach(node => {
            const outputs = node.outputs || {};
            Object.values(outputs).forEach(output => {
                const connections = output.connections || [];
                connections.forEach(connection => {
                    const inputNode = Object.values(flowData).find(item => item.id === connection.node);
                    if (!inputNode) return;
                    const branchId = this.getNodeBranchId(node);
                    this.assignNodeBranch(node, branchId);
                    this.assignNodeBranch(inputNode, branchId);
                    this.recordBranchConnection(branchId, connection.node);
                });
            });
        });
    }

    get usedTriggerFunctionIds() {
        const data = this.editorValue?.[0]?.flow_data?.drawflow?.Home?.data || {};
        const ids = [];
        Object.values(data).forEach(node => {
            const modelInfo = node.data?.model;
            if (node.data?.type === 'action' && Array.isArray(modelInfo) && modelInfo[0]) {
                ids.push(modelInfo[0]);
            }
        });
        return [...new Set(ids)];
    }

    get usedTriggerTypes() {
        const data = this.editorValue?.[0]?.flow_data?.drawflow?.Home?.data || {};
        const types = [];
        Object.values(data).forEach(node => {
            const triggerType = node.data?.trigger_type;
            if (node.data?.type === 'action' && triggerType) {
                types.push(triggerType);
            }
        });
        return [...new Set(types)];
    }

    get builtinTriggerActionIds() {
        const ids = {};
        const builtins = ['create', 'write', 'unlink'];
        (this.state.actions || []).forEach(action => {
            const funcName = (action?.func_name || "").toLowerCase();
            if (builtins.includes(funcName) && !ids[funcName]) {
                ids[funcName] = action.id;
            }
        });
        return ids;
    }

    get triggerActions() {
        return (this.state.actions || []).filter(action => {
            const funcName = (action?.func_name || "").toLowerCase();
            return funcName !== 'loop';
        });
    }

    get usedTriggerNames() {
        const ids = this.usedTriggerFunctionIds;
        if (!ids.length) {
            return [];
        }
        return this.state.actions
            .filter(action => ids.includes(action.id))
            .map(action => action.name);
    }

    isTriggerUsed(action) {
        if (this.usedTriggerFunctionIds.includes(action.id)) {
            return true;
        }
        if (action.trigger_type && this.usedTriggerTypes.includes(action.trigger_type)) {
            return true;
        }
        return false;
    }

    /**
     * Write a single cron schedule field to work.auto and keep the local
     * state in sync.  The backend write() override calls create_cron()
     * automatically, so no extra RPC is needed.
     *
     * @param {string} field  - one of: time_trigger_mode/time/day/month/weekday
     * @param {*}      value  - the new value
     */
    async setCronField(field, value) {
        const stateKey = {
            time_trigger_mode: 'cronMode',
            time_trigger_time: 'cronTime',
            time_trigger_day: 'cronDay',
            time_trigger_month: 'cronMonth',
            time_trigger_weekday: 'cronWeekday',
        }[field];
        if (stateKey) this.state[stateKey] = value;
        await this.orm.write('work.auto', [this.id], {[field]: value});
    }

    /**
     * Handler for Many2XAutocomplete update on the "Field to Watch" picker.
     * When the user picks from the inline dropdown, selection[0] contains
     * { id, display_name }. When the user picks via "Search More" dialog,
     * Odoo returns { id, name } without display_name.
     * We normalise both cases before delegating to setWatchedField.
     *
     * @param {Array} selection - array of selected record objects from Many2XAutocomplete
     */
    async onWatchedFieldSelect(selection) {
        if (!selection || !selection[0]) {
            await this.setWatchedField(false, '');
            return;
        }
        const record = selection[0];
        const fieldId = record.id;
        // display_name is present for inline dropdown picks;
        // for Search More picks Odoo only populates `name`.
        let fieldName = record.display_name || record.name || '';
        if (!fieldName && fieldId) {
            // Fallback: read from ORM to get the correct display name
            const data = await this.orm.searchRead(
                'ir.model.fields',
                [['id', '=', fieldId]],
                ['display_name', 'field_description']
            );
            fieldName = data[0]?.display_name || data[0]?.field_description || '';
        }
        await this.setWatchedField(fieldId, fieldName);
    }

    /**
     * Saves the selected watched field to work.auto.
     * `current_record` in the global variables context already represents the
     * triggering record, so no extra variable registration is needed.
     *
     * @param {number} fieldId   - id of the selected ir.model.fields record
     * @param {string} fieldName - user-visible field name / label
     */
    async setWatchedField(fieldId, fieldName) {
        this.state.watchedFieldId = fieldId || false;
        this.state.watchedFieldName = fieldName || "";
        await this.orm.write('work.auto', [this.id], {field_id: fieldId || false});
    }

    deleteNode(node) {
        if (!node || !node.data) {
            return;
        }
        const variablesInScope = (this.env.variables.context.variables || []).filter(variable => variable.scopeId === node.data.nodeId);
        const isUsed = variablesInScope.some(item =>
            item.usedIn.length > 1 || (item.usedIn.length === 1 && item.usedIn[0] !== node.data.nodeId)
        );
        if (isUsed) {
            const message = "You can't delete the node. Because the variables with in this scope is used in some other nodes.";
            this.dialogService.add(ConfirmationPopup, {
                title: "Oops!", message: message,
                confirmText: "Ok, Got it", showCancel: false,
                image: "cyllo_workflow_automation/static/src/img/warning_popup.png"
            });
            return
        }

        const dialogConfigs = {
            'model': {
                body: _t("While deleting this node, All the nodes will be Removed"),
                onConfirm: async () => {
                    await this.resetStatesWhenClear();
                }
            },
            'action': {
                body: _t("Do you want to delete the node. The variables with in this scope is also deleted."),
                onConfirm: async () => {
                    // Capture both IDs before removal.
                    // IMPORTANT: env.context.deleteNode() is intentionally NOT called here.
                    // editor.removeNodeId() fires synchronous connectionRemoved events that
                    // call contextUpdateConnection(), which needs the node to still be present
                    // in env.context. We defer context cleanup to the nodeRemoved handler
                    // via _pendingNodeRemoval, which runs AFTER all connectionRemoved events.
                    const nodeId = node.data.nodeId;
                    const drawflowId = node.id;
                    // 1. Remove this node's ID from every other variable's usedIn array
                    //    (clears stale consumer refs so producers can be deleted later).
                    this.removeNodeIdFromVariables(nodeId);
                    // 2. Remove all variables scoped to this node.
                    this.removeVariables(nodeId);
                    // 3. Remove any import statements registered by this node.
                    this.removeImports(nodeId);
                    // 4. Persist the deletion to the backend.
                    await this.orm.unlink("node.struct", [nodeId]);
                    // 5. Register mapping so nodeRemoved can call env.context.deleteNode()
                    //    after Drawflow's connectionRemoved cascade is complete.
                    if (!this._pendingNodeRemoval) this._pendingNodeRemoval = new Map();
                    this._pendingNodeRemoval.set(drawflowId, nodeId);
                    // 6. Remove from canvas — fires connectionRemoved then nodeRemoved.
                    this.editor.removeNodeId(`node-${drawflowId}`);
                }
            },
            'default': {
                body: _t("Do you want to delete the node. The variables with in this scope is also deleted."),
                onConfirm: async () => {
                    // Same deferred-context-delete pattern as 'action' — see comment above.
                    const nodeId = node.data.nodeId;
                    const drawflowId = node.id;
                    this.removeNodeIdFromVariables(nodeId);
                    this.removeVariables(nodeId);
                    this.removeImports(nodeId);
                    await this.orm.unlink("node.struct", [nodeId]);
                    if (!this._pendingNodeRemoval) this._pendingNodeRemoval = new Map();
                    this._pendingNodeRemoval.set(drawflowId, nodeId);
                    this.editor.removeNodeId(`node-${drawflowId}`);
                }
            }
        };
        const config = dialogConfigs[node.data.type] || dialogConfigs.default;
        this.dialogService.add(ConfirmationPopup, {
            title: "Confirm Action",
            message: config.body,
            confirmText: "Yes, proceed",
            cancelText: "No, cancel",
            onConfirm: config.onConfirm,
            onCancel: () => {
            },
            lottie: true,
            lottiePath: "cyllo_workflow_automation/static/src/img/lottie-warning.json",
        });
    }

    async clearModelNodeData(node) {
        this.destroyNodeApps();
        this.state.nodeDetails = [];
        this.editor.clearModuleSelected();
        this.orm.call('work.auto', 'clear_all_nodes', [this.id]);
        this.env.variables.setContext({variables: []});
        this.env.context.setContext({nodes: []});
        Object.assign(this.state, {
            variables: [], code: "", imports: [], model_blk: true,
            trigger_blk: false, other_blk: false, model: "", model_id: false,
        });
    }

    canConnect(inputId, outputId, outputClass) {
        const flowData = this.getCurrentFlowData();
        const flowNodes = Object.values(flowData || {});
        const outPutNode = flowNodes.find(node => node.id === outputId);
        const inPutNode = flowNodes.find(node => node.id === inputId);
        if (!outPutNode || !inPutNode) {
            return false;
        }
        const isReuseAutomation = inPutNode.name === "Reuse Automation" || inPutNode.data?.name === "Reuse Automation";
        const modelToAction = outPutNode.data.type === "model" && inPutNode.data.type === "action";
        const modelToReuse = outPutNode.data.type === "model" && isReuseAutomation;
        const actionToModel = inPutNode.data.type === "action" && outPutNode.data.type !== "model";
        // Allow: model -> trigger(action), model -> Reuse Automation(action_to_do)
        // Block: action -> non-model, any other model -> non-action
        if ((!modelToAction && !modelToReuse && outPutNode.data.type === "model") || actionToModel) {
            return false;
        }
        const branchId = this.getNodeBranchId(outPutNode);
        const currentBranches = this.branchInputMap[inputId] || new Set();
        if (currentBranches.has(branchId)) {
            return false;
        }
        return true;
    }

    selectTab(value) {
        this.state.block = value === 'block';
    }

    contextUpdateNodeCreation(id) {
        const flowData = this.editor.drawflow.drawflow.Home.data;
        const flowNodes = Object.values(flowData)
        const createdNode = flowNodes.find(node => node.id === id);
        if (!createdNode) return;
        const nodeId = createdNode.data.nodeId;
        const isParent = createdNode.name === "Condition" || createdNode.name === "Loop" || createdNode.name === "Try Catch"
        //TODO: Handle Context
        const currentContext = this.env.context.context
        const nodes = currentContext?.nodes || []
        const isLoop = createdNode.name === "Loop";
        const isTryCatch = createdNode.name === "Try Catch";
        this.env.context.setContext({
            nodes: [...nodes, {
                nodeId,
                parent: null,
                left: null,
                right: null,
                child1: isParent ? {
                    left: null,
                    right: null,
                    code: "pass"
                } : null,
                child2: null,
                isParent,
                isLoop,
                isTryCatch,
                code: "",
                type: createdNode.data.type,
                trigger_type: createdNode.data.trigger_type,
            }]
        })
    }

    contextUpdateConnection(data, creation) {
        // TODO: Handle Context
        const {output_id, input_id, output_class} = data;
        const flowData = this.editor.drawflow.drawflow.Home.data;
        const nodes = Object.values(flowData)
        const inputNode = nodes.find(node => node.id == input_id)
        const outputNode = nodes.find(node => node.id == output_id)
        if (!inputNode || !outputNode) return;
        const currentContext = this.env.context.context
        const context_input_node = currentContext.nodes.find(node => node.nodeId === inputNode.data.nodeId)
        const context_output_node = currentContext.nodes.find(node => node.nodeId === outputNode.data.nodeId)
        const isModelOutput = outputNode.data.type === "model";
        const branchId = isModelOutput
            ? `${this.branchDefaultPrefix}-${outputNode.data.nodeId}-${inputNode.data.nodeId}`
            : this.getNodeBranchId(outputNode);
        this.assignNodeBranch(outputNode, branchId);
        this.assignNodeBranch(inputNode, branchId);
        if (creation) {
            context_input_node.left = context_output_node;
            this.recordBranchConnection(branchId, inputNode.id);
        } else {
            context_input_node.left = null;
            this.removeBranchConnection(branchId, inputNode.id);
            this.removeNodeBranch(inputNode, branchId);
        }
        if (context_output_node.isParent) {
            const outputIdx = output_class.split('_')[1];
            const propName = outputIdx === '3' ? 'right' : `child${outputIdx}`;

            if (creation) {
                if (!Array.isArray(context_output_node[propName])) {
                    context_output_node[propName] = context_output_node[propName] ? [context_output_node[propName]] : [];
                }
                if (!context_output_node[propName].includes(context_input_node)) {
                    context_output_node[propName].push(context_input_node);
                }
            } else {
                if (Array.isArray(context_output_node[propName])) {
                    context_output_node[propName] = context_output_node[propName].filter(n => n !== context_input_node);
                } else if (context_output_node[propName] === context_input_node) {
                    context_output_node[propName] = null;
                }
            }
        } else if (isModelOutput) {
            // Model node connecting to an action_to_do (e.g. Reuse Automation directly)
            // Store the type on the input context node so getFlowRoots can find it.
            if (creation) {
                context_input_node.type = inputNode.data.type || context_input_node.type;
            }
        } else if (!isModelOutput) {
            if (creation) {
                if (!Array.isArray(context_output_node.right)) {
                    context_output_node.right = context_output_node.right ? [context_output_node.right] : [];
                }
                if (!context_output_node.right.includes(context_input_node)) {
                    context_output_node.right.push(context_input_node);
                }
            } else {
                if (Array.isArray(context_output_node.right)) {
                    context_output_node.right = context_output_node.right.filter(n => n !== context_input_node);
                } else if (context_output_node.right === context_input_node) {
                    context_output_node.right = null;
                }
            }
        }
    }

    registerNodes(flowData = this.editorState.value[0]?.flow_data) {
        Object.values(flowData?.drawflow?.Home?.data || {}).forEach(item => {
            const uniqueIdentifier = item.name + '__' + item.data.nodeId
            this.editor.registerNode(uniqueIdentifier, ModelComponent, item.data, {});
        })
    }

    async onClickNewRule() {
        const rule = await this.orm.create("work.auto", [{'name': 'Automation rule'}])
        const action = {
            type: "ir.actions.client",
            tag: "automation_view",
            context: {
                id: rule[0]
            }
        }
        const message = _t("You are already in a new record")
        this.deleteEmptyRecord(action, message)
    }

    onClickMenuBar() {
        this.env.bus.trigger('onclickMenuBar')
    }

    /**
     * The editor is a client action (tag "automation_view") opened without a
     * menu_id. After a browser refresh Odoo restores the current app from the
     * URL's menu_id or by matching the action id to a menu's actionID - neither
     * works for a client action, so `menuService.getCurrentApp()` comes back
     * empty and the top app menu (name + Triggers/Automations sections)
     * disappears. Explicitly flag the Workflow Automation app as current: this
     * repopulates getCurrentApp() (top menu renders immediately) and locks
     * menu_id back into the URL so later refreshes are restored by core too.
     */
    restoreCurrentApp() {
        const app = this.menuService
            .getApps()
            .find((menu) => menu.xmlid === "cyllo_workflow_automation.menu_workflow");
        if (app) {
            this.menuService.setCurrentMenu(app.id);
        }
    }

    async setModelState() {
        if (!this.id) return;
        const data = await this.orm.read("work.auto", [this.id], ['model_id']);
        if (data.length > 0) {
            const modelData = data[0].model_id;
            if (modelData) {
                const model_res = await this.orm.read("ir.model", [modelData[0]], ['model']);
                if (model_res.length > 0) {
                    this.state.model_id = modelData[0];
                    this.state.model = modelData[1];
                    this.state.model_name = model_res[0].model;
                }
            }
        }
    }

    get editorValue() {
        return this.editorState.value
    }

    get buttonClass() {
        const randomNumber = Math.floor(Math.random() * 7);
        return BUTTON_CLASSES[randomNumber];
    }

    get titleAccessibleVariables() {
        if (!this.currentNode || this.currentNode?.data.model.length > 0) return ""
        return "Accessible Variables " + this.currentNode.name
    }

    get globalVariablesContext() {
        return this.env.globalVariables.context.variables || []
    }

    get accessibleVariables() {
        if (!this.state.selectedNodeID) return [];
        const getAllLeftNodeIds = (node, nodeIds = [], visited = new Set()) => {
            if (!node || visited.has(node.nodeId)) return nodeIds;
            visited.add(node.nodeId);
            nodeIds.push(node.nodeId);
            return getAllLeftNodeIds(node.left, nodeIds, visited);
        };
        const currentNodeId = this.currentNode?.data?.nodeId;
        const currentContext = this.env.context.context || {};
        const allVariables = this.env.variables.context.variables || [];
        const contextNodes = currentContext.nodes || [];
        let selectedNode = contextNodes.find(
            item => item.nodeId === currentNodeId
        );
        const scopeIds = getAllLeftNodeIds(selectedNode);
        const filteredVariables = allVariables || [];
        const accessibleVariables = filteredVariables.filter(variable =>
            scopeIds.includes(variable.scopeId)
        );
        return accessibleVariables;
    }

    manageData(flowData = this.editorValue[0]?.flow_data) {
        if (flowData) {
            this.importData(flowData)
            this.state.nodeDetails.forEach(node => {
                const {component, props, ref} = node;
                if (!ref || !ref.isConnected) {
                    return;
                }
                props.updateImports = this.updateImportStatements.bind(this);
                this.mountComponent(component, ref, props);
            })
            this.positionCanvasForLoadedFlow();
        }
    }

    positionCanvasForLoadedFlow() {
        const applyPosition = () => {
            if (!this.editor?.precanvas || !this.drawBoard?.el) {
                return;
            }

            const nodeElements = Array.from(this.editor.precanvas.querySelectorAll('[id^="node-"]'));
            if (!nodeElements.length) {
                return;
            }

            const bounds = nodeElements.reduce((acc, el) => {
                const left = el.offsetLeft;
                const top = el.offsetTop;
                const right = left + el.offsetWidth;
                const bottom = top + el.offsetHeight;
                return {
                    minX: Math.min(acc.minX, left),
                    minY: Math.min(acc.minY, top),
                    maxX: Math.max(acc.maxX, right),
                    maxY: Math.max(acc.maxY, bottom),
                };
            }, {
                minX: Infinity,
                minY: Infinity,
                maxX: -Infinity,
                maxY: -Infinity,
            });

            if (!Number.isFinite(bounds.minX)) {
                return;
            }

            const viewportWidth = this.drawBoard.el.clientWidth;
            const viewportHeight = this.drawBoard.el.clientHeight;
            const graphWidth = bounds.maxX - bounds.minX;
            const graphHeight = bounds.maxY - bounds.minY;
            const leftPadding = Math.max(48, viewportWidth * 0.08);
            const topPadding = Math.max(28, viewportHeight * 0.06);
            const availableWidth = viewportWidth - leftPadding - 48;
            const availableHeight = viewportHeight - topPadding - 48;

            let targetX;
            if (graphWidth <= availableWidth) {
                targetX = leftPadding - bounds.minX;
            } else {
                targetX = (viewportWidth - graphWidth) / 2 - bounds.minX;
            }
            const targetY = graphHeight <= availableHeight
                ? topPadding - bounds.minY
                : (viewportHeight - graphHeight) / 2 - bounds.minY;

            this.editor.canvas_x = targetX;
            this.editor.canvas_y = targetY;
            this.editor.precanvas.style.transform = `translate(${targetX}px, ${targetY}px) scale(${this.editor.zoom})`;
            this.initialViewport = {
                canvas_x: this.editor.canvas_x,
                canvas_y: this.editor.canvas_y,
                zoom: this.editor.zoom,
            };
        };

        requestAnimationFrame(() => requestAnimationFrame(applyPosition));
    }

    restoreInitialViewport() {
        if (!this.initialViewport || !this.editor?.precanvas) {
            return false;
        }
        if (this.canvasFocusFrame) {
            cancelAnimationFrame(this.canvasFocusFrame);
            this.canvasFocusFrame = null;
        }
        this.editor.canvas_x = this.initialViewport.canvas_x;
        this.editor.canvas_y = this.initialViewport.canvas_y;
        this.editor.zoom = this.initialViewport.zoom;
        this.editor.zoom_last_value = this.initialViewport.zoom;
        this.applyCanvasTransform();
        this._updateZoomPercent();
        return true;
    }

    getViewportBoundsForNodes(nodes) {
        if (!nodes?.length || !this.drawBoard?.el || !this.editor?.precanvas) {
            return null;
        }
        const isSingleElement = nodes.length === 1;
        const bounds = nodes.reduce((acc, node) => {
            const nodeBounds = this.getNodeCanvasBounds(node);
            if (!nodeBounds) {
                return acc;
            }
            return {
                minX: Math.min(acc.minX, nodeBounds.left),
                minY: Math.min(acc.minY, nodeBounds.top),
                maxX: Math.max(acc.maxX, nodeBounds.right),
                maxY: Math.max(acc.maxY, nodeBounds.bottom),
            };
        }, {
            minX: Infinity,
            minY: Infinity,
            maxX: -Infinity,
            maxY: -Infinity,
        });

        if (!Number.isFinite(bounds.minX)) {
            return null;
        }

        const viewportWidth = this.drawBoard.el.clientWidth;
        const viewportHeight = this.drawBoard.el.clientHeight;
        const drawBoardRect = this.drawBoard.el.getBoundingClientRect();
        const sidebar = this.root.el?.querySelector('.cy_w_sidebar');
        const zoomControls = this.root.el?.querySelector('.bar-zoom');
        const sidebarRect = sidebar?.getBoundingClientRect();
        const zoomRect = zoomControls?.getBoundingClientRect();
        const leftOcclusion = sidebarRect
            ? Math.max(0, Math.min(drawBoardRect.right, sidebarRect.right) - drawBoardRect.left)
            : 0;
        const rightOcclusion = zoomRect
            ? Math.max(0, drawBoardRect.right - Math.max(drawBoardRect.left, zoomRect.left))
            : 0;
        const width = Math.max(1, bounds.maxX - bounds.minX);
        const height = Math.max(1, bounds.maxY - bounds.minY);
        const basePaddingX = isSingleElement ? Math.max(56, viewportWidth * 0.08) : Math.max(72, viewportWidth * 0.12);
        const basePaddingY = isSingleElement ? Math.max(48, viewportHeight * 0.08) : Math.max(56, viewportHeight * 0.12);
        const paddingLeft = basePaddingX + leftOcclusion;
        const paddingRight = basePaddingX + Math.max(20, rightOcclusion * 0.5);
        const paddingY = basePaddingY;
        const availableWidth = Math.max(160, viewportWidth - paddingLeft - paddingRight);
        const availableHeight = Math.max(120, viewportHeight - paddingY * 2);
        const fittedZoom = Math.min(
            this.editor.zoom_max,
            Math.max(
                isSingleElement ? Math.max(this.editor.zoom_min, 1.15) : Math.max(this.editor.zoom_min, 0.95),
                Math.min(
                    availableWidth / width,
                    availableHeight / height
                )
            )
        );

        const centerX = bounds.minX + width / 2;
        const centerY = bounds.minY + height / 2;
        const visibleCenterX = paddingLeft + availableWidth / 2;
        const visibleCenterY = paddingY + availableHeight / 2;
        const targetX = visibleCenterX - centerX * fittedZoom;
        const targetY = visibleCenterY - centerY * fittedZoom;
        return {targetX, targetY, targetZoom: fittedZoom};
    }

    animateCanvasFocus(targetX, targetY, targetZoom, duration = 320) {
        if (!this.editor?.precanvas) {
            return;
        }
        if (this.canvasFocusFrame) {
            cancelAnimationFrame(this.canvasFocusFrame);
        }
        const startX = this.editor.canvas_x;
        const startY = this.editor.canvas_y;
        const startZoom = this.editor.zoom;
        const startedAt = performance.now();
        const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

        const step = (now) => {
            const progress = Math.min(1, (now - startedAt) / duration);
            const eased = easeOutCubic(progress);
            this.editor.canvas_x = startX + (targetX - startX) * eased;
            this.editor.canvas_y = startY + (targetY - startY) * eased;
            this.editor.zoom = startZoom + (targetZoom - startZoom) * eased;
            this.editor.zoom_last_value = this.editor.zoom;
            this.applyCanvasTransform();
            this._updateZoomPercent();
            if (progress < 1) {
                this.canvasFocusFrame = requestAnimationFrame(step);
            } else {
                this.canvasFocusFrame = null;
            }
        };

        this.canvasFocusFrame = requestAnimationFrame(step);
    }

    focusCanvasOnNodes(nodes) {
        const viewport = this.getViewportBoundsForNodes(nodes);
        if (!viewport) {
            return false;
        }
        this.animateCanvasFocus(viewport.targetX, viewport.targetY, viewport.targetZoom);
        return true;
    }

    focusSelectedNode() {
        if (!this.state.selectedNodeID) {
            return false;
        }
        const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
        const selectedNode = Object.values(flowData).find(
            (node) => Number(node.id) === Number(this.state.selectedNodeID)
        );
        if (!selectedNode) {
            return false;
        }
        return this.focusCanvasOnNodes([selectedNode]);
    }

    focusWorkflowContent() {
        const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
        const nodes = Object.values(flowData);
        if (!nodes.length) {
            return false;
        }
        return this.focusCanvasOnNodes(nodes);
    }

    applyCanvasTransform() {
        if (!this.editor?.precanvas) {
            return;
        }
        this.editor.precanvas.style.transform =
            `translate(${this.editor.canvas_x}px, ${this.editor.canvas_y}px) scale(${this.editor.zoom})`;
    }

    flushCanvasPan() {
        this.canvasPanFrame = null;
        if (!this.editor) {
            this.pendingCanvasPan = {x: 0, y: 0};
            return;
        }
        this.editor.canvas_x -= this.pendingCanvasPan.x;
        this.editor.canvas_y -= this.pendingCanvasPan.y;
        this.pendingCanvasPan = {x: 0, y: 0};
        this.applyCanvasTransform();
    }

    onCanvasWheel(ev) {
        if (!this.editor || ev.ctrlKey) {
            return;
        }
        const deltaX = ev.deltaX || (ev.shiftKey ? ev.deltaY : 0);
        const deltaY = ev.deltaY;
        if (!deltaX && !deltaY) {
            return;
        }
        ev.preventDefault();
        this.pendingCanvasPan.x += deltaX;
        this.pendingCanvasPan.y += deltaY;
        if (!this.canvasPanFrame) {
            this.canvasPanFrame = requestAnimationFrame(() => this.flushCanvasPan());
        }
    }

    async loadData() {
        if (this.id) {
            this.editorState.value = await this.orm.read('work.auto', [this.id]);
            if (this.editorState.value[0] && this.editorState.value[0].flow_data.drawflow) {
                // No longer needed to set block states here as they are now reactive getters
            }
        } else {
            this.editorState.value = await this.orm.searchRead('work.auto', [], [], {limit: 1})
        }
    }

    importData(data) {
        this.destroyNodeApps();
        this.state.nodeDetails = [];
        this.editor.import(data)
    }

    getNodeCanvasBounds(node) {
        if (!this.editor?.precanvas || !node) {
            return null;
        }
        const nodeElement = this.editor.precanvas.querySelector(`#node-${node.id}`);
        if (nodeElement) {
            const left = Number(nodeElement.offsetLeft || 0);
            const top = Number(nodeElement.offsetTop || 0);
            const width = Number(nodeElement.offsetWidth || 180);
            const height = Number(nodeElement.offsetHeight || 72);
            return {
                left,
                top,
                right: left + width,
                bottom: top + height,
            };
        }

        const left = Number(node.pos_x ?? 0);
        const top = Number(node.pos_y ?? 0);
        const width = 180;
        const height = 72;
        return {
            left,
            top,
            right: left + width,
            bottom: top + height,
        };
    }
    _updateZoomPercent() {
        const zoom = this.editor && this.editor.zoom ? this.editor.zoom : 1;
        this.state.zoomPercent = Math.round(zoom * 100);
    }
    zoomOut() {
        this.editor.zoom_out();
        this._updateZoomPercent();
    }

    zoomReset() {
        if (this.restoreInitialViewport()) {
            return;
        }
        if (this.focusWorkflowContent()) {
            return;
        }
        if (!this.editor) {
            return;
        }
        this.editor.zoom = 1;
        this.editor.zoom_last_value = 1;
        this.editor.canvas_x = 0;
        this.editor.canvas_y = 0;
        this.applyCanvasTransform();
        this._updateZoomPercent();
    }

    zoomIn() {
        this.editor.zoom_in();
        this._updateZoomPercent();
    }

    changeMode() {
        this.drawBoardState.edit = !this.drawBoardState.edit;
        this.editor.editor_mode = this.drawBoardState.edit ? 'edit' : 'fixed';
        this.env.services.effect.add({
            message: this.drawBoardState.edit ? "Unlocked!" : 'Locked!',
            locked: true,
            type: "save_confetti",
        });
    }

    async clearModuleSelected() {
        this.dialogService.add(ConfirmationPopup, {
            title: _t("Are you sure"),
            message: _t("Are you sure you want to clear? All the nodes will be deleted permanently."),
            confirmText: _t("Yes, proceed"),
            cancelText: _t("No, cancel"),
            onConfirm: this.resetStatesWhenClear.bind(this),
            onCancel: () => {
            },
            lottie: true,
            lottiePath: "cyllo_workflow_automation/static/src/img/delete-lottie.json",
        });
    }

    async resetStatesWhenClear() {
        this.orm.call('work.auto', 'clear_all_nodes', [this.id]);
        this.env.variables.setContext({variables: []});
        this.env.context.setContext({nodes: []});
        this.destroyNodeApps();
        this.state.nodeDetails = [];
        this.editor.clearModuleSelected();
        this.autoSaveDrawFlow().then(() => {
            Object.assign(this.state, {
                variables: [],
                code: "",
                imports: GLOBAL_IMPORTS,
                model: "",
                model_id: false,
                selectedNodeID: undefined,
            });
        });
        this.branchInputMap = {};
        this.connectionBranchMap = {};
    }

    changeModule(module) {
        this.editor
    }

    extractBackendInfo() {
        const {data: mainData} = this.editor.drawflow.drawflow.Home;
        const model_data = Object.values(mainData).find(({data}) => data?.type === "model");
        const trigger_nodes = Object.values(mainData).filter(({data}) => data?.type === "action");
        const triggerFunctionIds = [];
        const seenTriggerTypes = new Set();
        trigger_nodes.forEach(({data}) => {
            const modelInfo = data?.model;
            const triggerType = data?.trigger_type;
            if (triggerType && seenTriggerTypes.has(triggerType)) {
                return;
            }
            if (Array.isArray(modelInfo) && modelInfo[0]) {
                triggerFunctionIds.push(modelInfo[0]);
                if (triggerType) {
                    seenTriggerTypes.add(triggerType);
                }
            }
        });
        const uniqueTriggerIds = [...new Set(triggerFunctionIds)];
        let backendData = {
            code: this.state.code,
            variables: this.state.variables,
            imports: this.state.imports,
            is_reusable: Boolean(this.state.isReusable),
            reuse_scope: this.state.isReusable ? 'generic' : false,
        };
        if (model_data) {
            backendData = {
                ...backendData,
                model_id: model_data.data.model[0]
            };
        }
        if (uniqueTriggerIds.length) {
            backendData = {
                ...backendData,
                function_id: uniqueTriggerIds[0]
            };
        }
        backendData = {
            ...backendData,
            trigger_function_ids: uniqueTriggerIds,
        };
        // Include schedule (cron) fields so the backend can create/update ir.cron
        backendData = {
            ...backendData,
            time_trigger_mode: this.state.cronMode || false,
            time_trigger_time: this.state.cronTime || 0,
            time_trigger_day: this.state.cronDay || 1,
            time_trigger_month: this.state.cronMonth || 1,
            time_trigger_weekday: this.state.cronWeekday || '0',
        };
        // Include watched field so field_id is saved even on first save of a new workflow
        if (this.state.watchedFieldId) {
            backendData = {
                ...backendData,
                field_id: this.state.watchedFieldId,
            };
        }
        return backendData;
    }

    getHistorySnapshot() {
        const snapshot = {
            drawflow: this.editor.export(),
            variables: this.state.variables,
            context: this.env.context.context,
            imports: this.state.imports,
        };
        return cloneState(snapshot);
    }

    saveHistory() {
        if (this.isRestoring) return;
        this.history.save(this.getHistorySnapshot());
        this.updateHistoryState();
    }

    saveHistoryDebounced() {
        if (this.isRestoring) return;
        if (this.moveTimeout) clearTimeout(this.moveTimeout);
        this.moveTimeout = setTimeout(() => {
            this.saveHistory();
        }, 300);
    }

    undo() {
        if (this.history.canUndo()) {
            // Any node configuration wizard still open at this point refers to a
            // node that is about to be replaced by the restored snapshot, so it
            // must be closed rather than left dangling over stale/removed data.
            this.dialogService.closeAll();
            const state = this.history.undo();
            this.restoreHistoryState(state);
        }
    }

    redo() {
        if (this.history.canRedo()) {
            this.dialogService.closeAll();
            const state = this.history.redo();
            this.restoreHistoryState(state);
        }
    }

    restoreHistoryState(snapshot) {
        if (!snapshot || !snapshot.drawflow) {
            console.error("Attempted to restore invalid history state:", snapshot);
            return;
        }
        this.isRestoring = true;
        try {
            const {drawflow, variables, context, imports} = snapshot;
            if (this.editorState.value[0]) {
                this.editorState.value[0].flow_data = drawflow;
            }

            this.state.variables = variables;
            this.env.variables.setContext({variables: [...variables]});

            this.env.context.setContext(context);

            this.state.imports = imports;
            this.registerNodes(drawflow);
            this.manageData(drawflow);
            this.updateHistoryState();
            this.autoSaveDrawFlow();
            this.updateCode();
        } finally {
            this.isRestoring = false;
        }
        // Since we imported, we might need to re-register nodes or fix Owl components
        // Drawflow import usually reconstructs the HTML but the Owl components need to be alive.
        // In this implementation, the components are managed via state.nodeDetails
        // and registerNode. Re-importing might require some orchestration if Owl components
        // get destroyed. However, Drawflow OWL integration often handles this.
    }

    updateHistoryState() {
        this.state.canUndo = this.history.canUndo();
        this.state.canRedo = this.history.canRedo();
    }

    onKeyDown(e) {
        if (e.ctrlKey || e.metaKey) {
            const key = e.key.toLowerCase();
            if (key === 'y') {
                e.preventDefault();
                this.redo();
            } else if (key === 'z') {
                e.preventDefault();
                this.undo();
            }
        }
    }

    get automationIdentifiers() {
        const identifiers = this.env.variables.context.variables.map(item => item.variable_name)
        return {
            pythonKeywords: [...PYTHON_KEYWORDS],
            variableNames: [...identifiers]
        };
    }

    async onSave() {
        const {isValid, error, nodeIds} = this.validateFlow();
        const nameValidation = this.validateName();
        if (!isValid || !nameValidation.isValid) {
            this.handleValidationErrors(isValid, nameValidation, nodeIds, error);
            return;
        }
        try {
            this.state.saveLoading = true
            await this.saveData();
            this.state.saveLoading = false
            this.showSuccessMessage();
        } catch (error) {
            this.showErrorMessage(error);
        }
    }

    get canShowSaveButton() {
        const summary = this.state.testResult?.summary;
        return Boolean(summary) && (summary.error || 0) === 0;
    }

    async onTestWorkflow() {
        if (this.state.testRunning) {
            return;
        }
        const {isValid, error, nodeIds} = this.validateFlow();
        const nameValidation = this.validateName();
        if (!isValid || !nameValidation.isValid) {
            const errorMessage = [nameValidation.isValid ? "" : nameValidation.error, error].filter(Boolean).join(", ");
            this.showTestValidationPanel(errorMessage, nodeIds);
            this.handleValidationErrors(isValid, nameValidation, nodeIds, error);
            return;
        }

        this.resetTestVisuals();
        this.state.testRunning = true;

        let response;
        try {
            await this.saveData();
            response = await jsonrpc('/cyllo_workflow/test_run', {
                work_auto_id: this.id,
            });
        } catch (error) {
            this.state.testRunning = false;
            this.showErrorMessage(error.message || error);
            return;
        }

        if (!response?.ok) {
            this.state.testRunning = false;
            this.showErrorMessage(response?.error || _t("Workflow test failed."));
            return;
        }

        const payload = {
            results: response.results || [],
            summary: response.summary || {},
            record: response.record || null,
        };
        this.state.testResult = payload;
        this.state.testResultMinimized = false;
        await this.playTestResults(payload.results);
        this.state.testRunning = false;

        const summary = payload.summary || {};
        if ((summary.error || 0) === 0 && (summary.total || 0) > 0) {
            if ((summary.warning || 0) > 0) {
                this.env.services.effect.add({
                    title: _t("Tests Passed with Warnings"),
                    message: _t("Workflow test completed with warnings. Please review them."),
                    type: "notification_panel",
                    notificationType: "warning",
                });
            } else {
                this.env.services.effect.add({
                    title: _t("All Tests Passed!"),
                    message: _t("Workflow test completed successfully. Please save your workflow."),
                    type: "notification_panel",
                    notificationType: "success",
                });
            }
        }

        this.scheduleTestReset();
    }

    async onRunNow() {
        if (this.state.runNowLoading) {
            return;
        }
        this.state.runNowLoading = true;
        try {
            // saveData() creates the record (and sets this.id) on first save,
            // so don't gate on this.id before calling it — a brand-new,
            // never-saved workflow must still be runnable from this button.
            await this.saveData();
            if (!this.id) {
                this.env.services.effect.add({
                    title: _t("Run Now failed"),
                    message: _t("Could not save the workflow before running it."),
                    type: "notification_panel",
                    notificationType: "danger",
                });
                return;
            }
            const response = await jsonrpc('/cyllo_workflow/run_now', {
                work_auto_id: this.id,
            });
            if (!response?.ok) {
                this.env.services.effect.add({
                    title: _t("Run Now failed"),
                    message: response?.error || _t("Workflow execution failed."),
                    type: "notification_panel",
                    notificationType: "danger",
                });
            } else {
                const processed = response.records_processed ?? 0;
                const errors = response.errors || [];
                const warning = response.warning || '';
                if (errors.length) {
                    this.env.services.effect.add({
                        title: _t("Run Now — errors"),
                        message: errors.slice(0, 3).join(' | '),
                        type: "notification_panel",
                        notificationType: "warning",
                    });
                } else if (warning) {
                    this.env.services.effect.add({
                        title: _t("Run Now"),
                        message: warning,
                        type: "notification_panel",
                        notificationType: "info",
                    });
                } else {
                    this.env.services.effect.add({
                        title: _t("Run Now succeeded"),
                        message: _t("Workflow executed on %s record(s).", processed),
                        type: "notification_panel",
                        notificationType: "success",
                    });
                }
            }
        } catch (error) {
            this.env.services.effect.add({
                title: _t("Run Now error"),
                message: error.message || String(error),
                type: "notification_panel",
                notificationType: "danger",
            });
        } finally {
            this.state.runNowLoading = false;
        }
    }

    showTestValidationPanel(message, nodeIds = []) {
        this.resetTestVisuals();
        const flowData = Object.values(this.getCurrentFlowData());
        const ids = [...new Set(nodeIds || [])];
        const results = ids.length
            ? ids.map((nodeId) => {
                const drawNode = flowData.find((node) => node.data?.nodeId === nodeId);
                return {
                    node_id: nodeId,
                    label: drawNode?.data?.label || drawNode?.data?.name || _t("Workflow node"),
                    status: 'error',
                    message,
                };
            })
            : [{
                node_id: `validation_${Date.now()}`,
                label: _t("Workflow"),
                status: 'error',
                message,
            }];

        this.state.testResult = {
            results,
            summary: {
                total: results.length,
                success: 0,
                warning: 0,
                error: results.length,
            },
            record: null,
        };
        this.state.testResultMinimized = false;

        for (const item of results) {
            if (typeof item.node_id === "number") {
                this.env.bus.trigger("FLOW:TEST:RESULT", item);
            }
        }
        this.scheduleTestReset();
    }

    get saveClass() {
        return (this.state.model || this.state.isGenericReusable) ? 'btn btn-primary' : 'btn btn-secondary'
    }

    validateName() {
        const name = this.state.name.trim();
        return {
            isValid: name !== "" && name !== "Automation rule",
            error: 'Add the correct name'
        };
    }

    handleValidationErrors(isFlowValid, nameValidation, nodeIds, err) {
        if (!isFlowValid && nodeIds) {
            this.env.bus.trigger("FLOW:VALIDATION", {nodeIds});
        }
        if (!nameValidation.isValid) {
            this.showNameError();
        }
        const errorMessage = [nameValidation.error, err].filter(Boolean).join(", ");
        this.showErrorMessage(errorMessage);
    }

    showNameError() {
        this.inputNameRef.el.focus();
        this.state.nameError = true;
        setTimeout(() => {
            if (owl.status(this) !== "destroyed") this.state.nameError = false;
        }, 5000);
    }

    onCreateTrigger() {
        if (this.state.isGenericReusable) {
            return;
        }
        this.state.customTrigger = true
    }

    async removeObjectNodeForReusable() {
        const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
        const modelNode = Object.values(flowData).find((node) => node.data?.type === "model");
        if (modelNode) {
            this.editor.removeNodeId(`node-${modelNode.id}`);
        }
        const buttonClickNodes = Object.values(flowData).filter((node) => node.data?.name === "Button Click");
        for (const buttonClickNode of buttonClickNodes) {
            this.editor.removeNodeId(`node-${buttonClickNode.id}`);
        }
        this.state.customTrigger = false;
        this.state.model = "";
        this.state.model_id = false;
        this.state.model_name = "";
        this.state.selectedNodeID = undefined;
        const currentRecordVariable = this.env.globalVariables.context.variables.find(
            (item) => item.variable_name === "current_record"
        );
        if (currentRecordVariable) {
            currentRecordVariable.modelId = undefined;
            currentRecordVariable.modelName = undefined;
        }
        if (this.id) {
            await this.orm.write('work.auto', [this.id], {model_id: false});
        }
    }

    async toggleReusable() {
        const newValue = !this.state.isReusable;
        this.state.isReusable = newValue;
        this.state.isGenericReusable = newValue;
        if (newValue) {
            await this.removeObjectNodeForReusable();
        }
        if (this.id) {
            await this.orm.write('work.auto', [this.id], {
                is_reusable: newValue,
                reuse_scope: 'generic',
            });
        }
    }

    async saveData() {
        this.updateCode();
        const data = this.editor.export();
        const newData = this.extractBackendInfo();
        // newData.image = await this.generateImage();

        // FIX: ttype (before/after) must only be 'before' when UNLINK is the
        // SOLE trigger in the automation. When multiple triggers are present
        // (e.g. create + field_change + unlink), 'after' is always the correct
        // choice: create needs the saved record available, field_change runs on
        // an existing record, and unlink-before is handled by its own patched
        // wrapper that calls _process before the actual deletion regardless of
        // this flag. Forcing ttype='before' for the whole automation when unlink
        // is merely one of many triggers was the root cause of create/field_change
        // actions receiving no record context (records was empty/undefined).
        const triggerNodes = Object.values(data.drawflow.Home.data).filter(
            item => item.data.type === 'action'
        );
        const hasUnlink = triggerNodes.some(
            item => item.data.trigger_type === 'unlink' || item.data.ttype === 'On Unlink'
        );
        const hasOtherTriggers = triggerNodes.some(
            item => item.data.trigger_type !== 'unlink' && item.data.ttype !== 'On Unlink'
        );
        // Only use 'before' (ttype=true) when unlink is the only trigger present.
        const ttype = hasUnlink && !hasOtherTriggers;
        const newId = await this.orm.call('work.auto', 'save_data', [this.id, data, this.state.name, ttype], newData);

        // Update this.id if it was a new record (this.id was falsy)
        if (!this.id && newId) {
            this.id = newId;
            // Also update the session context so it persists across reloads
            this.saveManually(newId);
        }
    }

    showSuccessMessage() {
        this.env.services.effect.add({
            message: "Great job! Record saved.",
            type: "save_confetti",
        });
    }

    showErrorMessage(error) {
        this.env.services.effect.add({
            title: "Flow validation failed",
            message: "Unable to save the record.",
            description: error,
            type: "notification_panel",
            notificationType: "error",
        });
        errorVibration();
    }

    async playTestResults(results) {
        const runId = ++this.testAnimationRunId;
        let previousNodeId = null;
        this.enableTestFlowCanvas();
        for (const item of results) {
            if (runId !== this.testAnimationRunId) {
                return;
            }
            this.activateTestConnection(previousNodeId, item.node_id);
            this.env.bus.trigger("FLOW:TEST:RESULT", {
                node_id: item.node_id,
                status: 'running',
                message: _t("Running test..."),
            });
            await new Promise(resolve => setTimeout(resolve, 180));
            if (runId !== this.testAnimationRunId) {
                return;
            }
            this.env.bus.trigger("FLOW:TEST:RESULT", item);
            previousNodeId = item.node_id;
            await new Promise(resolve => setTimeout(resolve, 220));
        }
    }

    resetTestVisuals() {
        this.testAnimationRunId += 1;
        this.resetTestConnections();
        if (this.testResetTimer) {
            clearTimeout(this.testResetTimer);
            this.testResetTimer = null;
        }
        this.env.bus.trigger("FLOW:TEST:RESET");
    }

    clearTestHighlights() {
        this.resetTestVisuals();
        this.state.testResult = null;
        this.state.testResultMinimized = false;
    }

    toggleTestResultPanel() {
        if (!this.state.testResult) {
            return;
        }
        this.state.testResultMinimized = !this.state.testResultMinimized;
    }

    getDrawflowNodeIdByStructId(structId) {
        const flowData = this.editor?.drawflow?.drawflow?.Home?.data || {};
        const match = Object.values(flowData).find(
            (node) => Number(node?.data?.nodeId) === Number(structId)
        );
        return match?.id || null;
    }

    getTestConnectionElement(fromStructId, toStructId) {
        const fromDrawflowId = this.getDrawflowNodeIdByStructId(fromStructId);
        const toDrawflowId = this.getDrawflowNodeIdByStructId(toStructId);
        if (!fromDrawflowId || !toDrawflowId || !this.editor?.precanvas) {
            return [];
        }
        return Array.from(this.editor.precanvas.querySelectorAll(
            `.connection.node_out_node-${fromDrawflowId}.node_in_node-${toDrawflowId}`
        ));
    }

    clearActiveTestConnection() {
        if (this.activeTestConnections.size) {
            for (const connection of this.activeTestConnections) {
                connection.classList.remove('cy-test-flow-active');
                connection.classList.add('cy-test-flow-complete');
                this.completedTestConnections.add(connection);
            }
            this.activeTestConnections.clear();
        }
    }

    enableTestFlowCanvas() {
        if (this.editor?.precanvas) {
            this.editor.precanvas.classList.add('cy-test-flow-mode');
        }
    }

    disableTestFlowCanvas() {
        if (this.editor?.precanvas) {
            this.editor.precanvas.classList.remove('cy-test-flow-mode');
        }
    }

    resetTestConnections() {
        this.clearActiveTestConnection();
        for (const connection of this.completedTestConnections) {
            connection.classList.remove('cy-test-flow-complete');
        }
        this.completedTestConnections.clear();
        this.activeTestConnections.clear();
        if (this.editor?.precanvas) {
            this.editor.precanvas
                .querySelectorAll('.connection.cy-test-flow-active, .connection.cy-test-flow-complete')
                .forEach((connection) => {
                    connection.classList.remove('cy-test-flow-active', 'cy-test-flow-complete');
                });
        }
        this.disableTestFlowCanvas();
    }

    activateTestConnection(fromStructId, toStructId) {
        this.clearActiveTestConnection();
        if (!fromStructId || !toStructId) {
            return;
        }
        const connections = this.getTestConnectionElement(fromStructId, toStructId);
        for (const connection of connections) {
            connection.classList.remove('cy-test-flow-complete');
            connection.classList.add('cy-test-flow-active');
            this.completedTestConnections.delete(connection);
            this.activeTestConnections.add(connection);
        }
    }

    scheduleTestReset() {
        if (this.testResetTimer) {
            clearTimeout(this.testResetTimer);
        }
        window.removeEventListener('click', this.handleWindowClickForTestReset);
        setTimeout(() => {
            if (owl.status(this) !== 'destroyed' && this.state.testResult) {
                window.addEventListener('click', this.handleWindowClickForTestReset, {once: true});
            }
        }, 0);
        this.testResetTimer = setTimeout(() => {
            if (owl.status(this) !== 'destroyed') {
                this.resetTestVisuals();
            }
        }, 10000);
    }

    onWindowClickForTestReset() {
        if (!this.state.testRunning && this.state.testResult) {
            this.resetTestVisuals();
        }
    }

    updateName(newName) {
        this.state.name = newName;
        this.resetTestVisuals();
        // You might also want to save this to the server here
    }

    getCurrentFlowData() {
        if (this.editor?.drawflow?.drawflow?.Home?.data) {
            return this.editor.drawflow.drawflow.Home.data;
        }
        return this.editorValue?.[0]?.flow_data?.drawflow?.Home?.data || {};
    }

    getFlowConnectivityIssues(flowData) {
        const drawNodes = Object.entries(flowData || {});
        const executableNodes = drawNodes.filter(([, node]) => node.data?.type !== "model");
        const triggerNodes = executableNodes.filter(([, node]) => node.data?.type === "action");
        const isGenericReusable = Boolean(this.state.isReusable && this.state.isGenericReusable);
        const nodeName = (node) => node.data?.label || node.data?.name || _t("Node");
        const uniqueNodeIds = (items) => [...new Set(items.map((item) => item.data?.nodeId).filter(Boolean))];

        if (!executableNodes.length) {
            return {
                isValid: false,
                nodeIds: [],
                error: _t("Add at least one trigger and connect it to a workflow step before testing."),
            };
        }

        const adjacency = new Map();
        const incomingCounts = new Map();
        const modelReuseRoots = new Set();
        for (const [drawId] of executableNodes) {
            adjacency.set(String(drawId), []);
            incomingCounts.set(String(drawId), 0);
        }

        for (const [drawId, node] of drawNodes) {
            const sourceType = node.data?.type;
            const outputs = node.outputs || {};
            for (const output of Object.values(outputs)) {
                for (const connection of output.connections || []) {
                    const targetId = String(connection.node);
                    const targetNode = flowData?.[targetId];
                    if (!targetNode) {
                        continue;
                    }
                    if (
                        sourceType === "model" &&
                        targetNode.data?.type === "action_to_do" &&
                        targetNode.data?.name === "Reuse Automation"
                    ) {
                        modelReuseRoots.add(targetId);
                    }
                    if (sourceType === "model" || targetNode.data?.type === "model") {
                        continue;
                    }
                    if (!adjacency.has(String(drawId))) {
                        adjacency.set(String(drawId), []);
                    }
                    adjacency.get(String(drawId)).push(targetId);
                    incomingCounts.set(targetId, (incomingCounts.get(targetId) || 0) + 1);
                }
            }
        }

        const directReuseRoots = executableNodes.filter(
            ([drawId, node]) =>
                node.data?.type === "action_to_do" &&
                node.data?.name === "Reuse Automation" &&
                modelReuseRoots.has(String(drawId))
        );

        if (!triggerNodes.length && !directReuseRoots.length && !isGenericReusable) {
            return {
                isValid: false,
                nodeIds: uniqueNodeIds(executableNodes.map(([, node]) => node)),
                error: _t("Add at least one trigger before testing the workflow."),
            };
        }

        let rootNodes = [];
        if (isGenericReusable) {
            rootNodes = executableNodes.filter(([drawId]) => (incomingCounts.get(String(drawId)) || 0) === 0);
            if (!rootNodes.length && executableNodes.length) {
                rootNodes = [executableNodes[0]];
            }
            if (rootNodes.length > 1) {
                const labels = rootNodes.map(([, node]) => nodeName(node));
                return {
                    isValid: false,
                    nodeIds: uniqueNodeIds(rootNodes.map(([, node]) => node)),
                    error: labels.length === 1
                        ? _t("%s is disconnected from the reusable workflow. Connect it before testing.", labels[0])
                        : _t("%s are disconnected from the reusable workflow. Connect them before testing.", labels.join(", ")),
                };
            }
        } else {
            const rootMap = new Map();
            for (const entry of [...triggerNodes, ...directReuseRoots]) {
                rootMap.set(String(entry[0]), entry);
            }
            rootNodes = [...rootMap.values()];
        }

        const reachable = new Set();
        const visit = (drawId) => {
            const key = String(drawId);
            if (reachable.has(key)) {
                return;
            }
            reachable.add(key);
            for (const childId of adjacency.get(key) || []) {
                visit(childId);
            }
        };
        for (const [drawId] of rootNodes) {
            visit(drawId);
        }

        const disconnectedTriggers = isGenericReusable
            ? []
            : triggerNodes.filter(([drawId]) => (adjacency.get(String(drawId)) || []).length === 0);
        if (disconnectedTriggers.length) {
            const labels = disconnectedTriggers.map(([, node]) => nodeName(node));
            return {
                isValid: false,
                nodeIds: uniqueNodeIds(disconnectedTriggers.map(([, node]) => node)),
                error: labels.length === 1
                    ? _t("%s is not connected to any workflow step.", labels[0])
                    : _t("%s are not connected to any workflow step.", labels.join(", ")),
            };
        }

        const orphanNodes = executableNodes.filter(([drawId, node]) => {
            if (node.data?.type === "action") {
                return false;
            }
            return !reachable.has(String(drawId));
        });
        if (orphanNodes.length) {
            const labels = orphanNodes.map(([, node]) => nodeName(node));
            return {
                isValid: false,
                nodeIds: uniqueNodeIds(orphanNodes.map(([, node]) => node)),
                error: labels.length === 1
                    ? _t("%s is disconnected from the workflow. Connect it to a trigger path before testing.", labels[0])
                    : _t("%s are disconnected from the workflow. Connect them to a trigger path before testing.", labels.join(", ")),
            };
        }

        return {isValid: true, nodeIds: [], error: ""};
    }

    validateFlow() {
        const validationArray = [];
        const nodes = this.env.context?.context?.nodes || [];

        // Generic reusable automations start without a model node -- they only
        // need at least one action node to be valid.
        if (nodes.length === 0) {
            if (this.state.isGenericReusable) {
                // Allow saving a generic automation even with an empty canvas
                // (user may save before adding nodes)
                return {isValid: true, error: ""};
            }
            return {isValid: false, error: "Please create a workflow"};
        }

        const data = this.getCurrentFlowData();
        if (!Object.keys(data).length) {
            console.error("Flow data is missing in editorValue:", this.editorValue);
            return {isValid: false, error: "Flow data not found"};
        }

        for (const node of nodes) {
            const nodeData = Object.values(data).find(
                (item) => item.data.nodeId === node.nodeId
            );

            if (!nodeData) {
                console.warn(`Skipping node ${node.nodeId}, not found in flow data`);
                continue; // prevents crash if node was deleted or not synced
            }

            // Validation: check if node requires configuration
            if (!node.code) {
                if (["action", "model"].includes(nodeData.data.type)) {
                    continue; // skip types that don't need validation
                }
                validationArray.push([nodeData.data.name, nodeData.data.nodeId]);
            }
        }

        if (validationArray.length > 0) {
            const errors = validationArray.map((item) => item[0]);
            const nodeIds = validationArray.map((item) => item[1]);
            const errorMessage =
                errors.length === 1
                    ? `${errors[0]} is not configured`
                    : `${errors.slice(0, -1).join(", ")} and ${errors[errors.length - 1]
                    } are not configured`;

            return {isValid: false, nodeIds, error: errorMessage};
        }

        const connectivityValidation = this.getFlowConnectivityIssues(data);
        if (!connectivityValidation.isValid) {
            return connectivityValidation;
        }

        const duplicateTriggerType = this.findDuplicateTriggerType(data);
        if (duplicateTriggerType) {
            const duplicateAction = this.state.actions.find(
                (action) => action.trigger_type === duplicateTriggerType
            );
            const label = duplicateAction?.name || duplicateTriggerType;
            return {
                isValid: false,
                error: _t("Trigger %s already exists in this workflow.", label),
            };
        }

        return {isValid: true, error: ""};
    }

    get Image() {
        return this.state.image
    }

    setImage(image) {
        this.state.image = image
    }

    getRecordId() {
        const id = Number(this.id);
        return Number.isInteger(id) && id > 0 ? id : null;
    }

    write(data) {
        const recordId = this.getRecordId();
        if (!recordId) {
            return;
        }
        owl.status(this) !== 'destroyed' && this.orm.write("work.auto", [recordId], data);
    }

    removeImports(nodeId) {
        for (const imps of this.imports) {
            imps.childStatement = imps.childStatement.filter(item => item.nodeId !== nodeId);
        }
        this.updateCode();
    }

    updateImportStatements(statement) {
        const {parent, child, nodeId} = statement;
        const statementObj = this.imports.find(item => item.importStatement === parent);
        if (statementObj) {
            const childObject = statementObj.childStatement.find(item => item.nodeId === nodeId)
            if (!childObject) {
                statementObj.childStatement.push({
                    statement: child,
                    nodeId: nodeId
                });
                this.state.imports = [...this.imports]
            } else {
                childObject.statement = child;
            }
        } else {
            this.state.imports = [...this.imports, {
                importStatement: parent,
                childStatement: [{statement: child, nodeId: nodeId}]
            }]
        }
    }

    triggerFileInput(actionId) {
        document.getElementById(`file-input-${actionId}`).click();
    }

    handleFileUpload(event, actionId) {
        const file = event.target.files[0];
        if (file && file.type === 'image/svg+xml') {
            const reader = new FileReader();
            reader.onload = (e) => {
                const action = this.state.actions.find(a => a.id === actionId);
                if (action) {
                    action.customIcon = e.target.result;
                    this.render(); // Trigger a re-render to show the new icon
                }
            };
            reader.readAsDataURL(file);
        } else {
            // Handle invalid file type
            alert('Please upload an SVG file.');
        }
    }

    get importStateMent() {
        let importStatements = "";
        for (let statement of this.imports) {
            const childStatements = statement.childStatement.map(item => {
                return item.statement;
            });
            const statementSet = new Set(childStatements.filter(Boolean))
            if (statement.childStatement.length > 0) {
                importStatements += `${statement.importStatement} ${Array.from(statementSet).join(', ')}\n`
            }
        }
        return importStatements;
    }

    get imports() {
        return this.state.imports || [];
    }

    updateCode() {
        const editor = this.editor || this.env.editor?.();
        if (!editor || typeof editor.export !== "function") {
            return;
        }
        const contextNodes = structuredClone(this.env.context.context?.nodes || []);
        const variables = this.env.variables?.context?.variables || [];
        const globalVariables = this.env.globalVariables?.context?.variables || [];
        let codeLines = [];
        for (const variable of globalVariables) {
            if (variable.variable_name === 'current_record') {
                // For generic reusable automations, model_name may be empty.
                // Fall back to records directly so current_record = records works.
                if (this.state.model_name) {
                    codeLines.push(`${variable.variable_name} = records[:1] if records else env['${this.state.model_name}'].browse()`);
                } else {
                    codeLines.push(`${variable.variable_name} = records[:1]`);
                }
            } else {
                codeLines.push(`${variable.variable_name} = ${variable.variable_value}`);
            }
        }

        const flowData = editor.export()?.drawflow?.Home?.data || {};

        // Map from trigger label (e.g. "On Write") to canonical trigger_type string.
        const triggerLabelMap = {
            'On Create': 'create',
            'On Write': 'write',
            'On Unlink': 'unlink',
            'On Field Change': 'field_change',
            'On Schedule': 'time',
            'On Time': 'time',
        };

        // Build a map ONLY for trigger nodes (type === 'action', directly connected
        // from a model node). Action descendant nodes (Activity, Warning, etc.) are
        // intentionally excluded so their inherited trigger_type does not pollute
        // the guard lookup.
        const triggerNodeMap = new Map(); // nodeId -> trigger_type string
        Object.values(flowData).forEach(node => {
            const data = node.data || {};
            // A trigger node in Drawflow: type === 'action' AND has a ttype
            // matching one of our known labels (or an explicit trigger_type).
            const isTriggerNode = data.type === 'action';
            if (!isTriggerNode) return;

            const rawTriggerType = data.trigger_type || triggerLabelMap[data.ttype];
            if (rawTriggerType && data.nodeId) {
                triggerNodeMap.set(String(data.nodeId), rawTriggerType);
            }
        });

        const flowRoots = this.getFlowRoots(contextNodes, triggerNodeMap);
        if (flowRoots.length) {
            codeLines.push("");
            flowRoots.forEach((root, index) => {
                const flowLines = this.buildFlowLines(root, variables);
                if (!flowLines.length) {
                    return;
                }
                // Derive trigger_type exclusively from the trigger node map so
                // that each branch is guarded by its OWN trigger, not the last-
                // dragged one from this.state.triggerType.
                const triggerType = triggerNodeMap.get(String(root.nodeId)) || root.trigger_type || '';
                if (triggerType) {
                    const triggerSafe = triggerType.replace(/'/g, "\\'");
                    codeLines.push(`if trigger_type == '${triggerSafe}':`);
                    flowLines.forEach(line => codeLines.push(`    ${line}`));
                } else {
                    codeLines.push(...flowLines);
                }
                if (index < flowRoots.length - 1) {
                    codeLines.push("");
                }
            });
        }
        const combinedCode = codeLines.join('\n');
        const imports = this.importStateMent;
        this.state.code = imports + "\n" + combinedCode;
    }

    getFlowRoots(nodes, triggerNodeMap) {
        // Primary: all trigger nodes identified in triggerNodeMap (type==='action').
        // triggerNodeMap keys are Strings so we compare String(node.nodeId).
        const actionRoots = nodes.filter(
            (node) => triggerNodeMap.has(String(node.nodeId))
        );

        // Also include Reuse Automation nodes connected directly to the model node
        // (model -> Reuse Automation without a trigger in between). These are valid
        // root nodes for code generation -- they run unconditionally when called.
        const directReuseRoots = nodes.filter(
            (node) => node.type === "action_to_do" &&
                node.left && node.left.type === "model"
        );

        const allRoots = [...actionRoots, ...directReuseRoots];
        if (allRoots.length) return allRoots;

        // Fallback: ALL nodes that have no incoming connection (no left parent).
        const fallbackRoots = nodes.filter((node) => !node.left);
        return fallbackRoots.length ? fallbackRoots : [];
    }

    buildFlowLines(startNode, variables) {
        if (!startNode) {
            return [];
        }

        const lines = [];
        // Build a fast lookup: nodeId → Drawflow node name (e.g. 'Search', 'Loop')
        const flowData = this.getCurrentFlowData() || {};
        const nodeNameMap = {};
        Object.values(flowData).forEach(n => {
            if (n.data?.nodeId != null) nodeNameMap[n.data.nodeId] = n.name || '';
        });

        // Nodes that are guaranteed to have already been emitted along every
        // execution path that can reach this point. Guards against a node
        // that is wired from more than one always-executed predecessor (e.g.
        // two connections converging on the same Mail node) being walked --
        // and therefore having its code, and its real-world side effect like
        // sending an email, duplicated -- once per incoming path.
        //
        // The set is threaded through by reference across purely sequential
        // edges (nextNodes / the search auto-loop body), so later siblings
        // see what earlier ones already emitted. It is cloned before
        // recursing into mutually exclusive branches (IF/ELSE, try/except)
        // so that one branch's emissions never suppress the other branch's
        // -- only one of them runs at a time, so a node shared by both
        // branches legitimately needs its own code in each.
        const traverse = (node, indentationLevel, parentArray = [], guarded = new Set()) => {
            if (!node) return;
            if (guarded.has(node.nodeId)) return;
            guarded.add(node.nodeId);

            const variablesInScope = variables.filter(item => item.scopeId === node.nodeId);
            for (const item of variablesInScope) {
                if (item.code) lines.push(`${indentationLevel}${item.code}`);
            }

            if (node.code) {
                const splitLines = node.code.split('\n');
                for (const line of splitLines) {
                    lines.push(`${indentationLevel}${line}`);
                }
            }

            if (node.isParent) {
                // Handle Condition/Loop/TryCatch nodes
                const children1 = Array.isArray(node.child1) ? node.child1 : (node.child1 ? [node.child1] : []);
                const children2 = Array.isArray(node.child2) ? node.child2 : (node.child2 ? [node.child2] : []);
                const nextNodes = Array.isArray(node.right) ? node.right : (node.right ? [node.right] : []);

                if (node.isTryCatch) {
                    // ── Try block ────────────────────────────────────────────
                    // node.code already contains "try:"
                    if (children1.length > 0) {
                        const lenBefore = lines.length;
                        const tryGuard = new Set(guarded);
                        children1.forEach(child => traverse(child, indentationLevel + "    ", [...parentArray, node], tryGuard));
                        if (lines.length === lenBefore) {
                            lines.push(`${indentationLevel}    pass`);
                        }
                    } else {
                        lines.push(`${indentationLevel}    pass`);
                    }

                    // ── Except / Catch block ──────────────────────────────────
                    // else_setup_code holds "except SomeError as err:"
                    const exceptHeader = node.else_setup_code || "except Exception as error:";
                    lines.push(`${indentationLevel}${exceptHeader}`);
                    // Bug 1 fix: inject "var_<name> = <name>" alias so that processValue
                    // token output (var_error) resolves correctly at Python runtime.
                    const exceptVarMatch = exceptHeader.match(/as\s+(\w+)\s*:/);
                    if (exceptVarMatch) {
                        const rawErrVar = exceptVarMatch[1];
                        lines.push(`${indentationLevel}    var_${rawErrVar} = ${rawErrVar}`);
                    }
                    if (children2.length > 0) {
                        const lenBefore = lines.length;
                        const catchGuard = new Set(guarded);
                        children2.forEach(child => traverse(child, indentationLevel + "    ", [...parentArray, node], catchGuard));
                        if (lines.length === lenBefore) {
                            lines.push(`${indentationLevel}    pass`);
                        }
                    } else {
                        lines.push(`${indentationLevel}    pass`);
                    }

                    // ── Continue after try/except ────────────────────────────
                    nextNodes.forEach(next => traverse(next, indentationLevel, parentArray, guarded));

                } else {
                    // Branch 1 (IF / Loop Body)
                    if (children1.length > 0) {
                        const branch1Guard = new Set(guarded);
                        children1.forEach(child => traverse(child, indentationLevel + "    ", [...parentArray, node], branch1Guard));
                    } else if (node.isLoop) {
                        lines.push(`${indentationLevel}    pass`);
                    } else {
                        // Logic requires something in the IF block if it's a condition
                        lines.push(`${indentationLevel}    pass`);
                    }

                    // Branch 2 (ELSE)
                    if (children2.length > 0 || node.else_setup_code) {
                        if (node.else_setup_code) {
                            lines.push(`${indentationLevel}${node.else_setup_code}`);
                            const complementVar = node.else_setup_code.split('=')[0].trim();
                            lines.push(`${indentationLevel}if ${complementVar}:`);
                        } else {
                            lines.push(`${indentationLevel}else:`);
                        }
                        if (children2.length > 0) {
                            const branch2Guard = new Set(guarded);
                            children2.forEach(child => traverse(child, indentationLevel + "    ", [...parentArray, node], branch2Guard));
                        } else {
                            lines.push(`${indentationLevel}    pass`);
                        }
                    }

                    // Continue after the branch
                    nextNodes.forEach(next => traverse(next, indentationLevel, parentArray, guarded));
                }

            } else {
                // Regular node
                const nextNodes = Array.isArray(node.right) ? node.right : (node.right ? [node.right] : []);

                // Auto-loop: when this node is a Search node that returns a recordset,
                // wrap all subsequent nodes so they run once per record.
                let searchVarName = null;

                // Primary: parse variable name from the node's code "varname = env['m'].search(...)"
                const isSearchByName = nodeNameMap[node.nodeId] === 'Search';
                if (isSearchByName && node.code) {
                    const m = node.code.match(/^(\w+)\s*=\s*env\[/m);
                    if (m) searchVarName = m[1];
                }

                // Fallback: find a recordset variable whose scope is this node
                if (!searchVarName) {
                    const rv = variablesInScope.find(v => v.variable_type === 'recordset' && v.variable_name);
                    if (rv) searchVarName = rv.variable_name;
                }

                if (searchVarName && nextNodes.length > 0) {
                    lines.push(`${indentationLevel}for current_record in ${searchVarName}:`);
                    nextNodes.forEach(next => traverse(next, indentationLevel + '    ', parentArray, guarded));
                } else {
                    nextNodes.forEach(next => traverse(next, indentationLevel, parentArray, guarded));
                }
            }
        };

        traverse(startNode, "");
        return lines;
    }

    findDuplicateTriggerType(flowData) {
        const typeCounts = {};
        Object.values(flowData).forEach(node => {
            const triggerType = node.data?.trigger_type;
            if (node.data?.type === 'action' && triggerType) {
                typeCounts[triggerType] = (typeCounts[triggerType] || 0) + 1;
            }
        });
        return Object.keys(typeCounts).find(type => typeCounts[type] > 1);
    }

    showCode() {
        this.state.showCode = true;
    }

    async autoSaveDrawFlow(values) {
        const flow_data = this.editor.export();
        this.editorState.value[0].flow_data = flow_data
        this.resetTestVisuals();
        await this.write({flow_data});
    }

    dragStart(event, type) {
        if (event.type === "touchstart") {
            const mobile_item_selec = event.target.closest(".drag-drawflow").getAttribute('data-node');
        } else {
            event.dataTransfer.setData("record", this.state.model_id);
            const target = event.currentTarget || event.target;
            event.dataTransfer.setData("action", target.getAttribute('data-action'));
            event.dataTransfer.setData("node", target.getAttribute('data-node'));
            event.dataTransfer.setData("type", target.getAttribute('data-type'));
            event.dataTransfer.setData("trigger_type", target.getAttribute('data-trigger_type'));
        }
    }

    dragStartButtonClick(ev) {
        if (this.state.isGenericReusable) {
            ev.preventDefault();
            return;
        }
        this.dragStart(ev, 'functionCall');
    }

    dragStartTrigger(ev, action) {
        if (this.isTriggerUsed(action)) {
            ev.preventDefault();
            this.showDuplicateTriggerMessage(action);
            return;
        }
        this.dragStart(ev, action.name);
    }

    showDuplicateTriggerMessage(action) {
        this.notification.add({
            title: "Trigger already added",
            message: `${action.name} is already part of this automation. Each trigger may appear only once.`,
            type: "notification_panel",
            notificationType: "warning",
        });
    }

    allowDrop(ev) {
        ev.preventDefault();
    }

    async withCanvasBusy(message, fn) {
        if (this.state.canvasBusy) {
            return undefined;
        }
        this.state.canvasBusy = true;
        this.state.canvasBusyMessage = message || "Working...";
        try {
            return await fn();
        } finally {
            if (owl.status(this) !== 'destroyed') {
                this.state.canvasBusy = false;
                this.state.canvasBusyMessage = "";
            }
        }
    }

    mountComponent(component, ref, props) {
        const app = new App(component, {props, env: this.env});
        this.nodeApps.set(app, ref);
        app.mount(ref).catch((error) => {
            // The app was discarded (canvas re-imported / view left) while its
            // async onWillStart was still pending: the failed mount is expected.
            if (!this.nodeApps.has(app)) {
                return;
            }
            this.nodeApps.delete(app);
            console.error("Workflow node could not be mounted:", error);
        });
        return app;
    }

    /**
     * Destroys node roots. Owl's scheduler drops the fibers of destroyed nodes,
     * so a mount still waiting on its RPCs is cancelled instead of completing on
     * detached DOM, and each node runs its onWillUnmount (which unregisters its
     * env.bus / env.context listeners).
     *
     * @param {boolean} [detachedOnly] only destroy roots whose DOM is already
     *      gone (single node removed), instead of the whole canvas.
     */
    destroyNodeApps(detachedOnly = false) {
        for (const [app, ref] of this.nodeApps) {
            if (detachedOnly && ref?.isConnected) {
                continue;
            }
            this.nodeApps.delete(app);
            try {
                app.destroy();
            } catch (error) {
                console.warn("Workflow node app could not be destroyed:", error);
            }
        }
    }

    getContext() {
        return {
            modelName: this.state.model_name,
            modelState: this.state.modelState,
            trigger: this.state.trigger,
            // Exposes trigger type (e.g. 'time') so child components such as
            // the Condition node can adapt their UI for cron-mode workflows.
            triggerType: this.state.triggerType,
        }
    }

    get scope() {
        try {
            const scopeId = this.state.selectedVariable.scopeId
            const data = this.getCurrentFlowData();
            const node = Object.values(data).find(item => item.data.nodeId === scopeId);
            return node || null
        } catch (e) {
            //TODO: handle error;
        }
    }

    get customTriggerProps() {
        const props = {
            back: this.resetCustomTrigger.bind(this),
            model: this.state.model_id,
            updateActions: this.updateActions.bind(this),
            triggers: this.state.actions,
            editTriggerId: this.state.editTriggerId || null,
        }
        return props
    }

    resetCustomTrigger() {
        this.state.customTrigger = false;
        this.state.editTriggerId = null;
    }

    async updateActions() {
        this.state.actions = await this.orm.searchRead('work.function', [], ['name', 'id', 'icon', 'model_id', 'func_name', 'trigger_type'])
    }

    onCronFieldChange(field, ev, type = 'string') {
        let value = ev.target.value;
        if (type === 'float') value = parseFloat(value) || 0;
        if (type === 'int') value = parseInt(value) || 0;
        this.setCronField(field, value);
    }

    /**
     * `time_trigger_time` is stored as a 24h decimal float (e.g. 14.5 = 14:30)
     * so the backend cron math (create_cron) doesn't need to change. This
     * getter derives the 12-hour display (hour/minute/AM-PM) from it.
     */
    get cronTimeParts() {
        const total = this.state.cronTime || 0;
        let hour24 = Math.floor(total);
        let minute = Math.round((total - hour24) * 60);
        if (minute === 60) {
            minute = 0;
            hour24 += 1;
        }
        hour24 = ((hour24 % 24) + 24) % 24;
        const ampm = hour24 >= 12 ? 'PM' : 'AM';
        let hour12 = hour24 % 12;
        if (hour12 === 0) hour12 = 12;
        return { hour12, minute, ampm };
    }

    /**
     * Handles a change on any of the 12-hour time selects (hour/minute/AM-PM),
     * recombines all three parts and converts back to the 24h decimal float
     * expected by time_trigger_time.
     *
     * @param {string} part - one of: hour12/minute/ampm
     * @param {Event}  ev
     */
    onCronTimePartChange(part, ev) {
        const current = this.cronTimeParts;
        let { hour12, minute, ampm } = current;
        if (part === 'hour12') hour12 = parseInt(ev.target.value) || 12;
        if (part === 'minute') minute = Math.max(0, Math.min(59, parseInt(ev.target.value) || 0));
        if (part === 'ampm') ampm = ev.target.value;

        let hour24 = hour12 % 12;
        if (ampm === 'PM') hour24 += 12;
        const value = hour24 + (minute / 60);
        this.setCronField('time_trigger_time', value);
    }

    get variableDetailProps() {
        const props = {
            variable: this.state.selectedVariable,
            back: this.resetVariableSelection.bind(this),
            edit: this.editVariable.bind(this),
            delete: this.deleteVariable.bind(this),
            usedNodes: this.usedNodes
        }
        const scope = this.scope
        if (scope) props['scope'] = scope
        return props
    }

    get flowCanvasNodes() {
        const data = this.editorValue?.[0]?.flow_data?.drawflow?.Home?.data || {};
        return Object.values(data);
    }

    get usedNodes() {
        const nodeIds = this.state.selectedVariable?.usedIn;
        if (nodeIds && nodeIds.length > 0) {
            const nodes = this.flowCanvasNodes.filter(item => nodeIds.includes(item.data.nodeId));
            return nodes;
        }
        return [];
    }

    get currentNode() {
        return this.flowCanvasNodes.find(node => node.id == this.state.selectedNodeID);
    }

    get globalWithAccessibleVariables() {
        return [...this.globalVariables, ...this.accessibleVariables,]
    }

    get globalVariables() {
        return this.env.globalVariables.context.variables || [];
    }

    makeVariable() {
        if (!this.currentNode || this.currentNode?.data.model.length > 0) {
            const message = !this.currentNode ? "You can't create a variable without selecting any block." : "You cant create a variable for model and trigger block.";
            this.dialogService.add(ConfirmationPopup, {
                title: "Oops!",
                message: message,
                confirmText: "Ok, Got it",
                showCancel: false,
                image: "cyllo_workflow_automation/static/src/img/warning_popup.png"
            });

        } else {
            this.dialogService.add(VariableNode, {
                name: "Make Variable",
                fields: variableFields,
                variable: {scopeId: this.currentNode.data.nodeId},
                display_name: "Here you can create new variables. Name for this Variable that's unique within this automation.",
                variables: this.globalWithAccessibleVariables,
                identifiers: this.automationIdentifiers,
                onConfirm: (fieldState, code) => {
                    const currentVariableContext = this.env.variables.context;
                    const variables = currentVariableContext.variables || []
                    this.env.variables.setContext({
                        variables: [...variables, owl.reactive({
                            id: new Date().toISOString(),
                            modelId: undefined,
                            scopeId: this.currentNode.data.nodeId, ...fieldState,
                            class: this.buttonClass,
                            code,
                            usedIn: [],
                            delete: true,
                        })]
                    })
                    this.setVariableState(this.env.variables.context.variables);
                    this.saveHistory();
                }
            })
        }
    }

    editVariable(variable) {
        const {
            variable_name,
            variable_type,
            type,
            variable_value,
            scopeId
        } = variable
        const nodes = this.flowCanvasNodes;
        const scopedNode = nodes.find(nod => nod.data.nodeId === scopeId);
        if (!scopedNode) {
            this.dialogService.add(ConfirmationPopup, {
                title: "Oops!",
                message: "The variable scope node is no longer available.",
                confirmText: "Ok, Got it",
                showCancel: false,
                image: "cyllo_workflow_automation/static/src/img/warning_popup.png"
            });
            return;
        }
        this.state.selectedNodeID = scopedNode.id;
        this.dialogService.add(VariableNode, {
            name: "Edit Variable",
            mode: "edit",
            variables: this.globalWithAccessibleVariables,
            display_name: "Here you can edit variables. Name for this Variable that's unique within this automation.",
            variable: {
                variable_name,
                variable_type,
                type,
                variable_value,
                scopeId
            },
            identifiers: this.automationIdentifiers,
            onConfirm: (fieldState, code) => {
                const currentVariableContext = this.env.variables.context;
                const variables = currentVariableContext.variables;
                const editedVariable = variables.find(item => item.id === variable.id);
                Object.assign(editedVariable, {...fieldState, code})
                this.setVariableState(variables);
                this.saveHistory();
            }
        })
        this.state.selectedNodeID = undefined;
    }

    deleteVariable(variable) {
        //FiXME: WWW
        if (variable.usedIn.length > 0) {
            this.dialogService.add(ConfirmationPopup, {
                title: "Oops!",
                message: "Used variable. Clear dependencies before deleting.",
                confirmText: "Ok, Got it",
                showCancel: false,
                image: "cyllo_workflow_automation/static/src/img/warning_popup.png"
            });
        } else {
            const variables = this.state.variables.filter(item => item.id !== variable.id);
            this.setVariableState(variables)
            this.env.variables.setContext({variables: [...variables]})
            this.saveHistory();
        }
    }

    selectVariable(variable) {
        this.state.selectedVariable = variable;
    }

    resetVariableSelection() {
        this.state.selectedVariable = undefined;
    }

    setVariableState(variables) {
        this.state.variables = [...variables]
    }

    removeVariables(nodeID) {
        const variables = this.state.variables.filter(item => item.scopeId !== nodeID);
        this.setVariableState(variables);
        this.env.variables.setContext({variables: [...variables]})
    }

    getSerializableVariables() {
        const variables = this.state.variables || [];
        return variables.map(variable => ({...variable}));
    }

    getSerializableImports() {
        return this.imports.map(statement => ({
            importStatement: statement.importStatement,
            childStatement: (statement.childStatement || []).map(child => ({...child})),
        }));
    }

    async addNodeToDrawFlow(name, pos_x, pos_y, selectedValue, record, action, type, trigger_type) {
        return this.withCanvasBusy(
            `Adding ${name === 'model' ? 'model' : name} node...`,
            () => this._addNodeToDrawFlow(name, pos_x, pos_y, selectedValue, record, action, type, trigger_type),
        );
    }

    async _addNodeToDrawFlow(name, pos_x, pos_y, selectedValue, record, action, type, trigger_type) {
        if (this.editor.editor_mode === 'fixed') return false;
        if (type === 'trigger') {
            this.state.trigger = name || "";
            this.state.triggerType = trigger_type || "";
        }
        // Calculate position
        pos_x = pos_x * (this.editor.precanvas.clientWidth / (this.editor.precanvas.clientWidth * this.editor.zoom)) - (this.editor.precanvas.getBoundingClientRect().x * (this.editor.precanvas.clientWidth / (this.editor.precanvas.clientWidth * this.editor.zoom)));
        pos_y = pos_y * (this.editor.precanvas.clientHeight / (this.editor.precanvas.clientHeight * this.editor.zoom)) - (this.editor.precanvas.getBoundingClientRect().y * (this.editor.precanvas.clientHeight / (this.editor.precanvas.clientHeight * this.editor.zoom)));
        // Create node in backend
        const nodeId = await this.createNodeInBackend(name, type, trigger_type);
        const cur_rec = this.env.globalVariables.context.variables.find(item => item.variable_name === "current_record")
        // Define common properties
        const commonProps = {
            name,
            nodeId,
            model: [],
            primary_model_id: this.state.model_id,
            primary_model_name: this.state.model_name,
            updateImports: this.updateImportStatements.bind(this),
            work_auto_id: this.id,
        };
        this.env.bus.trigger("UPDT-PRIMARY", {model_id: this.state.model_id})
        let specificProps = {};
        let label = name;
        let left = 1;
        let right = 1;
        switch (name) {
            case 'model':
                specificProps.type = name;
                specificProps.model = [parseInt(record), 'ir.model'];
                label = `model_${record} model_rec`;
                left = 0;
                cur_rec.modelId = this.state.model_id;
                cur_rec.modelName = this.state.model_name;
                break;
            case 'Search':
            case 'Create':
            case 'Write':
            case 'Filter':
            case 'Iteration':
            case 'Date':
            case 'Button Click':
            case 'Code':
            case 'Function Args':
            case 'Mail':
            case 'SMS':
            case 'WhatsApp':
            case 'Activity':
            case 'Follower':
            case 'Mapped':
            case 'Assignment':
            case 'Window':
            case 'Duplicate':
            case 'Webhook':
                specificProps.type = "action_to_do";
                break;
            case 'Warning':
                specificProps.type = "action_to_do";
                left = 1;
                right = 0;
                break;
            case 'Condition':
            case 'Try Catch':
                specificProps.type = "action_to_do";
                right = 3;
                break;
            case 'Loop':
                specificProps.type = "action_to_do";
                right = 1;
                break;
            case 'Reuse Automation':
                specificProps.type = "action_to_do";
                break;
            default:
                specificProps.type = "action";
                specificProps.ttype = name;
                specificProps.trigger_type = trigger_type;
                specificProps.model = [parseInt(action), "work.function"];
                label = action;
                break;
        }

        // DO NOT inherit this.state.triggerType for action_to_do nodes.
        // The correct trigger branch is resolved at code-generation time by
        // updateCode() via the context tree (triggerNodeMap + getFlowRoots).
        // Stamping every action_to_do with the last-dragged global triggerType
        // caused all branches to share the same guard (e.g. always 'field_change')
        // regardless of which trigger they were actually connected under.
        const newProps = {...commonProps, ...specificProps};
        const uniqueIdentifier = name + '__' + nodeId

        // Register node
        this.editor.registerNode(uniqueIdentifier, ModelComponent, newProps, {});

        // Add node to editor
        await this.editor.addNode(name, left, right, pos_x, pos_y, label, {...newProps}, uniqueIdentifier, 3);

        // Update component
        let {component, ref, props} = this.data
        props = {...props, ...newProps};
        this.mountComponent(component, ref, props);
    }

    drop(ev) {
        if (this.state.canvasBusy) {
            ev.preventDefault();
            return;
        }
        if (ev.type === "touchend") {
            var parentdrawflow = document.elementFromPoint(mobile_last_move.touches[0].clientX, mobile_last_move.touches[0].clientY).closest("#drawflow");
            if (parentdrawflow != null) {
                this.addNodeToDrawFlow(mobile_item_selec, mobile_last_move.touches[0].clientX, mobile_last_move.touches[0].clientY);
            }
            let mobile_item_selec = '';
        } else {
            ev.preventDefault();
            let data = ev.dataTransfer.getData("node");
            let record = ev.dataTransfer.getData("record");
            let action = ev.dataTransfer.getData("action");
            const type = ev.dataTransfer.getData("type");
            const trigger_type = ev.dataTransfer.getData("trigger_type");
            if (data && data !== 'null') {
                if (type === 'trigger') {
                    this.state.trigger = data;
                    this.state.triggerType = trigger_type;
                }
                this.mainBlk.el.querySelector("#trigger_blocks").classList.remove('show')
                const triggerHeader = this.mainBlk.el.querySelector('.trigger.w_card-header');
                if (triggerHeader) {
                    triggerHeader.classList.add('collapsed');
                }
                const selectedValue = this.state.model;
                this.addNodeToDrawFlow(data, ev.clientX, ev.clientY, selectedValue, record, action, type, trigger_type);
            }
        }
    }

    async createNodeInBackend(name, type, trigger_type = null) {
        type = type === "null" ? "node" : type;
        const [id] = await this.orm.create(
            "node.struct",
            [
                {
                    name,
                    work_auto_id: this.id,
                    model_id: this.state.model_id,
                    type,
                    trigger_type,
                    ttype: (type === 'trigger' || type === 'action') ? name : null,
                },
            ],
        );
        return id;
    }

    async onSelectPrimary(ev) {
        if (!ev) return;
        // const model_data = await this.orm.read('ir.model', [ev[0].id], ['display_name', 'model']);
        const model_data = await this.orm.searchRead('ir.model', [["id", "=", ev[0].id]], ['display_name', 'model'])
        this.state.model = ev[0].display_name ? ev[0].display_name : model_data[0].display_name;
        this.state.model_id = ev[0].id;
        this.state.model_name = model_data[0].model;
        this.settingModelState(ev[0].id);
        await this.updatePrimaryModel(ev[0].id);
        const name = "model"
        const action = null
        const precanvasRect = this.editor.precanvas.getBoundingClientRect();
        const defaultX = precanvasRect.left + precanvasRect.width / 35;
        const defaultY = precanvasRect.top + precanvasRect.height / 5 - 8;
        this.addNodeToDrawFlow(name, defaultX, defaultY, this.state.model, this.state.model_id, action, "model")
    }

    updatePrimaryModel(model_id) {
        this.orm.write("work.auto", [this.id], {model_id});
    }

    settingModelState(model_id) {
        const modelState = this.state.modelState.filter(model => model.type !== 'primary')
        this.state.modelState = [{
            id: 0,
            model_id,
            type: 'primary'
        }, ...modelState]
    }

    getDomain() {
        return []
    }

    getContextNodes() {
        return this.env.context?.context?.nodes || [];
    }

    getValidRecordIds(ids = []) {
        return ids
            .map((id) => {
                if (typeof id === "number" && Number.isInteger(id) && id > 0) {
                    return id;
                }
                if (typeof id === "string" && /^\d+$/.test(id)) {
                    const parsedId = Number.parseInt(id, 10);
                    return parsedId > 0 ? parsedId : null;
                }
                return null;
            })
            .filter((id) => id !== null);
    }

    getCurrentRecordIds() {
        return this.getValidRecordIds([this.id]);
    }

    hasPersistedCurrentRecord() {
        return this.getCurrentRecordIds().length > 0;
    }

    shouldDeleteCurrentEmptyRecord() {
        return !this.getContextNodes().length && this.hasPersistedCurrentRecord();
    }

    async unlinkCurrentRecordIfValid() {
        const recordIds = this.getCurrentRecordIds();
        if (!recordIds.length) {
            return false;
        }
        await this.orm.unlink("work.auto", recordIds);
        return true;
    }

    async deleteEmpty() {
        if (this.shouldDeleteCurrentEmptyRecord()) {
            await this.unlinkCurrentRecordIfValid();
        }
    }

    deleteEmptyRecord(action, message) {
        if (this.shouldDeleteCurrentEmptyRecord()) {
            this.dialogService.add(ConfirmationPopup, {
                title: _t("Are you sure"),
                message: message || _t("If you leave this page,This empty record will be deleted"),
                confirmText: _t("Yes, proceed"),
                cancelText: _t("No, cancel"),
                onConfirm: async () => {
                    await this.unlinkCurrentRecordIfValid();
                    this.action.doAction(action);
                },
                onCancel: () => {
                },
            })
        } else {
            this.action.doAction(action)
        }
    }

    async navigatePage(navigateId) {
        const action = {
            type: "ir.actions.client",
            tag: "automation_view",
            context: {
                id: navigateId
            }
        }
        this.deleteEmptyRecord(action)

    }

    async handleClickBack(e) {
        e.preventDefault()
        // const domain = !this.env.context.context.nodes.length ? [['id', '!=', this.id]] : [];
        const action = {
            type: "ir.actions.act_window",
            res_model: "work.auto",
            views: [[false, "workflowCard"], [false, "list"], [false, "form"]],
            target: "main",
            name: "Workflow Automation",
            // domain,
            context: {delete_node_id: this.shouldDeleteCurrentEmptyRecord() ? this.getCurrentRecordIds()[0] : false}
        }
        const message = _t("If you go back, This record will be deleted");
        this.deleteEmptyRecord(action, message)
    }

    static components = {
        Many2XAutocomplete,
        Many2OneField,
        Record,
        VariableNode,
        Many2ManyTagsField,
        FoldOut,
        VariableItem,
        VariableDetails,
        CustomTrigger,
        WorkPager,
        SaveLoading,
        TestResultPanel,
    }
}

WorkFlowAuto.template = "client_action.automation_view"
registry.category("actions").add("automation_view", WorkFlowAuto)
