/** @odoo-module **/
import {
    Component,
    onMounted,
    useState,
    useEffect,
    useRef,
    onWillStart,
    onWillUpdateProps,
    useExternalListener,
} from "@odoo/owl";
import {
    useService,
    useOwnedDialogs
} from "@web/core/utils/hooks";
import {
    CylloStudioDropdown
} from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import {
    registry
} from "@web/core/registry";
import {
    handleUndoRedo
} from "@cyllo_studio/js/utils/undo_redo_utils";
import {
    ExpressionEditorDialog
} from "@web/core/expression_editor_dialog/expression_editor_dialog";
import {
    _t
} from "@web/core/l10n/translation";
import {
    getWidgetTypes,
    getWidgetSupport
} from "@cyllo_studio/js/view_editor/widget";
import { MultiSelectDropDown } from "@cyllo_studio/js/view_editor/dropdown/multi_select_dropdown/multi_select_dropdown";
import {
    DomainSelectorDialog
} from "@web/core/domain_selector_dialog/domain_selector_dialog";

import {
    SelectionFieldValue
} from "@cyllo_studio/js/view_editor/components/selection_field_widget_values/selection_field_value_widget";
import {
    usePopover
} from "@web/core/popover/popover_hook";
import {
    ModelFieldSelectorPopover
} from "@web/core/model_field_selector/model_field_selector_popover";
import {
    useLoadFieldInfo
} from "@web/core/model_field_selector/utils";

import {
    CodeEditor
} from "@web/core/code_editor/code_editor";

import {
    ComputeDialog
} from "@cyllo_studio/js/view_editor/aside_bar/dialog/compute_dialog"

import {
    DateTimePicker
} from "@web/core/datetime/datetime_picker";

import { ConstraintDialog } from "@cyllo_studio/js/view_editor/aside_bar/dialog/constraint_dialog";



export class FieldProperties extends Component {
    static template = "cyllo_studio.FieldProperties";
    static props = {
        attr: {
            type: Object,
            optional: true
        },
        allFields: {
            type: Object,
            optional: true
        },
        type: {
            type: String,
            optional: true
        },
        name: {
            type: String,
            optional: true
        },
        string: {
            type: String,
            optional: true
        },
        label: {
            type: String,
            optional: true
        },
        widget: {
            type: String,
            optional: true
        },
        fieldType: {
            type: String,
            optional: true
        },
        context: {
            type: String,
            optional: true
        },
        viewType: {
            type: String,
            optional: true
        },
        model: {
            type: String,
            optional: true
        },
        viewId: {
            type: Number,
            optional: true
        },
        create: {
            type: Boolean,
            optional: true
        },
        placeholder: {
            type: String,
            optional: true
        },
        help: {
            type: String,
            optional: true
        },
        edit: {
            type: Boolean,
            optional: true
        },
        readonly: {
            type: String,
            optional: true
        },
        recordData: {
            type: Object,
            optional: true
        },
        dynamic_placeholder: {
            type: String,
            optional: true
        },
        column_invisible: {
            type: String,
            optional: true
        },
        invisible: {
            type: String,
            optional: true
        },
        required: {
            type: String,
            optional: true
        },
        related_model: {
            type: String,
            optional: true
        },
        relational_model: {
            type: [Object, String],
            optional: true
        },
        domain: {
            type: String,
            optional: true
        },
        field_path: {
            type: String,
            optional: true
        },
        label_path: {
            type: String,
            optional: true
        },
        path: {
            type: String,
            optional: true
        },
        widget_types: {
            type: Object,
            optional: true
        },
        options: {
            type: Object,
            optional: true
        },
        position: {
            type: String,
            optional: true
        },
        item_type: {
            type: String,
            optional: true
        },
        field_info: {
            type: Object,
            optional: true
        },
        sibling: {
            type: Boolean,
            optional: true
        },
        sibling_edit: {
            type: Boolean,
            optional: true
        },
        mode: {
            type: [String, Object, Number],
            optional: true
        },
        activeFields: {
            type: Object,
            optional: true
        },
        measure: {
            type: [String, Object, Array],
            optional: true
        },
        isMenu: {
            type: Boolean,
            optional: true
        },
        hasColorPicker: {
            type: Boolean,
            optional: true
        },
        progressAttributes: {
            type: Object,
            optional: true
        },
        envModel: {
            type: [String, Object],
            optional: true
        },
        ribbonElement: {
            type: Object,
            optional: true
        },
        MetaData: {
            type: Object,
            optional: true
        },
        calendar_info: {
            type: Object,
            optional: true
        },
        isFieldTag: {
            type: Boolean,
            optional: true
        },
        colorPickerPath: {
            type: String,
            optional: true
        },
        optional: {
            type: String,
            optional: true
        },
        fieldNodes: {
            type: Object,
            optional: true
        },
    };
    setup() {

        this.sqlConstraints = useState([]);

        this.actionService = useService("action");
        this.action = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.fieldService = useService("field");
        this.popover = usePopover(ModelFieldSelectorPopover, {
            popoverClass: "o_model_field_selector_popover",
        });
        this.loadFieldInfo = useLoadFieldInfo();
        this.fieldsInfo = this.props.allFields || {};
        this.notification = useService("effect");
        this.addDialog = useOwnedDialogs();
        this.ref = useRef('cy-Properties')
        this.prevState = useState({
            ...this.props
        })
        this.StatusBarValues = useState({
            clickable: false,
            foldField: '',
            statusbarVisible: '',
            group_ids: [],
            invisible: 'False',
            defaultValue: 'True',
        })
        this.state = useState({
            xStudio: 0,
            create: this.props.create || false,
            field_names: [],
            item_name: null,
            name: this.props.name,
            string: this.props.string,
            related_model: this.props.related_model || this.getRelatedModelFromField(),
            widget: this.props.widget,
            help: this.props.help,
            placeholder: this.props.placeholder,
            dynamic_placeholder: this.props.dynamic_placeholder || '',
            dynamic_placeholder_field: null, // Store the actual field object
            optional: this.props?.attr?.optional || '',
            column_invisible: this.props.column_invisible || 'false',
            invisible: this.props.invisible || 'false',
            readonly: this.props.readonly || 'false',
            required: this.props.required || 'false',
            relatedModel: this.props.related_model || '',
            relatedModelField: "",
            field_path: this.props.field_path,
            label_path: this.props.label_path,
            edited: false,
            recordData: this.props.recordData || {},
            isPlaceholderFocused: false,
            existedField: false,
            fieldType: [
                "Char",
                "Text",
                "Html",
                "Integer",
                "Float",
                "Date",
                "Datetime",
                "Binary",
                "Selection",
                "Boolean",
                "Many2one",
                "One2many",
                "Many2many",
            ],
            field: 'existing',
            values: [],
            selectionValues: [],
            SelectedOptions: [],
            models: [],
            domain: this.props.domain || '',
            inverseFields: [],
            selectedFieldType: this.props.fieldType || 'char',
            widget_types: [],
            context: '{}',
            sibling: this.props.sibling,
            isStatusBar: false,
            related_model_field: [],
            is_computed: false,
            compute_dependencies: "",
            compute_code: "",
            default_value: "",
            constraintEnabled: false,
            pythonConstraint: null,
        });
        if (!this.props.edit) {
            this.state.field = "new";
        }
        // Initialize dynamic_placeholder_field and resolve value if dynamic_placeholder is set
        if (this.state.dynamic_placeholder && this.props.allFields) {
            const fieldInfo = this.props.allFields[this.state.dynamic_placeholder];

            if (fieldInfo) {
                let fieldValue = this.state.recordData?.[this.state.dynamic_placeholder];

                if (fieldValue && typeof fieldValue === 'object' && 'display_name' in fieldValue) {
                    fieldValue = fieldValue.display_name;
                }

                this.state.dynamic_placeholder_field = {
                    name: this.state.dynamic_placeholder,
                    string: fieldInfo.string || this.state.dynamic_placeholder,
                    type: fieldInfo.type,
                    value: fieldValue
                };
            }
        }
        this.state.show_compute_section =
            this.props.edit === true &&
            (this.props.name || "").startsWith("x_studio_");
        if (this.props.attr) {
            this.state.is_computed = this.props.attr.is_computed || false;
            this.state.compute_dependencies = this.props.attr.depends || "";
            this.state.compute_code = this.props.attr.compute || "";
        }
        this.selectedWidget = this.props.widget === 'False' ? '' : this.props.widget || ''
        onWillUpdateProps((nextProps) => {
            if (nextProps.name !== this.lastFieldName) {
                // Reset dynamic state when switching fields
                this.state.default_value = "";
                this.state.values = [];
                this.state.selectionValues = [];
                this.state.SelectedOptions = [];
                this.state.field = nextProps.field_info && nextProps.field_info.selection ? "existing" : "new";
                this.state.dynamic_placeholder = '';

                this.lastFieldName = nextProps.name;
            }
            this.state.show_compute_section =
                this.props.edit === true &&
                (this.props.name || "").startsWith("x_studio_");
            this.state.name = nextProps.name
            this.state.string = nextProps.string

            let relatedModel = nextProps.related_model;
            if (!relatedModel && nextProps.name && nextProps.allFields) {
                const fieldInfo = nextProps.allFields[nextProps.name];
                if (fieldInfo?.relation) {
                    relatedModel = fieldInfo.relation;
                }
            }
            if (nextProps.field_info && nextProps.field_info.selection) {
                this.state.values = nextProps.field_info.selection;
                this.state.field = 'existing';
            } else if (nextProps.allFields && nextProps.name && nextProps.allFields[nextProps.name]?.selection) {
                this.state.values = nextProps.allFields[nextProps.name].selection;
                this.state.field = 'existing';
            } else if (!nextProps.field_info) {
                if (this.props.create || !nextProps.name) {
                    this.state.field = 'new';
                }
            }
            if (nextProps.dynamic_placeholder) {
                this.state.dynamic_placeholder = nextProps.dynamic_placeholder;

                const fieldInfo = nextProps.allFields?.[nextProps.dynamic_placeholder];
                if (fieldInfo) {
                    this.state.dynamic_placeholder_field = {
                        name: nextProps.dynamic_placeholder,
                        string: fieldInfo.string || nextProps.dynamic_placeholder,
                        type: fieldInfo.type
                    };
                }
            } else {
                this.state.dynamic_placeholder = '';
                this.state.dynamic_placeholder_field = null;
            }


            this.state.related_model = relatedModel;
            this.state.recordData = nextProps.recordData || {};
            this.state.widget = nextProps.widget
            if (nextProps.widget && nextProps.widget !== this.props.widget) {
                this.widgetOptionalFields(nextProps.widget, nextProps.options);
            }
            this.state.selectedFieldType = nextProps.fieldType
            this.state.help = nextProps.help
            this.state.placeholder = nextProps.placeholder
            this.state.dynamic_placeholder = nextProps.dynamic_placeholder;
            this.state.optional = nextProps.optional
            this.state.column_invisible = nextProps.column_invisible || 'false'
            this.state.invisible = nextProps.invisible || 'false'
            this.state.readonly = nextProps.readonly || 'false'
            this.state.required = nextProps.required || 'false'
            this.state.sibling = nextProps.sibling
            this.state.widget_types = getWidgetTypes(nextProps.fieldType);
            this.state.domain = nextProps.domain || '';
            if (nextProps.name !== this.props.name) {
                this.rpc("/cyllo_studio/get_default", {
                    model: nextProps.model,
                    field_name: nextProps.name,
                }).then((value) => {
                    this.state.default_value = value || "";
                });

            } else {
                this.state.default_value =
                    "default_value" in nextProps ? (nextProps.default_value ?? "") : "";
            }

        });

        useEffect(() => {
            if (this.props.edit === true && this.state.widget === 'statusbar') {
                this.loadStatusbarValues();
            }
        }, () => [this.props.edit, this.state.widget])

        // Add this useEffect in setup() after your existing useEffect blocks
        useEffect(() => {
            const loadConstraintsForField = async () => {
                if (this.props.edit && this.props.name && this.props.model) {
                    try {
                        // Load SQL constraints
                        const constraints = await this.rpc("/cyllo_studio/get_sql_constraints", {
                            model: this.props.model,
                            field_name: this.props.name,
                        });

                        // Clear existing constraints
                        this.sqlConstraints.splice(0, this.sqlConstraints.length);

                        // Load new SQL constraints
                        let hasSqlConstraints = false;
                        if (constraints && constraints.length > 0) {
                            this.sqlConstraints.push(...constraints);
                            hasSqlConstraints = true;
                        }

                        // Load Python constraints
                        let hasPythonConstraint = false;
                        try {
                            const pythonConstraintInfo = await this.rpc("/cyllo_studio/get_python_constraint", {
                                model: this.props.model,
                                field_name: this.props.name,
                            });

                            if (pythonConstraintInfo && pythonConstraintInfo.code && pythonConstraintInfo.deps) {
                                this.state.pythonConstraint = {
                                    deps: pythonConstraintInfo.deps,
                                    code: pythonConstraintInfo.code
                                };
                                hasPythonConstraint = true;
                            } else {
                                this.state.pythonConstraint = null;
                            }
                        } catch (error) {
                            this.state.pythonConstraint = null;
                        }

                        // Enable checkbox if either SQL or Python constraints exist
                        this.state.constraintEnabled = hasSqlConstraints || hasPythonConstraint;

                        const constraintTypes = [];
                        if (hasSqlConstraints) constraintTypes.push("SQL");
                        if (hasPythonConstraint) constraintTypes.push("Python");

                        if (constraintTypes.length > 0) {
                        } else {
                        }
                    } catch (error) {
                        console.error('Error loading constraints:', error);
                        this.sqlConstraints.splice(0, this.sqlConstraints.length);
                        this.state.pythonConstraint = null;
                        this.state.constraintEnabled = false;
                    }
                } else {
                    // Not in edit mode - clear constraints
                    this.sqlConstraints.splice(0, this.sqlConstraints.length);
                    this.state.pythonConstraint = null;
                    this.state.constraintEnabled = false;
                }
            };

            loadConstraintsForField();
        }, () => [this.props.edit, this.props.name, this.props.model]);

        onWillStart(async () => {
            if (this.props.edit) {

                this.state.field = "new";
                const result = this.props.name
                    ? await this.rpc("/cyllo_studio/get_default", {
                        model: this.props.model,
                        field_name: this.props.name,
                    })
                    : null;
                this.state.default_value = result || "";

                // Load SQL constraints
                const constraints = await this.rpc("/cyllo_studio/get_sql_constraints", {
                    model: this.props.model,
                    field_name: this.props.name,
                });

                // Clear existing constraints
                this.sqlConstraints.splice(0, this.sqlConstraints.length);

                // Load SQL constraints and check for Python constraints
                let hasSqlConstraints = false;
                if (constraints && constraints.length > 0) {
                    this.sqlConstraints.push(...constraints);
                    hasSqlConstraints = true;
                }

                // Load Python constraints
                let hasPythonConstraint = false;
                try {
                    const pythonConstraintInfo = await this.rpc("/cyllo_studio/get_python_constraint", {
                        model: this.props.model,
                        field_name: this.props.name,
                    });

                    if (pythonConstraintInfo && pythonConstraintInfo.code && pythonConstraintInfo.deps) {
                        this.state.pythonConstraint = {
                            deps: pythonConstraintInfo.deps,
                            code: pythonConstraintInfo.code
                        };
                        hasPythonConstraint = true;
                    } else {
                        this.state.pythonConstraint = null;
                    }
                } catch (error) {
                    this.state.pythonConstraint = null;
                }

                // Set constraint state based on loaded data
                this.state.constraintEnabled = hasSqlConstraints || hasPythonConstraint;

                const constraintTypes = [];
                if (hasSqlConstraints) constraintTypes.push(`${constraints.length} SQL`);
                if (hasPythonConstraint) constraintTypes.push("Python");

                if (constraintTypes.length > 0) {
                }
            }
        });
        useEffect(() => {
            const loadComputeInfo = async () => {
                if (this.props.edit && this.props.name && this.props.model) {
                    try {
                        const computeInfo = await this.rpc('/cyllo_studio/get_field_compute_info', {
                            model: this.props.model,
                            field_name: this.props.name
                        });

                        if (computeInfo && computeInfo.is_computed) {
                            this.state.is_computed = true;
                            this.state.compute_code = computeInfo.compute || "";
                            this.state.compute_dependencies = computeInfo.depends || "";
                        } else {
                            this.state.is_computed = false;
                            this.state.compute_code = "";
                            this.state.compute_dependencies = "";
                        }
                    } catch (error) {
                        console.error("Error loading compute info:", error);
                        this.state.is_computed = false;
                        this.state.compute_code = "";
                        this.state.compute_dependencies = "";
                    }
                } else {
                    this.state.is_computed = false;
                    this.state.compute_code = "";
                    this.state.compute_dependencies = "";
                }
            };

            loadComputeInfo();
        }, () => [this.props.edit, this.props.name, this.props.model]);

        onMounted(async () => {
            this.state.widget_types = getWidgetTypes(this.props.fieldType)
            this.action_area = document.querySelector(".o_action_manager")
            const fieldsData = await this.orm.searchRead(
                "ir.model.fields",
                [
                    ["model_id", "=", this.props.model]
                ],
                ["name"]
            );
            const studioFields = fieldsData.filter((field) =>
                field.name?.startsWith("x_studio")
            );
            this.state.xStudio = studioFields.length;
            this.state.models = await this.rpc('/cyllo_studio/get_non_abstract_non_transient_models');


            if (this.props.edit && this.props.name && this.props.model) {
                try {
                    const defaultResult = await this.rpc('/cyllo_studio/get_default', {
                        model: this.props.model,
                        field_name: this.props.name
                    });

                    if (defaultResult.success && defaultResult.default_value !== null) {
                        this.state.default_value = String(defaultResult.default_value);
                    }
                } catch (error) {
                }
            }

            if (this.props.field_info && this.props.field_info.selection) {
                this.state.values = this.props.field_info.selection;
                this.state.field = 'existing';
            } else if (this.props.edit && this.props.name && this.props.allFields) {
                const fieldInfo = this.props.allFields[this.props.name];
                if (fieldInfo && fieldInfo.selection) {
                    this.state.values = fieldInfo.selection;
                    this.state.field = 'existing';
                }
            }
            if (this.props.widget === "date" || this.props.fieldType === "date") {
                this.widgetOptionalFields("date", this.props.options);
            } else if (this.props.widget) {
                this.widgetOptionalFields(this.props.widget, this.props.options);
            }
        });

        var arrExistingFields = []
        Object.entries(this.props.allFields).forEach(([key, value]) => {
            arrExistingFields.push({
                name: key,
                string: value.string,
                type: value.type,
                relation: value.relation,
            })
        });
        this.existedField = arrExistingFields

    }
    //start
    onOptionalClick({ target }) {
        this.state.optional = target.checked ? 'hide' : 'show'
        this.autoSave();
    }
    get statusbarVisibleOptions() {
        // Use props.options if exists
        let visible = '';
        if (this.props.options && this.props.options.statusbar_visible) {
            visible = this.props.options.statusbar_visible;
        } else if (this.StatusBarValues.statusbarVisible) {
            visible = this.StatusBarValues.statusbarVisible;
        }

        const visibleArray = visible
            ? visible.split(',').map(v => v.trim()).filter(Boolean)
            : [];

        return visibleArray;
    }

    async loadStatusbarValues() {
        try {
            // Load selection values for the field
            if (this.props.field_info && this.props.field_info.selection) {
                this.state.values = this.props.field_info.selection;
            } else if (this.props.allFields && this.props.name) {
                const fieldInfo = this.props.allFields[this.props.name];
                if (fieldInfo && fieldInfo.selection) {
                    this.state.values = fieldInfo.selection;
                }
            }

            // Load currently visible options from widget options
            if (this.props.options && this.props.options.statusbar_visible) {
                const visibleStr = this.props.options.statusbar_visible;
                // statusbar_visible contains keys (technical names), not labels
                this.state.SelectedOptions = visibleStr
                    .split(',')
                    .map(v => v.trim())
                    .filter(Boolean);
                this.StatusBarValues.statusbarVisible = visibleStr;
            } else {
                // If no statusbar_visible is set, show all values
                this.state.SelectedOptions = this.state.values.map(v => v[0]);
            }
        } catch (error) {
            console.error('Error loading statusbar values:', error);
        }
    }

    // Add method to get compatible fields for dynamic placeholder
    getDynamicPlaceholderOptions() {
        const currentFieldType = this.state.selectedFieldType || this.props.fieldType;

        // Don't show dynamic placeholder for relational fields
        if (['many2one', 'one2many', 'many2many', 'binary', 'html'].includes(currentFieldType)) {
            return [{ value: '', label: '(None)' }];
        }

        const compatibleFields = [];

        // Add "None" option
        compatibleFields.push({ value: '', label: '(None)' });

        // Filter fields by compatible types
        Object.entries(this.props.allFields || {}).forEach(([fieldName, fieldInfo]) => {
            // Map field types to compatible types
            const typeMapping = {
                'char': ['char'],
                'text': ['text'],
                'integer': ['integer'],
                'float': ['float'],
                'date': ['date'],
                'datetime': ['datetime'],
                'boolean': ['boolean'],
                'selection': ['selection'],
            };

            const compatibleTypes = typeMapping[currentFieldType] || [currentFieldType];

            if (compatibleTypes.includes(fieldInfo.type)) {
                compatibleFields.push({
                    value: fieldName,
                    label: `${fieldInfo.string || fieldName} (${fieldInfo.type})`,
                    fieldType: fieldInfo.type
                });
            }
        });

        return compatibleFields;
    }

    handleDynamicPlaceholderChange(value) {
        this.state.edited = true;
        this.state.dynamic_placeholder = value;

        if (value) {
            const fieldInfo = this.props.allFields[value];

            // Get the actual value from recordData
            let fieldValue = this.state.recordData?.[value];
            if (fieldValue && typeof fieldValue === 'object' && 'display_name' in fieldValue) {
                fieldValue = fieldValue.display_name;
            }

            this.state.dynamic_placeholder_field = {
                name: value,
                string: fieldInfo?.string || value,
                type: fieldInfo?.type,
                value: fieldValue // Store the value as well
            };
            this.state.placeholder = `${fieldValue}`;
            //            this.state.placeholder = `{{${value}}}`;
        } else {
            this.state.dynamic_placeholder_field = "";
            this.state.dynamic_placeholder = '';
            if (this.state.placeholder && this.state.placeholder.startsWith('{{') && this.state.placeholder.endsWith('}}')) {
                this.state.placeholder = "";
            }
        }
        this.autoSave();
    }
    getPlaceholderDisplay() {
        const val = this.state.placeholder || '';
        if (this.state.isPlaceholderFocused) {
            return val;
        }
        if (val.includes('{{')) {
            return val.replace(/{{(.*?)}}/g, (match, fieldName) => {
                const field = fieldName.trim();
                const value = this.state.recordData?.[field];
                //                this.state.placeholder = value
                if (value === undefined || value === null) {
                    return match;
                }
                return (value && typeof value === 'object' && 'display_name' in value)
                    ? value.display_name
                    : value;
            });
        }
        return val;
    }

    handlePlaceholderInput(ev) {
        this.state.placeholder = ev.target.value;
        this.state.edited = true;
        const match = ev.target.value.match(/^{{(.*?)}}$/);
        this.state.dynamic_placeholder = match ? match[1].trim() : '';
    }


    generateRandomFieldName() {
        const timestamp = Date.now();
        const randomNum = Math.floor(Math.random() * 1000);
        return `x_studio_${timestamp}_${randomNum}`;
    }

    onCellKeydown(value) {
        this.state.edited = true
        const labelValue = this.ref.el.querySelector("#label").value.trim();
        this.state.name = 'x_studio_' + labelValue.toLowerCase().split(' ').join('_');
    }
    get fieldType() {
        const result = this.state.fieldType.map((item) => ({
            value: item,
            label: item
        }));
        return result;
    }
    RelatedModel(array) {
        const result = array.map((item) => ({
            value: item.model,
            label: item.name,
        }));
        return result;
    }
    async handleFieldTypeChange(value) {
        this.state.edited = true
        this.selectedWidget = ''
        const container = document.getElementById('dynamic-container');
        while (container && container.firstChild) {
            container.removeChild(container.firstChild);
        }
        this.state.selectedFieldType = value.toLowerCase()
        this.state.widget_types = getWidgetTypes(this.state.selectedFieldType)
        if (['many2one', 'many2many'].includes(this.state.selectedFieldType)) {
            this.state.models = await this.rpc('/cyllo_studio/get_non_abstract_non_transient_models');
        } else if (this.state.selectedFieldType === 'one2many') {
            const relatedFields = await this.orm.searchRead('ir.model.fields', [
                ['ttype', '=', 'many2one'],
                ['relation', '=', this.action.currentController.action.res_model]
            ], ['name', 'field_description', 'model_id'])
            this.state.related_model_field = relatedFields;
        } else {
            this.state.related_model_field = [];
        }
    }
    getRelatedModelFromField() {
        if (this.props.name && this.props.allFields) {
            const fieldInfo = this.props.allFields[this.props.name];
            if (fieldInfo?.relation) {
                return fieldInfo.relation;
            }
        }
        return '';
    }

    fieldsDomain() {
        const ModelName = this.state.related_model || this.props.model || this.props.related_model
        this.dialogService.add(DomainSelectorDialog, {
            resModel: ModelName,
            domain: this.state.domain,
            onConfirm: (domain) => this.domainConfirm(domain),
            title: ("Domain"),
        });
    }
    domainConfirm(domain) {
        this.state.domain = domain
        this.autoSave();
    }
    cancelField() {
        if (this.props.create) {
            this.action.doAction('studio_reload')
            this.env.bus.trigger('CLEAR-MENU');
        }
    }

    async deleteField(el) {
        const view_id = this.props.viewId
        const view_type = this.props.viewType
        // Resolve the field's xpath. props.path can be empty when the arch node's
        // cy-xpath attribute wasn't captured at selection time; fall back to the
        // live DOM element, which reliably carries cy-xpath. Without a path the
        // backend builds `<xpath expr="/">` and the view validation fails.
        let path = this.props.path;
        if (!path && this.props.name) {
            const el = document.querySelector(`[name="${this.props.name}"][cy-xpath]`);
            path = el?.getAttribute("cy-xpath") || "";
        }
        if (!path) {
            this.notification.add({
                title: _t("Cannot Remove Field"),
                message: "Could not locate this field in the view. Re-select the field and try again.",
                type: "notification_panel",
                notificationType: "warning",
            });
            return;
        }
        try {
            const response = await this.rpc("cyllo_studio/delete/existing_fields", {
                method: 'delete_existing_fields',
                model: this.props.model,
                view_id: this.props.viewId,
                view_type: this.props.viewType,
                args: [{
                    fieldName: this.props.string,
                    model: this.props.model,
                    path: path,
                    label_path: this.props.label_path
                }],
                kwargs: {
                    view_id: view_id ? view_id : null,
                    view_type: view_type,
                }
            });
            if (response) {
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr);
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            }
            await this.action.doAction('studio_reload');
        } catch (error) {
            // Extract a readable message from the server error.
            // Odoo ValidationError surfaces via error.data.message or error.message.
            const raw = error?.data?.message || error?.message || "";
            // Pull out the first human-readable sentence (before any XML dump).
            const firstLine = raw.split('\n').find(l => l.trim() && !l.trim().startsWith('<')) || raw;
            // Highlight which field is causing the dependency conflict.
            const fieldMatch = raw.match(/Field '([^']+)'/);
            const fieldHint = fieldMatch
                ? `Field "${fieldMatch[1]}" is referenced in a visibility condition of another column.`
                : firstLine.slice(0, 200) || "This field is referenced by another element in this view.";

            this.notification.add({
                title: _t("Cannot Remove Field"),
                message: _t("Remove the dependency first before deleting this field."),
                description: fieldHint,
                type: "notification_panel",
                notificationType: "warning",
            });
        }
    }
    /**
     * Auto-apply a property change for an EXISTING field (edit mode).
     * Each change persists immediately — no manual Save.
     * New fields (create mode) keep the explicit Save button; they need a
     * name + type before anything can be written.
     * Saves are serialized so rapid toggles don't fire overlapping RPCs;
     * the last change made while a save is in flight runs once it finishes.
     */
    async autoSave() {
        if (!this.props.edit) {
            return;
        }
        if (this._autoSaving) {
            this._autoSavePending = true;
            return;
        }
        this._autoSaving = true;
        try {
            await this.createField();
        } finally {
            this._autoSaving = false;
            if (this._autoSavePending) {
                this._autoSavePending = false;
                this.autoSave();
            }
            this.actionService.doAction("studio_reload");
            if (this.props.path) {
                sessionStorage.setItem('RestoreFieldPath', this.props.path);
            }
        }
    }
    async createField() {
        // Validate field name
        if (!this.state.name) {
            this.notification.add({
                title: _t("Validation Error"),
                message: "Unable to save the field.",
                description: "Please provide a field name to save",
                type: "notification_panel",
                notificationType: "warning",
            });
            return;
        }
        if (this.state.relatedField && this.state.relatedField.trim()) {
            const parts = this.state.relatedField.split(".");
            if (parts.length < 2) {
                this.notification.add({
                    title: _t("Related Field Error"),
                    message: "Invalid related field path.",
                    description: "Please select a valid relational field path.",
                    type: "notification_panel",
                    notificationType: "warning",
                });
                return;
            }
        }

        if (this.state.is_computed) {
            const deps = (this.state.compute_dependencies || "").trim();
            const code = (this.state.compute_code || "").trim();
            if (!deps || !code) {
                this.notification.add({
                    title: _t("Compute Field Incomplete"),
                    message: "Please configure the compute field properly.",
                    description: "Click the 'Based on' button next to Compute and add both Dependencies and Compute Code.",
                    type: "notification_panel",
                    notificationType: "warning",
                })
                return;
            }
        }
        if (this.state.default_value && !this.validateDefaultValueForType()) {
            return;
        }
        if (this.props.edit && !this.state.constraintEnabled) {
            try {
                // Remove Python constraint if it exists
                if (this.state.pythonConstraint) {
                    await this.rpc("/cyllo_studio/get_python_constraint", {
                        model: this.props.model,
                        field_name: this.props.name,
                    });
                    // Mark for removal by setting to null
                    this.state.pythonConstraint = null;
                }
            } catch (error) {
                console.error('Error preparing constraint removal:', error);
            }
        }
        if (this.props.edit) {
            const defaultResult = await this.rpc("/cyllo_studio/set_default", {
                model: this.props.model,
                field_name: this.props.name,
                value: this.state.default_value || "",
            });
        }
        let optionalFields = {};

        // Collect widget options from DOM
        const container = document.getElementById('dynamic-container');
        if (container) {
            container.querySelectorAll('input, select').forEach(field => {
                const fieldName = field.id;
                let fieldValue = field.type === "checkbox" ? field.checked : field.value;

                if (field.name === "fold_field") {
                    // fold_field must be a string field name, not a boolean.
                    // The checkbox UI means "use the 'fold' field" — store the name.
                    if (field.checked) {
                        fieldValue = "fold";
                        this.orm.searchRead("ir.model.fields", [
                            ['model', '=', this.state.relatedModel]
                        ])
                            .then((fields) => {
                                const foldFieldExists = fields.some(f => f.name === 'fold');
                                if (!foldFieldExists) {
                                    this.action.doAction({
                                        type: 'ir.actions.client',
                                        tag: 'display_notification',
                                        params: {
                                            message: 'Related model must contain fold field',
                                            type: 'danger',
                                            sticky: false,
                                        },
                                    });
                                }
                            });
                    } else {
                        fieldValue = "";
                    }
                }

                if (fieldValue !== undefined && fieldValue !== null && fieldValue !== "") {
                    optionalFields[fieldName] = fieldValue;
                }

                if (typeof fieldValue === 'string' && fieldValue.startsWith('[') && fieldValue.endsWith(']')) {
                    try {
                        fieldValue = fieldValue.replace(/'/g, '"');
                        fieldValue = JSON.parse(fieldValue);
                        optionalFields[fieldName] = fieldValue;
                    } catch (e) {
                        console.error('Error parsing field value:', e);
                    }
                }
            });
        }
        // CylloStudioDropdown-based widget options (e.g. monetary currency_field)
        // are OWL components, not native <input>/<select>, so the DOM scan above
        // misses them. Their selected values live in previewImage — merge them in
        // so the option is actually written to the field's `options` attribute.
        if (this.state.previewImage) {
            for (const [key, val] of Object.entries(this.state.previewImage)) {
                if (val !== undefined && val !== null && val !== "" && val !== false) {
                    optionalFields[key] = val;
                }
            }
        }
        // Build the arguments object
        const attrs = {
            widget: this.state.widget || '',
            help: this.state.help || '',
            placeholder: this.state.placeholder || '',
            dynamic_placeholder: this.state.dynamic_placeholder || '', // Add this
            invisible: this.state.invisible || '',
            readonly: this.state.readonly || '',
            required: this.state.required || '',
            domain: this.state.domain || '',
            context: this.state.context || '',
            default_value: this.state.default_value || '',
            is_computed: this.state.is_computed || false,
            depends: this.state.compute_dependencies || "",
            compute: this.state.compute_code || "",
        };

        if (this.state.relatedField) {
            attrs.related = this.state.relatedField;
            attrs.store = true;
        }
        let args = {};

        if (this.props.edit) {
            // EDIT MODE: Send changed values with field_info containing selection
            const changedValues = this.getCurrentChanges(this.prevState, this.state);
            changedValues.default_value = this.state.default_value;

            //                changedValues.dynamic_placeholder = this.state.dynamic_placeholder;

            // Ensure field_info is included for selection fields
            if (this.state.selectedFieldType === 'selection') {
                changedValues.field_info = {
                    selection: this.state.SelectedOptions
                        .filter(val => val && val.trim() !== '')
                        .map(val => [val.toLowerCase().replace(/\s+/g, '_'), val])
                };
            }

            if (this.state.widget === 'statusbar' && this.state.SelectedOptions.length > 0) {
                optionalFields['statusbar_visible'] = this.state.SelectedOptions.join(', ');
            }
            changedValues.dynamic_placeholder = this.state.dynamic_placeholder || '';
            changedValues.is_computed = this.state.is_computed;
            if (this.state.is_computed) {
                changedValues.compute = this.state.compute_code || "";
                changedValues.depends = this.state.compute_dependencies || "";
            } else {
                changedValues.compute = "";
                changedValues.depends = "";
            }

            if (this.state.constraintEnabled) {

                // Add SQL constraints if any exist
                if (this.sqlConstraints && this.sqlConstraints.length > 0) {
                    changedValues.sql_constraints = this.sqlConstraints.map(c => [
                        c.key,
                        c.definition,
                        c.message
                    ]);
                } else {
                    changedValues.sql_constraints = [];
                }

                // Add Python constraint if it exists
                if (this.state.pythonConstraint) {
                    changedValues.python_constraint = this.state.pythonConstraint;
                } else {
                    changedValues.python_constraint = null;
                }
            } else {
                changedValues.sql_constraints = [];
                changedValues.python_constraint = null;
            }

            args = {
                edit: true,
                value: changedValues,
                optional_fields: optionalFields || {},
                field_path: this.props.field_path || this.props.path,
                label_path: this.props.label_path || '',
                field_name: this.props.name || '',
                active_fields: this.props.activeFields,
                model: this.state.related_model || this.props.model,
            };
        } else {
            var related_model_field = null;
            if (this.state.selectedFieldType === 'one2many') {
                const related_field_id = this.state.relatedModelField ? this.state.relatedModelField : '';
                if (related_field_id) {
                    related_model_field = this.state.related_model_field.find(field => field.id == related_field_id);
                }
            }

            // For statusbar widget in new field mode
            if (this.state.widget === 'statusbar' && this.state.selectionValues.length > 0) {
                optionalFields['statusbar_visible'] = this.state.selectionValues.join(', ');
            }
            args = {
                edit: false,
                field_type: this.state.selectedFieldType || 'char',
                optional_fields: optionalFields || {},
                technical_name: this.state.name,
                label: this.state.string || '',
                position: this.props.position || 'inside',
                cy_path: this.props.path || '',
                sibling: this.state.sibling || false,
                item_type: this.props.item_type || "",
                field_info: this.props.field_info || {},
                field_path: this.props.path,
                label_path: this.props.label_path,
                elementType: "",
                related_model: this.state.related_model,
                attrs,
                model: this.props.model,
                view_id: this.props.viewId,
                view_type: this.props.viewType,
                selectionValues: this.state.selectionValues,
                related_model_field: related_model_field,
                active_fields: this.props.activeFields,
            };
        }
        this.env.services.ui.block();
        let hasError = false;
        try {
            const modelName = sessionStorage.getItem("RelationalModel")
                ? (Flatted.parse(sessionStorage.getItem("RelationalModel"))?.[0]?.relation || this.props.model)
                : this.props.model;
            if (!this.props.edit &&
                ((this.state.selectedFieldType == 'one2many' && !this.state.relatedModelField) ||
                    (['many2one', 'many2many'].includes(this.state.selectedFieldType) && !this.props.related_model))) {
                this.notification.add({
                    title: _t("Validation Error"),
                    message: "Unable to save the field.",
                    description: this.state.selectedFieldType == 'one2many'
                        ? "A One2many field requires a valid Many2one inverse field on the related model."
                        : "Please select a related model field for Many2one or Many2many.",
                    type: "notification_panel",
                    notificationType: "warning",
                });
                hasError = true;
                return;
            }
            const response = await this.rpc("/cyllo_studio/create/new_fields", {
                method: 'create_new_fields',
                model: modelName || this.props.model,
                view_id: this.props.viewId,
                view_type: this.props.viewType,
                args: [args],
            });

            if (this.state.default_value && this.state.default_value.trim()) {
                const defaultResult = await this.rpc("/cyllo_studio/set_default", {
                    model: this.props.model,
                    field_name: this.props.edit ? this.props.name : this.state.name,
                    value: this.state.default_value,
                });
            }
            if (response) {
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr);
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            }
        } catch (error) {
            hasError = true;
            console.error('Error creating field:', error);
            const errName = error?.data?.name || error?.exceptionName;
            if (errName === 'odoo.exceptions.AccessError') {
                throw error;
            }
            this.notification.add({
                title: _t("Error"),
                message: "Failed to save the field",
                description: error.message || "An unexpected error occurred",
                type: "notification_panel",
                notificationType: "danger",
            });
        } finally {
            this.env.services.ui.unblock();
            if (!hasError) {
                await this.action.doAction("studio_reload");
            }
        }
    }

    openCalendarPopover() {
        const fieldType = this.state.selectedFieldType;
        const input = document.getElementById('default_value');
        if (!input) {
            console.error('Input element not found');
            return;
        }
        let currentValue = null;
        if (this.state.default_value) {
            try {
                const { DateTime } = luxon || window.luxon;

                if (fieldType === 'date') {
                    currentValue = DateTime.fromISO(this.state.default_value);
                } else if (fieldType === 'datetime') {
                    const isoValue = this.state.default_value.includes('T')
                        ? this.state.default_value
                        : this.state.default_value.replace(' ', 'T');
                    currentValue = DateTime.fromISO(isoValue);
                }
            } catch (e) {
                console.warn('Could not parse current date:', e);
                currentValue = null;
            }
        }
        const picker = this.env.services.datetime_picker.create({
            pickerProps: {
                type: fieldType,
                value: currentValue,
                onSelect: (value) => {
                    if (value) {
                        this.updateInputFromDate(value, fieldType, input);
                    }
                },
            },
            onApply: (value) => {
                if (value) {
                    this.updateInputFromDate(value, fieldType, input);
                }
            },
            target: input,
        });
        picker.enable();
        picker.computeBasePickerProps();
        picker.open(0);
    }
    updateInputFromDate(dateValue, fieldType, input) {
        if (fieldType === 'date') {
            this.state.default_value = dateValue.toISODate();
        } else if (fieldType === 'datetime') {
            const iso = dateValue.toISO().split('.')[0];
            this.state.default_value = iso.replace('T', ' ');
        }
        if (input) {
            input.value = this.state.default_value;
        }
        this.state.edited = true;
    }

    getCurrentChanges(prev, current) {
        const changed = {};
        const excludedKeys = ['fieldType', 'widget_types'];
        const forceKeys = ["is_computed", "compute_code", "compute_dependencies", "compute", "depends", "default_value", "min_precision",
            "max_precision", "sql_constraints", "python_constraint", "dynamic_placeholder"];

        for (const key in current) {
            if (forceKeys.includes(key)) {
                changed[key] = current[key];
                continue;
            }
            if (
                prev[key] !== undefined &&
                !excludedKeys.includes(key) &&
                prev[key] !== current[key]
            ) {
                changed[key] = current[key];
            }
        }
        return changed;
    }


    handleColumnInvisibleChange(event) {
        this.state.edited = true
        this.state.column_invisible = ["false", "undefined"].includes(this.state.column_invisible) ? "true" : "false";
        this.autoSave();
    }
    handleInvisibleChange(event) {
        this.state.edited = true
        this.state.invisible = ["false", "undefined"].includes(this.state.invisible) ? "true" : "false";
        this.autoSave();
    }
    handleReadonlyChange(event) {
        this.state.edited = true
        this.state.readonly = ["false", "undefined"].includes(this.state.readonly) ? "true" : "false";
        this.autoSave();
    }
    handleRequiredChange(event) {
        this.state.required = ["false", "undefined"].includes(this.state.required) ? "true" : "false";
        this.autoSave();
    }
    handleRelatedModelChange(value) {
        this.state.edited = true
        this.props.related_model = value;
        this.state.related_model = value;
    }
    handleDefaultValueChange(value) {
        this.state.edited = true;
        this.state.default_value = value;
        this.autoSave();
    }

    openComputeDialog() {
        this.dialogService.add(ComputeDialog, {
            title: "Computed Field Configuration",
            resModel: this.props.model,
            dependencies: this.state.compute_dependencies || "",
            code: this.state.compute_code || "",
            onConfirm: ({ deps, code, disableCompute }) => {

                if (disableCompute) {
                    this.state.is_computed = false;
                    this.state.compute_dependencies = "";
                    this.state.compute_code = "";
                    this.state.edited = true;
                    this.autoSave();
                    return;
                }
                this.state.is_computed = true;
                this.state.compute_dependencies = deps;
                this.state.compute_code = code;
                this.state.edited = true;
                this.autoSave();
            },
        });
    }

    toggleIsComputed(ev) {
        this.state.is_computed = ev.target.checked;
        if (!ev.target.checked) {
            this.state.compute_code = "";
            this.state.compute_dependencies = "";
            this.state.edited = true;
            // Only auto-apply when disabling — enabling waits for the compute
            // dialog (openComputeDialog) so we don't persist an empty compute.
            this.autoSave();
        }
    }
    validateDefaultValueForType() {
        const ttype = (this.state.selectedFieldType || "").toLowerCase();
        let raw = this.state.default_value;
        let val = (raw === null || raw === undefined) ? "" : String(raw).trim();
        const errors = [];
        if (ttype === "selection") {
            const values = this.state.field === 'existing'
                ? (this.state.values || [])
                : (this.state.selectionValues || []);

            let options = [];

            if (values.length && Array.isArray(values[0])) {
                options = values.map(v => String(v[0]));
            } else {
                options = values.map(v => String(v).toLowerCase().replace(/\s+/g, '_'));
            }

            if (val !== "" && !options.includes(val)) {
                errors.push(`Selection default must be one of: ${options.join(", ")}`);
            }
        }
        if (ttype === "boolean") {
            const allowed = ["true", "false", "1", "0"];
            if (val !== "" && !allowed.includes(val.toLowerCase())) {
                errors.push("Boolean default accepts only: true, false, 1, 0");
            }
        }
        if (ttype === "integer") {
            if (val !== "" && !/^-?\d+$/.test(val)) {
                errors.push("Integer default accepts only whole numbers (e.g., 10, -3).");
            }
        }
        if (ttype === "float") {
            if (val !== "" && !/^-?\d+(\.\d+)?$/.test(val)) {
                errors.push("Float default accepts only numeric values (e.g., 10, 10.25).");
            }
        }
        if (ttype === "date") {
            // Odoo format: YYYY-MM-DD
            const dateRegex = /^\d{4}-\d{2}-\d{2}$/;

            if (val !== "" && !dateRegex.test(val)) {
                errors.push("Date default must follow format: YYYY-MM-DD (e.g., 2025-11-19)");
            }
        }
        if (ttype === "datetime") {
            const datetimeRegex = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;

            if (val !== "" && !datetimeRegex.test(val)) {
                errors.push("Datetime default must follow format: YYYY-MM-DD HH:MM:SS (e.g., 2025-11-19 14:30:00)");
            }
        }
        if (errors.length) {
            this.notification.add({
                title: _t("Default Value Error"),
                message: errors.join(" — "),
                type: "notification_panel",
                notificationType: "warning",
            });
            return false;
        }
        return true;
    }
    RelatedModelField(array) {
        if (!array || array.length === 0) {
            return [{ value: false, label: 'No compatible fields available' }];
        }
        const result = array.map(item => ({
            value: item.id,
            label: item.field_description + '(' + item.model_id[1] + ')'
        }));
        return result;
    }

    async handleRelatedModelFieldChange(value) {
        this.state.relatedModelField = value;
        if (!value) {
            this.state.relatedModel = "";
            return;
        }
        const One2ManyRelated = this.state.related_model_field.find(field => field.id == this.state.relatedModelField)
        if (One2ManyRelated) {
            const One2ManyRelatedModel = await this.orm.read("ir.model", [One2ManyRelated.model_id[0]], [])
            this.state.relatedModel = One2ManyRelatedModel[0].model
        }
    }

    get defaultRelatedModelField() {
        return this.state.relatedModelField
    }

    async attrDomain(ev) {
        this.state.edited = true
        const parent = event.target.closest('.cy-basedOn')
        var attribute = parent.getAttribute('data-attribute')
        var domain = '';
        if (attribute === 'readonly' && this.props.readonly) {
            domain = this.state.readonly ? this.state.readonly : this.props.readonly
        } else if (attribute === 'invisible' && this.props.invisible) {
            domain = this.state.invisible ? this.state.invisible : this.props.invisible
        } else if (attribute === 'required' && this.props.required) {
            domain = this.state.required ? this.state.required : this.props.required
        } else {
            domain = false
        }
        var resModel = this.action.currentController.props.resModel
        var fields_detail = await this.orm.call(resModel, 'fields_get', [], {
            attributes: ['string', 'help', 'type', 'relation', 'selection', 'domain']
        });
        var resModel = this.action.currentController.props.resModel
        domain = domain ? domain : "False";

        // Use the fields that are already available from props
        const fields_info = this.props.allFields || {};
        this.addDialog(ExpressionEditorDialog, {
            resModel,
            fields: fields_info,
            expression: domain,
            onConfirm: (expression) => this.modifier(expression, attribute),
        });
    }
    modifier(expression, attribute) {
        this.attribute = attribute
        if (attribute == 'invisible') {
            this.state.invisible = expression
        }
        if (attribute == 'readonly') {
            this.state.readonly = expression
        }
        if (attribute == 'required') {
            this.state.required = expression
        }
        this.autoSave();
    }
    get newFieldWidgets() {
        return this.state.widget_types.length ? [{
            value: false,
            label: '(None)'
        }, ...this.state.widget_types] : this.state.widget_types
    }

    FieldTypeChange(value) {
        if (value === 'button') {
            this.createButton();
        } else if (value === 'new') {
            this.createNewField();
        } else if (value === 'existing') {
            this.env.bus.trigger("LIST_EXISTING_FIELDS", {
                name: "ExistingName",
                type: "ExistingProperties",
            });
            this.env.bus.trigger('CLEAR-MENU');
        }
    }

    openFieldSelector(ev) {
        const targetEl = ev.currentTarget;
        const resModel = this.props.model;

        this.popover.open(targetEl, {
            resModel,
            path: this.state.finalRelated || "",
            showSearchInput: true,
            followRelations: true,
            isDebugMode: !!(this.env.debug || odoo.debug),
            filter: (fieldDef, path) => {
                const isRootLevel = !path || path.trim() === "";
                if (isRootLevel) {
                    return fieldDef.type === "many2one";
                } else {
                    return true;
                }
            },
            update: async (path) => {
                this.state.finalRelated = path;
                this.state.relatedModelField = path;
                this.state.relatedField = path;
                const fieldInfo = await this.loadFieldInfo(resModel, path);
                this.state.relatedFieldType = fieldInfo.fieldDef.type;
                this.state.edited = true;
            }

        });
    }

    async createButton() {
        this.env.bus.trigger("BUTTON_DETAILS", {
            type: "ButtonProperties",
            path: "/tree",
            position: "inside",
        });
    }

    handleFieldWidgetChange(value) {
        this.state.widget = value;
        this.widgetOptionalFields(this.state.widget)
        this.autoSave();
    }

    //    Widget Options Start
    widgetOptionalFields(widget_name, widget_options = null) {
        if (document.getElementById('dynamic-container')) {
            document.getElementById('dynamic-container').innerHTML = '';
        }
        if (widget_name) {

            if (widget_name == "statusbar") {
                this.state.isStatusBar = true
                this.loadStatusbarValues();
            } else {
                this.state.isStatusBar = false
            }
            const supportedOptions = getWidgetSupport(widget_name);
            const widgetOption = getWidgetTypes(widget_name)
            if (supportedOptions) {
                const container = document.getElementById('dynamic-container');
                if (container) {
                    container.innerHTML = '';
                    supportedOptions.forEach(async field => {
                        const fieldName = field.options.name;
                        const widgetOptionsType = widgetOption?.component?.props[fieldName]?.type
                        let widgetOptionsType_value = "";

                        if (widgetOptionsType && widgetOptionsType.name) {
                            widgetOptionsType_value = widgetOptionsType.name.toString();
                        }
                        var fieldValue = this.props.options?.[fieldName] || ''
                        // The monetary currency is intrinsic to the field — when no
                        // explicit currency_field option is set in the arch, resolve it
                        // from the field's metadata (falling back to currency_id) so the
                        // read-only dropdown shows the real value instead of being blank.
                        if (fieldName === 'currency_field' && !fieldValue) {
                            fieldValue = this.props.allFields?.[this.props.name]?.currency_field || 'currency_id';
                        }
                        if (field.options.availableTypes && field.options.availableTypes.length > 0) {
                            const optionFields = this.state.field_type === 'many2many' ? this.state.related_model : this.existedField
                            if (optionFields) {
                                this.state.charFields = Object.keys(optionFields)
                                    .filter(key => optionFields[key].type === field.options.availableTypes[0])
                                    .reduce((obj, key) => {
                                        obj[key] = optionFields[key];
                                        return obj;
                                    }, {});
                            }
                            if (widget_name === 'monetary' && this.state.charFields) {
                                const options = Object.keys(this.state.charFields)
                                    .filter(item => this.state.charFields[item].relation === 'res.currency')
                                    .reduce((acc, key) => {
                                        acc[key] = this.state.charFields[key];
                                        return acc;
                                    }, {});

                                // Update charFields with the filtered options (for 'monetary' widget)
                                this.state.charFields = options;
                                // The effective currency field may not be among the view's
                                // own fields — add it so the read-only dropdown can display
                                // it (e.g. currency_id even when it's not a visible column).
                                if (fieldName === 'currency_field' && fieldValue &&
                                    !Object.values(this.state.charFields).some(f => f.name === fieldValue)) {
                                    this.state.charFields = {
                                        ...this.state.charFields,
                                        [fieldValue]: {
                                            name: fieldValue,
                                            string: this.props.allFields?.[fieldValue]?.string || 'Currency',
                                        },
                                    };
                                }
                            }
                        }
                        var obj = field.options.label
                        let string = "";
                        for (const key in obj) {
                            if (obj.hasOwnProperty(key)) {
                                string += obj[key];
                            }
                        }
                        if (field.options.type === 'field') {
                            if (fieldName === "fold_field") {
                                const div = document.createElement('div');
                                div.id = fieldName + '_div';
                                div.innerHTML = `
                                    <div class="cy-toggle-row">
                                        <span class="cy-toggle-label">${obj}</span>
                                        <label class="cy-switch">
                                            <input type="checkbox" id="${fieldName}" name="${fieldName}" ${fieldValue ? 'checked' : ''}>
                                            <span class="cy-slider"></span>
                                        </label>
                                    </div>`;
                                container.appendChild(div);
                            } else {
                                const div = document.createElement('div');
                                div.id = fieldName + '_div'; // Use field name as ID
                                div.innerHTML = `
                                        <label class="cy-navbar_label" for="${fieldName}">${obj}</label>`;
                                container.appendChild(div);
                                const div2 = document.createElement('div');
                                div2.setAttribute('id', fieldName);
                                div2.classList.add('cy-studio-custom-dropdown-image-widget', 'cy-studio-custom-dropdown');
                                container.appendChild(div2);;
                                // Seed previewImage with the EXPLICIT option value (from the
                                // arch) so an unchanged dropdown is written back on save, not
                                // dropped. Use the explicit value — not the resolved display
                                // value — so a merely-intrinsic currency_field isn't persisted
                                // as a redundant option (matches Odoo, which never writes it).
                                const explicitValue = this.props.options?.[fieldName];
                                if (explicitValue) {
                                    this.state.previewImage = {
                                        ...this.state.previewImage,
                                        [fieldName]: explicitValue,
                                    };
                                }
                                // Like Odoo Studio, the monetary currency field is
                                // intrinsic to the field — show it read-only, not editable.
                                const isReadonlyOption = fieldName === 'currency_field';
                                await owl.mount(CylloStudioDropdown, div2, {
                                    props: {
                                        options: this.ImageWidget,
                                        defaultValue: fieldValue,
                                        disabled: isReadonlyOption,
                                        onChange: (value) => this.AddModelWidget({
                                            [fieldName]: value
                                        })

                                    },
                                })
                            }
                        } else if (field.options.type === 'string') {
                            const div = document.createElement('div');
                            div.id = fieldName + '_div';

                            // Create label element
                            const label = document.createElement('label');
                            label.className = 'cy-navbar_label';
                            label.htmlFor = fieldName; // Links the label to the input by ID
                            label.textContent = `${obj}`;

                            // Create input element
                            const input = document.createElement('input');
                            input.className = 'cy-input';
                            input.type = 'text';
                            input.autocomplete = 'off';
                            input.id = fieldName;
                            input.name = fieldName;
                            input.value = fieldValue;
                            if (widgetOptionsType) {
                                input.placeholder = `Expected Input  As :- ${widgetOptionsType_value}`;
                            }

                            // Bind events
                            input.addEventListener('change', (ev) => this.fieldValidation(ev, widgetOptionsType_value)); // Event for the input
                            // Append elements
                            div.appendChild(label);
                            div.appendChild(input);

                            // Append the div to the container
                            container.appendChild(div);
                        } else if (field.options.type == 'boolean') {
                            const div = document.createElement('div');
                            div.id = fieldName + '_div';
                            div.innerHTML = `
                                <div class="cy-toggle-row">
                                    <span class="cy-toggle-label">${obj}</span>
                                    <label class="cy-switch">
                                        <input type="checkbox" id="${fieldName}" name="${fieldName}" ${fieldValue ? 'checked' : ''}>
                                        <span class="cy-slider"></span>
                                    </label>
                                </div>`;
                            const checkbox = div.querySelector('input[type="checkbox"]');
                            if (checkbox) {
                                checkbox.addEventListener('change', (ev) => {
                                    this.state.edited = true;
                                    this.autoSave();
                                });
                            }
                            container.appendChild(div);
                        } else if (field.options.type === "select") {
                            const div = document.createElement("div");
                            div.id = fieldName + "_div";

                            const label = document.createElement("label");
                            label.className = "cy-navbar_label";
                            label.textContent = field.options.name + ":";
                            div.appendChild(label);

                            const select = document.createElement("select");
                            select.id = fieldName;
                            select.className = "cy-input";

                            field.options.options.forEach(opt => {
                                const option = document.createElement("option");
                                option.value = opt;
                                option.textContent = opt;
                                if (opt === fieldValue) option.selected = true;
                                select.appendChild(option);
                            });

                            select.addEventListener("change", (ev) => {
                                if (fieldName === "minimalPrecision") {
                                    this.handleMinPrecisionChange(ev.target.value);
                                } else if (fieldName === "maximalPrecision") {
                                    this.handleMaxPrecisionChange(ev.target.value);
                                }
                                this.state.edited = true;
                            });

                            div.appendChild(select);
                            container.appendChild(div);
                        }
                    })
                }

            }
        } else if (document.getElementById('dynamic-container')) {
            const container = document.getElementById('dynamic-container');
            container.innerHTML = '';
        }
    }

    get ImageWidget() {
        const arr = [{
            value: false,
            label: '(None)'
        }]
        for (let value in this.state.charFields) {
            const field = this.state.charFields[value];
            const label = field.string || field.display_name || field.name;
            const obj = {
                value: field.name,
                // Append the technical name so the entry reads as a field,
                // not an empty placeholder (e.g. "Currency (currency_id)").
                label: field.name && label !== field.name ? `${label} (${field.name})` : label
            }
            arr.push(obj)
        }
        return arr
    }
    AddModelWidget(value) {
        this.state.previewImage = { ...this.state.previewImage, ...value }
    }

    get multiSelectDropDown() {
        const values = this.state.field === 'existing' ? (this.state.values || []) : (this.state.selectionValues || []);

        let allValues = {};
        const isExistingFormat = values.length && Array.isArray(values[0]);

        if (isExistingFormat) {
            // values are in form [[key, label], ...]
            values.forEach(item => {
                if (Array.isArray(item) && item.length >= 2) {
                    const key = String(item[0]);
                    const label = String(item[1]);
                    allValues[key] = label;
                }
            });
        } else {
            // new-field mode: values are simple strings; we expose them as key->label (use normalized key)
            values.forEach(item => {
                if (item) {
                    const label = String(item);
                    const key = String(label).toLowerCase().replace(/\s+/g, '_');
                    allValues[key] = label;
                }
            });
        }

        return {
            selectedValues: [...new Set(this.state.SelectedOptions || [])],
            allValues,
            onUpdate: (value) => {
                this.state.SelectedOptions = value;
                this.StatusBarValues.statusbarVisible = value.join(',');
                this.state.edited = true;
                this.autoSave();
            },
        };
    }

    get defaultValueSelectionOptions() {
        const values = this.state.field === 'existing' ? (this.state.values || []) : (this.state.selectionValues || []);
        const arr = [{ value: "", label: "(None)" }];
        const isExistingFormat = values.length && Array.isArray(values[0]);

        if (isExistingFormat) {
            values.forEach(item => {
                if (Array.isArray(item) && item.length >= 2) {
                    arr.push({ value: String(item[0]), label: String(item[1]) });
                }
            });
        } else {
            values.forEach(item => {
                if (item) {
                    const label = String(item);
                    const key = String(label).toLowerCase().replace(/\s+/g, '_');
                    arr.push({ value: key, label: label });
                }
            });
        }
        return arr;
    }

    openConstraintDialog() {
        // Auto-enable the checkbox when opening dialog
        this.state.constraintEnabled = true;
        const fieldName = this.props.edit ? this.props.name : this.state.name;
        const fieldLabel = this.props.edit ? this.props.string : this.state.string;
        if (!fieldName || !fieldName.trim()) {
            this.notification.add({
                title: _t("Field Name Required"),
                message: _t("Please enter a field name before adding constraints."),
                type: "notification_panel",
                notificationType: "warning",
            });
            return;
        }

        this.addDialog(ConstraintDialog, {
            fieldName: fieldName,
            fieldLabel: fieldLabel || fieldName,
            existingConstraints: this.sqlConstraints || [],
            model: this.props.model,
            onConfirm: (constraint) => this.addConstraint(constraint),
            onCancel: () => this.handleConstraintDialogCancel(),
        });
    }

    handleConstraintDialogCancel() {
        // If no constraints exist after cancel, disable the checkbox
        if (!this.sqlConstraints || this.sqlConstraints.length === 0) {
            this.state.constraintEnabled = false;
        }
    }

    handleConstrainsChange(event) {
        const isChecked = event.target.checked;

        if (!isChecked) {
            // If unchecking and constraints exist, warn user
            const hasSqlConstraints = this.sqlConstraints && this.sqlConstraints.length > 0;
            const hasPythonConstraint = !!this.state.pythonConstraint;
            const hasAnyConstraints = hasSqlConstraints || hasPythonConstraint;

            if (hasAnyConstraints) {
                this.clearAllConstraints();
                this.state.edited = true;

                this.notification.add({
                    title: _t("Constraints Cleared"),
                    message: "All constraints have been removed.",
                    type: "notification_panel",
                    notificationType: "success",
                });
            } else {
                this.state.constraintEnabled = false;
            }
            // Auto-apply only when disabling/clearing constraints — enabling
            // waits for the constraint dialog so we don't persist an empty one.
            this.state.edited = true;
            this.autoSave();
            return;
        } else {
            this.state.constraintEnabled = true;
        }

        this.state.edited = true;
    }

    addConstraint(constraint) {

        // Handle both SQL and Python constraints
        const hasSqlConstraint = constraint.sql_constraint;
        const hasPythonConstraint = constraint.python_constraint;

        if (!hasSqlConstraint && !hasPythonConstraint) {
            this.notification.add({
                title: _t("Invalid Constraint"),
                message: "No valid constraint data provided.",
                type: "notification_panel",
                notificationType: "warning",
            });
            this.state.constraintEnabled = false;
            return;
        }
        if (hasSqlConstraint) {
            const sqlConstraint = constraint.sql_constraint;
            if (!sqlConstraint.key || !sqlConstraint.definition || !sqlConstraint.message) {
                this.notification.add({
                    title: _t("Invalid SQL Constraint"),
                    message: "SQL constraint data is incomplete.",
                    type: "notification_panel",
                    notificationType: "warning",
                });
                return;
            }

            if (!this.sqlConstraints) {
                this.sqlConstraints = [];
            }

            const exists = this.sqlConstraints.some(c => c.key === sqlConstraint.key);
            if (exists) {
                this.notification.add({
                    title: _t("Duplicate Constraint"),
                    message: `SQL constraint '${sqlConstraint.key}' already exists`,
                    type: "notification_panel",
                    notificationType: "warning",
                });
                return;
            }

            // Add SQL constraint
            this.sqlConstraints.push(sqlConstraint);
        }

        // Handle Python constraint
        if (hasPythonConstraint) {
            const pythonConstraint = constraint.python_constraint;

            // Validate Python constraint data
            if (!pythonConstraint.deps || !pythonConstraint.code) {
                this.notification.add({
                    title: _t("Invalid Python Constraint"),
                    message: "Python constraint data is incomplete.",
                    type: "notification_panel",
                    notificationType: "warning",
                });
                return;
            }
            this.state.pythonConstraint = pythonConstraint;
        }
        this.state.constraintEnabled = true;
        this.state.edited = true;

        const messages = [];
        if (hasSqlConstraint) messages.push("SQL");
        if (hasPythonConstraint) messages.push("Python");

        this.notification.add({
            title: _t("Success"),
            message: `${messages.join(" and ")} constraint(s) added successfully.`,
            type: "notification_panel",
            notificationType: "success",
        });
        this.autoSave();
    }


    async removeConstraint(index) {
        if (this.sqlConstraints && this.sqlConstraints[index]) {
            const constraintToRemove = this.sqlConstraints[index];

            // Remove from database immediately
            try {
                const result = await this.rpc('/cyllo_studio/remove_single_constraint', {
                    model: this.props.model,
                    field_name: this.props.name,
                    constraint_key: constraintToRemove.key
                });

                if (result.success) {
                    // Remove from frontend array
                    this.sqlConstraints.splice(index, 1);
                    this.state.edited = true;

                    // Check if we still have any constraints
                    const hasSqlConstraints = this.sqlConstraints.length > 0;
                    const hasPythonConstraint = !!this.state.pythonConstraint;

                    // Auto-disable checkbox if no constraints left
                    if (!hasSqlConstraints && !hasPythonConstraint) {
                        this.state.constraintEnabled = false;
                    }

                    this.notification.add({
                        title: _t("Success"),
                        message: "Constraint removed successfully",
                        type: "notification_panel",
                        notificationType: "success",
                    });
                } else {
                    this.notification.add({
                        title: _t("Error"),
                        message: result.error || "Failed to remove constraint",
                        type: "notification_panel",
                        notificationType: "danger",
                    });
                }
            } catch (error) {
                console.error('Error removing constraint:', error);
                this.notification.add({
                    title: _t("Error"),
                    message: "Failed to remove constraint",
                    type: "notification_panel",
                    notificationType: "danger",
                });
            }
        }
    }

    // New method to remove Python constraint
    removePythonConstraint() {
        if (this.state.pythonConstraint) {
            this.state.pythonConstraint = null;
            this.state.edited = true;

            // Check if we still have any SQL constraints
            const hasSqlConstraints = this.sqlConstraints && this.sqlConstraints.length > 0;

            // Auto-disable checkbox if no constraints left
            if (!hasSqlConstraints) {
                this.state.constraintEnabled = false;
            }
        }
    }

    // New method to clear all constraints
    clearAllConstraints() {

        // Clear SQL constraints
        if (this.sqlConstraints) {
            this.sqlConstraints.splice(0, this.sqlConstraints.length);
        }

        // Clear Python constraint
        this.state.pythonConstraint = null;

        // Disable checkbox
        this.state.constraintEnabled = false;
        this.state.edited = true;

    }

    getSQLConstraintsTuples() {
        if (!this.sqlConstraints || this.sqlConstraints.length === 0) {
            return [];
        }
        return this.sqlConstraints.map(c => [c.key, c.definition, c.message]);
    }
    checkSelectionValues() {
        const lowerCaseArray = this.state.selectionValues.map(element => element.toLowerCase());
        let setValues = new Set(lowerCaseArray);
        const isSameElement = setValues.size != lowerCaseArray.length
        const isEmpty = lowerCaseArray.some(str => str === null || str.match(/^ *$/) !== null);
        if (isSameElement || isEmpty) {
            let message = isSameElement ? 'Containing same values!' : 'Containing empty values!'
            this.env.services.action.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'warning',
                    'sticky': false,
                }
            })
            return false
        }
        return true
    }
    addSelectionValue() {
        return this.checkSelectionValues() ? this.state.selectionValues.push('') : false
    }
    changeSelectionValue(index, value) {
        this.state.selectionValues[index] = value
    }
    deleteSelectionValue(index) {
        this.state.selectionValues.splice(index, 1)
    }

    /**
     * Validates and auto-saves a dynamically created widget-option input
     * (type = "string") when the user commits a change.
     *
     * Called from `widgetOptionalFields()` via:
     *   input.addEventListener('change', (ev) => this.fieldValidation(ev, widgetOptionsType_value))
     *
     * @param {Event}  ev                  - The DOM change event from the input.
     * @param {string} widgetOptionsType   - Expected JS type name, e.g. "String", "Number".
     */
    fieldValidation(ev, widgetOptionsType) {
        const input = ev.target;
        const rawValue = input.value.trim();

        // Type-check when an explicit type is declared
        if (widgetOptionsType && rawValue !== '') {
            const expectedType = widgetOptionsType.toLowerCase();

            if (expectedType === 'number') {
                if (isNaN(Number(rawValue))) {
                    this.notification.add({
                        title: _t("Invalid Value"),
                        message: _t(`Expected a numeric value for "${input.name || input.id}".`),
                        type: "notification_panel",
                        notificationType: "warning",
                    });
                    input.value = '';
                    return;
                }
            }
        }

        // Mark as changed and auto-save (persists the option to the view arch)
        this.state.edited = true;
        this.autoSave();
    }

}

FieldProperties.components = {
    CylloStudioDropdown,
    MultiSelectDropDown,
    SelectionFieldValue,
    CodeEditor,
    ComputeDialog,
    //        DatePicker,
    DateTimePicker,
    ConstraintDialog
};