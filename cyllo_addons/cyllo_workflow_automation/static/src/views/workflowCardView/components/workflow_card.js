/* @odoo-module */
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {Component, onWillStart, onWillUpdateProps, useExternalListener, useState} from "@odoo/owl";
import { RenameAutomationDialog } from "../../../js/components/renameAutomationDialog/renameAutomationDialog";
import {
    getImageSrcFromRecordInfo,
} from "@web/views/kanban/kanban_record";

export class WorkflowCard extends Component {
    setup() {
        this.state = useState({
            img: "",
            icon: "",
            // Track in-progress toggle to prevent double-clicks firing twice.
            toggling: false,
            active: true,
            menuOpen: false,
        });
        this.action = useService('action')
        this.orm = useService("orm");
        this.dialogService = useService('dialog')
        this.notification = useService('notification')

        const syncActiveState = (props) => {
            const active = props?.value?.data?.active;
            this.state.active = active !== false;
        };
        syncActiveState(this.props);

        onWillStart(async () => {
            if (this.props.value.data.function_id) {
                this.state.icon = await this.orm.read('work.function', [this.props.value.data.function_id[0]], ['icon'])
            }
        });
        onWillUpdateProps((nextProps) => {
            syncActiveState(nextProps);
        });
        useExternalListener(document, "click", this.onDocumentClick, { capture: true });
    }

    get Image() {
        const {
            value: record,
            model
        } = this.props
        return getImageSrcFromRecordInfo(record, model, "image_1920", this.recordId)
    }

    get WorkflowCard() {
        return this.props.value?.data || {};
    }

    get recordId() {
        return this.props.value?.resId
            || this.props.value?.evalContext?.id
            || this.WorkflowCard.id;
    }

    get triggerNames() {
        const triggers = this.WorkflowCard.trigger_function_ids || [];
        return (triggers || []).map(item => item?.[1]).filter(Boolean);
    }

    get validRecordIds() {
        const recordId = this.recordId;
        if (typeof recordId === "number" && Number.isInteger(recordId) && recordId > 0) {
            return [recordId];
        }
        if (typeof recordId === "string" && /^\d+$/.test(recordId)) {
            const parsedId = Number.parseInt(recordId, 10);
            if (parsedId > 0) {
                return [parsedId];
            }
        }
        return [];
    }

    async openView() {
        this.closeMenu();
        if (this.props.model == "work.auto") {
            this.action.doAction({
                target: "current",
                tag: "automation_view",
                type: "ir.actions.client",
                context: {
                    rec_id: this.recordId
                }
            })
        }
    }

    get isActive() {
        return this.state.active;
    }

    get isReusable() {
        return this.WorkflowCard.is_reusable === true;
    }

    toggleMenu(ev) {
        ev.stopPropagation();
        this.state.menuOpen = !this.state.menuOpen;
    }

    closeMenu() {
        this.state.menuOpen = false;
    }

    async onClickRename() {
        this.closeMenu();
        const currentName = this.WorkflowCard.name || "";
        this.dialogService.add(RenameAutomationDialog, {
            title: _t("Rename Automation"),
            initialName: currentName,
            onConfirm: async (trimmedName) => {
                if (!trimmedName || trimmedName === currentName) {
                    return;
                }
                try {
                    await this.orm.write("work.auto", [this.recordId], { name: trimmedName });
                    this.notification.add(_t("Workflow renamed."));
                    await this._reloadList();
                } catch (error) {
                    this.notification.add(
                        error?.message || _t("Unable to rename the workflow."),
                        { type: "danger" }
                    );
                    throw error;
                }
            },
        });
    }

    onDocumentClick(ev) {
        if (!this.state.menuOpen) {
            return;
        }
        if (ev.target?.closest?.(".auto-card-more")) {
            return;
        }
        this.closeMenu();
    }

    /**
     * Reload the card listing in-place using the relational model's own
     * load() method.  This is far more reliable than doAction() because:
     *   • No full page navigation / component teardown
     *   • No race between the write RPC and the reload
     *   • Preserves the current search domain & filters
     *   • Works correctly for both activate AND deactivate
     *
     * The RelationalModel root is reachable via props.value.model.root.
     * We call load() with active_test=false so that the freshly toggled
     * record remains visible right after toggling (the view's own search
     * filters will hide it on the next user-initiated search if needed).
     */
    async _reloadList() {
        try {
            await this.action.doAction('soft_reload');
        } catch (e) {
            const model = this.props.value?.model;
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "work.auto",
                views: [[false, "workflowCard"], [false, "list"], [false, "form"]],
                target: "main",
                name: "Workflow Automation",
                context: {
                    ...(model?.config?.context || {}),
                    active_test: false,
                },
            });
        }
    }

    /**
     * Perform the actual active/inactive write then reload the list.
     * Marked with a toggling guard so rapid double-clicks can't queue
     * two simultaneous writes.
     */
    async _doToggleActive(newActive) {
        if (this.state.toggling) return;
        this.state.toggling = true;
        this.closeMenu();
        const previousActive = this.state.active;
        this.state.active = newActive;
        try {
            await this.orm.write('work.auto', [this.recordId], {
                active: newActive,
            }, {
                context: { active_test: false },
            });
            await this._reloadList();
            if (newActive) {
                this.notification.add(_t("Workflow activated."));
            } else {
                this.notification.add(_t("Workflow deactivated."));
            }
        } catch (error) {
            this.state.active = previousActive;
            this.notification.add(
                error?.message || _t("Unable to update the workflow status."),
                { type: "danger" }
            );
            throw error;
        } finally {
            this.state.toggling = false;
        }
    }

    async toggleActive(ev) {
        ev?.stopPropagation?.();

        // Prevent double-clicks while the first toggle is in flight.
        if (this.state.toggling) return;

        const newActive = !this.isActive;

        // ── Hard block: deactivating a reusable automation that is in use ────
        // If this automation is reusable AND other active workflows reference
        // it via a "Reuse Automation" node, we BLOCK the deactivation entirely
        // and show a warning popup listing the dependent workflows.
        // The user must first remove/disconnect those references before they
        // can deactivate this automation — there is no "confirm and proceed".
        if (!newActive && this.isReusable) {
            let dependents = [];
            try {
                dependents = await this.orm.call(
                    'work.auto', 'get_dependents', [[this.recordId]]
                );
            } catch (e) {
                console.warn('get_dependents RPC failed:', e);
            }

            if (dependents && dependents.length > 0) {
                // Build the dependent workflow name list for the warning.
                const nameList = dependents
                    .map((d, i) => `${i + 1}. ${d.name}`)
                    .join('\n');

                // Show a blocking warning dialog (OK only — no "proceed" option).
                // Deactivation is fully stopped here.
                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Cannot Deactivate — Workflow In Use"),
                    body: _t(
                        "This reusable automation is currently used by %s active workflow(s):\n\n%s\n\n" +
                        "Please remove or disconnect the 'Reuse Automation' node(s) in those workflows before deactivating this automation.",
                        dependents.length,
                        nameList
                    ),
                    // Only show the OK/close button — no confirm-to-proceed.
                    confirmLabel: _t("OK, Got it"),
                    // No cancel callback — dialog closes on OK, nothing happens.
                });
                return; // ← deactivation is fully blocked, nothing written to DB
            }
        }

        // No dependents (or this is an activation) — proceed immediately.
        await this._doToggleActive(newActive);
    }

    onClickDelete() {
        this.closeMenu();
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Do you really want to Delete the record?"),
            confirm: (async () => {
                const recordIds = this.validRecordIds;
                if (!recordIds.length) {
                    return;
                }
                const domain = [['id', '!=', recordIds[0]]];
                this.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "work.auto",
                    views: [[false, "workflowCard"], [false, "list"], [false, "form"]],
                    target: "main",
                    name: "Workflow Automation",
                    domain,
                    context: {delete_node_id: recordIds[0]}
                })
                await this.orm.unlink("work.auto", recordIds)
            }),
        });
    }
}

WorkflowCard.template = `WorkflowCard`;
