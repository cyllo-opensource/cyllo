/** @odoo-module **/
import {
 Component, useState
  } from "@odoo/owl";
import {
 CodeEditor
 } from "@web/core/code_editor/code_editor";
import {
 usePopover
  } from "@web/core/popover/popover_hook";
import {
 useService
  } from "@web/core/utils/hooks";
import {
 _t
 } from "@web/core/l10n/translation";
import {
 ModelFieldSelectorPopover
 } from "@web/core/model_field_selector/model_field_selector_popover";
import {
 Dialog
 } from "@web/core/dialog/dialog";

export class ComputeDialog extends Component {
    setup() {
        this.state = useState({
            deps: this.props.dependencies || "",
            code: this.props.code || "",
        });
        this.notification = useService("effect");

        this.popover = usePopover(ModelFieldSelectorPopover, {
            popoverClass: "o_model_field_selector_popover",
        });
    }

    openDependenciesPopover(ev) {
        const target = ev.currentTarget;

        this.popover.open(target, {
            resModel: this.props.resModel,
            path: "",
            showSearchInput: true,
            followRelations: true,
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

//    clearDeps() {
//        this.state.deps = "";
//    }

    onComputeCodeChange(value) {
        this.state.code = value;
        this.state.edited=true

    }


    confirm() {
        const deps = (this.state.deps || "").trim();
        const code = (this.state.code || "").trim();
        if (!deps && !code) {
            this.props.onConfirm({
                deps: "",
                code: "",
                disableCompute: true,
            });
            this.props.close();
            return;
        }
        if ((deps && !code) || (!deps && code)) {
            this.notification.add({
                title: _t("Validation Error"),
                message: "Both fields required",
                description: "Please provide both Dependencies and Compute Code, or clear both to disable compute.",
                type: "notification_panel",
                notificationType: "warning",
            });
            return;
        }
        this.props.onConfirm({
            deps,
            code,
            disableCompute: false,
        });

        this.props.close();
    }

    onCancel() {
        this.props.onConfirm({
            deps: "",
            code: "",
            disableCompute: true,
        });
        this.props.close();
    }

    }

ComputeDialog.template = "cyllo_studio.ComputeDialog";
ComputeDialog.components = { Dialog, CodeEditor };
