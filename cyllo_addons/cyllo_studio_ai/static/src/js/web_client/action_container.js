/** @odoo-module **/
import { ActionContainer } from '@web/webclient/actions/action_container';
import { patch } from '@web/core/utils/patch';
import { useBus, useService } from "@web/core/utils/hooks";
import { xml, useState, onWillUpdateProps, onRendered ,onMounted} from "@odoo/owl";

patch(ActionContainer.prototype,{
    setup(){
        super.setup()
        this.action = useService("action");
        this.state = useState({
            showMenuSidebar: true,
            isPromptDialog: false,
        });
            onRendered(() => {
            if(this.info.componentProps?.action?.tag == 'PromptDialog'){
                this.props.updateState("isAI", true);
            }
        })
    }
})
ActionContainer.props = {
    ...ActionContainer.props,
    isAI: { type: Boolean, optional: true },
};
ActionContainer.template = "cyllo_studio_ai.ActionContainer"

