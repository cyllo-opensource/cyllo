/** @odoo-module **/

/**
 * RibbonProperties Component
 *
 * Provides the properties sidebar for a Kanban ribbon element in Studio.
 * Allows editing the ribbon's label, color, visibility, and domain conditions.
 * Integrates with ExpressionEditorDialog for domain expressions.
 */
const { Component, useState, onMounted, useExternalListener, onWillUpdateProps } = owl;
import { ExpressionEditorDialog } from "@web/core/expression_editor_dialog/expression_editor_dialog";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { handleUndoRedo } from "@cyllo_studio/js/utils/undo_redo_utils";
import { _t } from "@web/core/l10n/translation";

export class RibbonProperties extends Component {
    static template = 'cyllo_studio.RibbonProperties';

    setup() {
        this.addDialog = useOwnedDialogs();
        this.notification = useService('effect');
        this.action = useService('action');
        this.rpc = useService('rpc');

        this.state = useState({
            showDropdown: false,
            is_edit: false,
        });

        this.properties = useState({
            string: '',
            color: 'text-bg-danger',
            invisible: 'False',
        });

        this._autoSaving = false;
        this._autoSavePending = false;
        this._saved = false;

        this.autoSaveHandler = () => {
            if (!this.properties.string) {
                return;
            }
            this.autoSave();
        };
        onMounted(() => {
            this.action_area = document.querySelector(".o_action_manager");
            const isEdit = this.props.properties?.is_edit || this.props.is_edit;
            if (isEdit) {
                this.properties.string = this.props.properties?.string || this.props.string || '';
                this.properties.color = this.props.properties?.color || this.props.color || 'text-bg-danger';
                this.properties.invisible = this.props.properties?.invisible || this.props.invisible || 'False';
                this.state.is_edit = true;
            } else {
                this.state.is_edit = false;
            }
        });

        onWillUpdateProps((nextPropsRaw) => {
            const nextProps = nextPropsRaw?.props || nextPropsRaw;
            const isEdit = nextProps.properties?.is_edit || nextProps.is_edit;

            if (isEdit) {
                this.properties.string = nextProps.properties?.string || nextProps.string || '';
                this.properties.color = nextProps.properties?.color || nextProps.color || 'text-bg-danger';
                this.properties.invisible = nextProps.properties?.invisible || nextProps.invisible || 'False';
                this.state.is_edit = true;
                this._saved = false;
            } else {
                this.properties.string = '';
                this.properties.color = 'text-bg-danger';
                this.properties.invisible = 'False';
                this.state.is_edit = false;
                this._saved = false;
            }
        });
    }

    autoSave() {
        if (this._autoSaving) { this._autoSavePending = true; return; }
        this._autoSaving = true;
        this.doSave().finally(() => {
            this._autoSaving = false;
            if (this._autoSavePending) { this._autoSavePending = false; this.autoSave(); }
        });
    }

    async doSave() {
        if (!this.properties.string) {
            return this.notification.add({
                title: _t("Validation Error"),
                message: "Unable to save the ribbon.",
                description: "Please provide a label to save",
                type: "notification_panel",
                notificationType: "warning",
            });
        }
        this.env.services.ui.block();
        try {
            const viewType = this.props.viewDetails.viewType;
            let response;
            const isEditMode = this.state.is_edit || this._saved;

            if (!isEditMode) {
                // ADD logic
                const endpoint = viewType === "form"
                    ? "cyllo_studio/form/add/ribbon"
                    : "cyllo_studio/kanban/add/ribbon";

                let requestData = {
                    path: this.props.properties.elementInfo.path,
                    position: this.props.properties.elementInfo.position,
                    ...this.props.viewDetails,
                    properties: { ...this.properties },
                    viewType: this.props.viewDetails.viewType,
                    viewId: this.props.viewDetails.viewId,
                    model: this.props.viewDetails.model,
                };

                if (viewType === "form") {
                    requestData = {
                        viewType: this.props.viewDetails.viewType,
                        viewId: this.props.viewDetails.viewId,
                        model: this.props.viewDetails.model,
                        path: this.props.properties.elementInfo.path,
                        properties: { ...this.properties },
                        position: this.props.properties.elementInfo.position,
                        ...this.props.viewDetails,
                    };
                }

                response = await this.rpc(endpoint, requestData);
                this._saved = true;
            } else {
                // UPDATE logic
                const endpoint = viewType === "form"
                    ? "cyllo_studio/form/update/ribbons"
                    : "cyllo_studio/kanban/update/ribbons";

                let targetPath = this.props.properties?.elementInfo?.path || this.props.path;

                // For ribbons just added in this session, resolve their new cy-xpath
                if (this._saved && !this.state.is_edit) {
                    const ribbons = document.querySelectorAll('div.ribbon[cy-xpath]');
                    let matchedRibbon = Array.from(ribbons).find(r => {
                        const span = r.querySelector('span');
                        return span && span.textContent.trim() === this.properties.string && span.classList.contains(this.properties.color);
                    });
                    if (!matchedRibbon) {
                         const parentEl = document.querySelector(`[cy-xpath="${targetPath}"]`);
                         if (parentEl) {
                             matchedRibbon = parentEl.querySelector('div.ribbon[cy-xpath]');
                         }
                    }
                    if (matchedRibbon) {
                        targetPath = matchedRibbon.getAttribute('cy-xpath');
                    }
                }

                if (!targetPath) {
                    throw new Error("Could not determine ribbon path for update.");
                }

                let requestData = {
                    viewId: this.props.viewDetails.viewId,
                    viewType: this.props.viewDetails.viewType,
                    model: this.props.viewDetails.model,
                    active_fields: this.props.viewDetails.active_fields || this.props.viewDetails.allFields,
                    ribbons: [{
                        path: targetPath,
                        invisible: this.properties.invisible,
                        color: this.properties.color,
                        firstElementContent: this.properties.string,
                        hasEdit: true,
                        hasDelete: false
                    }]
                };

                response = await this.rpc(endpoint, requestData);
            }

            if (response) {
                handleUndoRedo(response);
            }
        } catch (error) {
            this.notification.add({
                title: _t("Error"),
                message: "Failed to save ribbon",
                description: error.message || "An unexpected error occurred",
                type: "notification_panel",
                notificationType: "danger",
            });
        } finally {
            this.action.doAction("studio_reload");
            this.env.services.ui.unblock();
        }
    }

    /**
     * Cancels ribbon editing and closes the sidebar.
     *
     * @param {Event} ev - Triggering event
     */
    async cancelribbon(ev) {
        this.env.bus.trigger("CLEAR-MENU");
        this.action.doAction('studio_reload');
    }
    /**
     * Returns the available color options for ribbons.
     */
    get colors() {
        return {
            'text-bg-primary': 'Primary',
            'text-bg-secondary': 'Secondary',
            'text-bg-success': 'Success',
            'text-bg-info': 'Info',
            'text-bg-warning': 'Warning',
            'text-bg-danger': 'Danger'
        };
    }

    /**
     * Handles selecting a color for the ribbon.
     *
     * @param {string} color - CSS class representing the color
     */
    handleSelectColor(color) {
        let span = this.props.element?.querySelector("span");
        if (this.props.element && !span) {
            span = document.createElement("span");
            this.props.element.appendChild(span);
        }
        if (span) {
            span.className = color;
        }

        this.properties.color = color;
        this.state.showDropdown = false;
        this.autoSave();
    }

    /**
     * Updates the ribbon's label text.
     *
     * @param {Event} event - Input change event
     */
    handleLabelChange({ target }) {
        //        this.props.element.firstChild.textContent = target.value;
        //        this.properties.string = target.value;
        let span = this.props.element?.querySelector("span");

        if (this.props.element && !span) {
            span = document.createElement("span");
            span.className = this.properties.color || "text-bg-danger";
            this.props.element.appendChild(span);
        }
        if (span) {
            span.textContent = target.value;
        }
        this.properties.string = target.value;
    }

    /**
     * Adds or removes click/mousedown listeners for auto-saving.
     *
     * @param {boolean} isAdd - True to add listeners, false to remove
     */
    handleListener(isAdd = true) {
        if (isAdd) {
            document.addEventListener("click", this.autoSaveHandler, { capture: true });
            document.addEventListener("mousedown", this.autoSaveHandler, { capture: true });
        } else {
            document.removeEventListener("click", this.autoSaveHandler, { capture: true });
            document.removeEventListener("mousedown", this.autoSaveHandler, { capture: true });
        }
    }

    /**
     * Updates the ribbon's visibility based on domain radio selection.
     *
     * @param {Event} target - Radio input event
     */
    onDomainRadioClick({ target }) {
        this.properties.invisible = target.checked ? 'True' : 'False';
        this.autoSave();
    }
    /**
     * Opens the ExpressionEditorDialog for editing the ribbon's domain expression.
     *
     * @param {Event} target - Click event
     */
    async onDomainClick({ target }) {
        this.handleListener(false)
        this.addDialog(ExpressionEditorDialog, {
            resModel: this.props.viewDetails.model,
            fields: this.props.viewDetails.allFields,
            expression: this.properties.invisible,
            onConfirm: (expression) => this.handleDomain(expression),
            onClose: () => this.handleListener(),
        });
    }
    /**
     * Handles updating the domain expression after editing.
     *
     * @param {string} expression - The new domain expression
     */
    handleDomain(expression) {
        this.handleListener()
        this.properties.invisible = expression;
        this.autoSave();
    }

}
