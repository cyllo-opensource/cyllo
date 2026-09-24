/** @odoo-module */
import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";

export class QualityInstructions extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            instruction: "",
            readonly: false,
        });

        onWillStart(async () => {
            if (this.props.action.params.instruction) {
                this.state.instruction = this.props.action.params.instruction;
                this.state.readonly = true;
            } else if (this.props.action.params.res_id) {
                const [record] = await this.orm.read("quality.inspection", [this.props.action.params.res_id], ["instruction"]);
                this.state.instruction = record.instruction || "";
                this.state.readonly = false;
            }
        });
    }

    get title() {
        return this.state.readonly ? "Quality Instructions" : "Add Quality Instructions";
    }

    cancel() {
        this.action.doAction({ type: "ir.actions.act_window_close" });
    }

    async onSave() {
        await this.orm.write("quality.inspection", [this.props.action.params.res_id], {
            instruction: this.state.instruction,
        });
        this.cancel();
    }
}
QualityInstructions.template = "cyllo_quality.InstructionDialog";
QualityInstructions.components = { Dialog };
registry.category("actions").add("quality_instruction_action", QualityInstructions);


