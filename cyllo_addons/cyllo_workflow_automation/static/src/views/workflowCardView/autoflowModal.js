/** @odoo-module */
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Record } from "@web/model/record";

const { useState, Component } = owl;
import { _t } from "@web/core/l10n/translation";


export class autoflowModal extends Component {
    // This is a class for configuration dialog box
    setup() {
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
                this.action = useService("action");

        this.notification = useService("notification");
        this.defaultCondition = null;
        this.state = useState({
            name: "",

        })
    }

    async configSave(ev){
        const c = await this.orm.create("work.auto", [{'name':this.state.name}])
    }

    onDiscard() {
        this.props.close();
    }
}

// Define the tempalate and components for the ConfigurationDialog component
autoflowModal.template = "cyllo_workflow_automation.autoflowModal";