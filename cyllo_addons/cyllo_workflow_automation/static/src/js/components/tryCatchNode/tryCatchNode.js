/** @odoo-module */
const { useState, useRef, onMounted } = owl;
import { ConfigurationBase } from "../configurationBase/configurationBase";

/**
 * TryCatchNode — modal configuration for the Try/Catch node.
 *
 * The Try/Catch node wraps a branch of workflow nodes inside a Python
 * try/except block.  Two output ports are exposed:
 *
 *   Output 1 (top / "try body")   — nodes to execute inside the try block.
 *   Output 2 (bottom / "catch body") — nodes to execute when an exception
 *                                      is caught.
 *   Output 3 ("continue")         — nodes that execute after the try/except
 *                                    block regardless of the outcome.
 *
 * Configuration options:
 *   - label            — display label for the node.
 *   - errorVariable    — name of the Python variable holding the exception
 *                        (default: "error").
 *   - errorTypes       — comma-separated list of exception class names to
 *                        catch (default: "Exception").
 */
export class TryCatchNode extends ConfigurationBase {
    setup() {
        super.setup();
        this.labelInput = useRef("labelInput");

        this.tryCatchState = useState({
            errorVariable: "error",
            errorTypes: "Exception",
            labelError: false,
            varError: false,
            typesError: false,
        });

        onMounted(() => {
            if (this.labelInput.el) this.labelInput.el.focus();
            // Restore previously saved values
            this.tryCatchState.errorVariable =
                this.fieldState.try_catch_error_variable || "error";
            this.tryCatchState.errorTypes =
                this.fieldState.try_catch_error_types || "Exception";
        });
    }

    // ── Handlers ─────────────────────────────────────────────────────────────

    setLabel(value) {
        this.fieldState.label = value;
        this.tryCatchState.labelError = false;
        this.env.bus.trigger("CHANGE-LABEL", {
            label: value,
            nodeId: this.props.id,
        });
    }

    setErrorVariable(value) {
        this.tryCatchState.errorVariable = value.trim();
        this.tryCatchState.varError = false;
    }

    setErrorTypes(value) {
        this.tryCatchState.errorTypes = value;
        this.tryCatchState.typesError = false;
    }

    // ── Validation ───────────────────────────────────────────────────────────

    validateForm() {
        const errors = {};

        if (!this.fieldState.label || !this.fieldState.label.trim()) {
            this.tryCatchState.labelError = true;
            errors.label = "Label is required.";
        }

        const varName = (this.tryCatchState.errorVariable || "").trim();
        if (!varName) {
            this.tryCatchState.varError = true;
            errors.var = "Error variable name is required.";
        } else if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(varName)) {
            this.tryCatchState.varError = true;
            errors.var =
                "Error variable name must start with a letter/underscore and contain only alphanumeric characters.";
        }

        const types = (this.tryCatchState.errorTypes || "").trim();
        if (!types) {
            this.tryCatchState.typesError = true;
            errors.types =
                "At least one exception type is required (e.g. 'Exception').";
        }

        return { isValid: Object.keys(errors).length === 0, errors };
    }

    // ── Code Generation ───────────────────────────────────────────────────────

    /**
     * Generate the opening "try:" line that goes into node.code.
     * The except clause header is injected via node.else_setup_code so that
     * the existing traverse() logic in workflow_automation.js can append it
     * before the catch-branch children.
     */
    generateCode() {
        return "try:";
    }

    /**
     * Build the "except <Types> as <var>:" line stored in else_setup_code.
     * The traverse() function already renders else_setup_code when child2
     * is present, but for the try/catch we need the except syntax, not "else:".
     * We store a special marker that generateExceptHeader() will produce at
     * code-generation time.
     */
    generateExceptHeader() {
        const varName = (this.tryCatchState.errorVariable || "error").trim();
        const types = (this.tryCatchState.errorTypes || "Exception")
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean)
            .join(", ");
        const typesPart =
            types && types !== "Exception" ? `(${types})` : types || "Exception";
        return `except ${typesPart} as ${varName}:`;
    }

    // ── Confirm ──────────────────────────────────────────────────────────────

    async onConfirm() {
        const { isValid, errors } = this.validateForm();
        if (!isValid) {
            this.env.services.effect.add({
                title: "Validation Error",
                message: "Unable to save Try/Catch node.",
                description: Object.values(errors).join("\n"),
                type: "notification_panel",
                notificationType: "warning",
            });
            return;
        }

        // Persist config into fieldState
        this.fieldState.try_catch_error_variable =
            this.tryCatchState.errorVariable.trim();
        this.fieldState.try_catch_error_types =
            this.tryCatchState.errorTypes.trim();
        // Store the except header in else_setup_code so traverse() can render it
        this.fieldState.else_setup_code = this.generateExceptHeader();

        const code = this.generateCode();
        this.state.used_variables = {};

        this.props.onConfirm(this.fieldState, code, this.state.used_variables);
        this.props.close();
    }
}

TryCatchNode.template = "TryCatchNode";
