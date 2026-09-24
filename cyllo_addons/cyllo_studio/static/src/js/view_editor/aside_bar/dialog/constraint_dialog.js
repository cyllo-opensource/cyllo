/** @odoo-module **/
import {
    Component,
    useState,
    useRef,
    onMounted,
} from "@odoo/owl";
import {
    useService,
    useOwnedDialogs,
} from "@web/core/utils/hooks";
import {
 CodeEditor
 } from "@web/core/code_editor/code_editor";
import {
    DomainSelectorDialog
} from "@web/core/domain_selector_dialog/domain_selector_dialog";
import {
 _t
 } from "@web/core/l10n/translation";
import {
 Dialog
 } from "@web/core/dialog/dialog";
import {
 usePopover
  } from "@web/core/popover/popover_hook";
  import {
 ModelFieldSelectorPopover
 } from "@web/core/model_field_selector/model_field_selector_popover";
  import { patch } from '@web/core/utils/patch';


export class ConstraintDialog extends Component {
    static template = "cyllo_studio.ConstraintDialog";
    static props = {
        fieldName: String,
        fieldLabel: {
            type: String,
            optional: true,
        },
        existingConstraints: {
            type: Array,
            optional: true,
        },
        model: {
            type: String,
            optional: true,
        },
        onConfirm: Function,
        onCancel: {
            type: Function,
            optional: true,
        },
        close: Function,
    };

    setup() {
        this.notification = useService("effect");
        this.dialogService = useService("dialog");
        this.addDialog = useOwnedDialogs();
        this.rpc = useService("rpc");

        this.state = useState({
            activeTab: 'sql_constraints',
            deps: this.props.dependencies || "",
            code: this.props.code || "",
            fieldName: this.props.fieldName,
            fieldLabel: this.props.fieldLabel || this.props.fieldName,
            constraintType: "",
            condition: "",
            errorMessage: "",
            constraintKey: "",
            // ⭐ NEW: Track NULL/empty data warnings
            nullWarning: {
                show: false,
                nullCount: 0,
                emptyCount: 0,
                totalRecords: 0,
                affectedPercentage: 0,
            },
            isLoadingDataCheck: false,
            isLoadingConstraints: false,
        });
        this.popover = usePopover(ModelFieldSelectorPopover, {
            popoverClass: "o_model_field_selector_popover",
        });
        this.constraintTypes = [
            {value: "",label:""},
            { value: "unique", label: "Unique (No Duplicates)" },
            { value: "not_null", label: "Not Null (Required)" },
            { value: "check", label: "Check (Condition)" },
        ];

        onMounted(() => {
            this.generateConstraintKey();
            this.loadExistingConstraints();

        });
    }

    async loadExistingConstraints() {
    if (!this.props.model || !this.props.fieldName) {
        return;
    }

    this.state.isLoadingConstraints = true;

    try {
        // Load Python constraint
        const pythonConstraintInfo = await this.rpc("/cyllo_studio/get_python_constraint", {
            model: this.props.model,
            field_name: this.props.fieldName,
        });

        if (pythonConstraintInfo && pythonConstraintInfo.deps && pythonConstraintInfo.code) {
            this.state.deps = pythonConstraintInfo.deps;
            this.state.code = pythonConstraintInfo.code;
            this.state.activeTab = 'python_constraints'; // Switch to Python tab if constraint exists
        }

        // Load SQL constraints (if you want to display them too)
        if (this.props.existingConstraints && this.props.existingConstraints.length > 0) {
            const firstConstraint = this.props.existingConstraints[0];
            this.state.constraintType = firstConstraint.type || "unique";
            this.state.errorMessage = firstConstraint.message || "";
            this.state.condition = firstConstraint.definition || "";
            this.state.constraintKey = firstConstraint.key || "";
            this.state.activeTab = 'sql_constraints'; // Switch to SQL tab if constraints exist
        }

    } catch (error) {
        console.error("Error loading constraints:", error);
    } finally {
        this.state.isLoadingConstraints = false;
    }
}

    // ⭐ SIMPLIFIED: Load existing constraints for the field
async loadExistingConstraints() {
    if (!this.props.model || !this.props.fieldName) {
        return;
    }

    this.state.isLoadingConstraints = true;

    try {
        // Load Python constraint from RPC
        const pythonConstraintInfo = await this.rpc("/cyllo_studio/get_python_constraint", {
            model: this.props.model,
            field_name: this.props.fieldName,
        });

        // ⭐ If Python constraint exists, populate the fields
        if (pythonConstraintInfo && pythonConstraintInfo.deps && pythonConstraintInfo.code) {
            this.state.deps = pythonConstraintInfo.deps;
            this.state.code = pythonConstraintInfo.code;
        }

    } catch (error) {
        console.error("Error loading constraints:", error);
    } finally {
        this.state.isLoadingConstraints = false;
    }
}

    generateConstraintKey() {
        const fieldLower = this.state.fieldName.toLowerCase().replace(/\s+/g, '_');
        const typeLower = this.state.constraintType.toLowerCase();
        this.state.constraintKey = `${fieldLower}_${typeLower}`;
    }

    // ⭐ NEW METHOD: Check for NULL/empty values in the field
    async checkFieldData() {
        if (this.state.constraintType !== "not_null") {
            this.state.nullWarning.show = false;
            return;
        }

        if (!this.props.model) {
            console.warn("Model not provided to ConstraintDialog");
            return;
        }

        this.state.isLoadingDataCheck = true;

        try {
            const result = await this.rpc("/cyllo_studio/check_field_data", {
                model: this.props.model,
                field_name: this.props.fieldName,
            });

            const nullCount = result.null_count || 0;
            const emptyCount = result.empty_count || 0;
            const totalRecords = result.total_records || 0;
            const invalidCount = nullCount + emptyCount;

            this.state.nullWarning = {
                show: invalidCount > 0,
                nullCount: nullCount,
                emptyCount: emptyCount,
                totalRecords: totalRecords,
                affectedPercentage: totalRecords > 0 ? Math.round((invalidCount / totalRecords) * 100) : 0,
            };

            if (this.state.nullWarning.show) {
                console.warn(
                    `Field "${this.props.fieldName}" has ${invalidCount} NULL/empty values ` +
                    `out of ${totalRecords} records (${this.state.nullWarning.affectedPercentage}%)`
                );
            }
        } catch (error) {
            console.error("Error checking field data:", error);
            this.state.nullWarning.show = false;
        } finally {
            this.state.isLoadingDataCheck = false;
        }
    }

    async onConstraintTypeChange(value) {
        this.state.constraintType = value;
        this.state.condition = "";
        this.generateConstraintKey();

        // ⭐ Check data when switching to NOT NULL
        if (value === "not_null") {
            await this.checkFieldData();
        } else {
            this.state.nullWarning.show = false;
        }
    }

    openConditionBuilder() {
        if (this.state.constraintType !== "check") {
            this.notification.add({
                title: _t("Info"),
                message: "Condition builder is only for CHECK constraints",
                type: "notification_panel",
                notificationType: "info",
            });
            return;
        }

        const conditionInput = document.getElementById('condition-input');
        if (conditionInput) {
            conditionInput.focus();
        }
    }

    validateConstraint() {
        if (!this.state.errorMessage || !this.state.errorMessage.trim()) {
            this.notification.add({
                title: _t("Validation Error"),
                message: "Error message is required",
                type: "notification_panel",
                notificationType: "warning",
            });
            return false;
        }

        if (this.state.constraintType === "check" && !this.state.condition.trim()) {
            this.notification.add({
                title: _t("Validation Error"),
                message: "Check condition is required for CHECK constraints",
                type: "notification_panel",
                notificationType: "warning",
            });
            return false;
        }

        // ⭐ NEW: Warn about NOT NULL constraint with existing NULL values
        if (this.state.constraintType === "not_null" && this.state.nullWarning.show) {
            const confirmApply = confirm(
                `WARNING: This field has ${this.state.nullWarning.nullCount + this.state.nullWarning.emptyCount} ` +
                `NULL/empty values (${this.state.nullWarning.affectedPercentage}% of records).\n\n` +
                `When you save this constraint, these values will be automatically converted to empty strings.\n\n` +
                `Do you want to continue?`
            );

            if (!confirmApply) {
                return false;
            }
        }

        return true;
    }

    buildSQLConstraint() {
        const fieldName = this.state.fieldName;
        let definition = "";

        switch (this.state.constraintType) {
            case "unique":
                definition = `UNIQUE(${fieldName})`;
                break;
            case "not_null":
                definition = `CHECK(${fieldName} IS NOT NULL)`;
                break;
            case "check":
                definition = `CHECK(${this.state.condition})`;
                break;
            case "foreign_key":
                definition = this.state.condition;
                break;
            default:
                definition = "";
        }

        return {
            key: this.state.constraintKey,
            definition: definition,
            message: this.state.errorMessage,
        };
    }

//    confirm() {
//        if (!this.validateConstraint()) {
//            return;
//        }
//        const constraint = this.buildSQLConstraint();
//        this.props.onConfirm(constraint);
//          const deps = (this.state.deps || "").trim();
//        const code = (this.state.code || "").trim();
//        if (!deps && !code) {
//            this.props.onConfirm({
//                deps: "",
//                code: "",
//            });
//            this.props.close();
//            return;
//        }
//        if ((deps && !code) || (!deps && code)) {
//            this.notification.add({
//                title: _t("Validation Error"),
//                message: "Both fields required",
//                description: "Please provide both Dependencies and Constraint Code.",
//                type: "notification_panel",
//                notificationType: "warning",
//            });
//            return;
//        }
//        this.props.onConfirm({
//            deps,
//            code,
//        });
//        this.props.close();        // Case 4: Both empty → No SQL constraint (OK, continue)
        // else: sqlConstraint remains null
//    }

    confirm() {
    const isSqlTab = this.state.activeTab === 'sql_constraints';
    const isPythonTab = this.state.activeTab === 'python_constraints';

    const deps = (this.state.deps || "").trim();
    const code = (this.state.code || "").trim();
    const constraintType = (this.state.constraintType || "").trim();
    const errorMessage = (this.state.errorMessage || "").trim();


    let sqlConstraint = null;
    let pythonConstraint = null;

    if (isSqlTab) {
        const hasSqlType = !!constraintType;
        const hasSqlMessage = !!errorMessage;

        // Case 1: Both provided → Valid SQL constraint
        if (hasSqlType && hasSqlMessage) {
            if (!this.validateConstraint()) {
                return; // validateConstraint() already shows notifications
            }
            sqlConstraint = this.buildSQLConstraint();
        }
        // Case 2: Only Type provided (no message)
        else if (hasSqlType && !hasSqlMessage) {
            this.notification.add({
                title: _t("Validation Error"),
                message: "Missing Error Message",
                description: "Please provide an Error Message for the SQL constraint.",
                type: "notification_panel",
                notificationType: "warning",
            });
            return;
        }
        // Case 3: Only Message provided (no type)
        else if (!hasSqlType && hasSqlMessage) {
            this.notification.add({
                title: _t("Validation Error"),
                message: "Missing Constraint Type",
                description: "Please select a Constraint Type for the SQL constraint.",
                type: "notification_panel",
                notificationType: "warning",
            });
            return;
        }
    }
    if (isPythonTab) {
        const hasDeps = !!deps;
        const hasCode = !!code;

        if (hasDeps && hasCode) {
            pythonConstraint = { deps, code };
        }
        // Case 2: Only Dependencies provided (no code)
        else if (hasDeps && !hasCode) {
            this.notification.add({
                title: _t("Validation Error"),
                message: "Missing Constraint Code",
                description: "Please provide Constraint Code for the Python constraint.",
                type: "notification_panel",
                notificationType: "warning",
            });
            return;
        }
        else if (!hasDeps && hasCode) {
            this.notification.add({
                title: _t("Validation Error"),
                message: "Missing Constraint Fields",
                description: "Please provide Constraint Fields for the Python constraint.",
                type: "notification_panel",
                notificationType: "warning",
            });
            return;
        }
    }
    const result = {};

    if (sqlConstraint) {
        result.sql_constraint = sqlConstraint;
    }

    if (pythonConstraint) {
        result.python_constraint = pythonConstraint;
    }

    this.props.onConfirm(result);
    this.props.close();
}

    cancel() {
        if (this.props.onCancel) {
            this.props.onCancel();
        }
        this.props.close();
    }

    getWarningSeverity() {
        if (!this.state.nullWarning.show) return null;
        const percentage = this.state.nullWarning.affectedPercentage;
        if (percentage > 50) return "danger";
        if (percentage > 25) return "warning";
        return "info";
    }
    switchTab(tabName) {
    this.state.activeTab = tabName;
    this.render();
}
    onConstraintCodeChange(value) {
        this.state.code = value;
        this.state.edited=true

    }
        openConstraintsPopover(ev) {
        const target = ev.currentTarget;

        this.popover.open(target, {
            resModel: this.props.model,
            path: "",
            showSearchInput: true,
            followRelations: false,
            filter: () => true,

            update: (path) => {
                const arr = this.state.deps
                    .split(",")
                    .map((x) => x.trim())
                    .filter((x) => x);

                if (!arr.includes(path)) arr.push(path);
                this.state.deps = arr.join(", ");
            },
        });
    }
}
patch(CodeEditor, {
    props: {
        ...CodeEditor.props,
        lang: { type: String, optional: true },
        height: { type: [String, Number], optional: true },
    }
});

ConstraintDialog.components = {Dialog, CodeEditor};