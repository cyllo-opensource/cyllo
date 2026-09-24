/** @odoo-module **/
import {Component, useState} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import { useBus, useService } from "@web/core/utils/hooks";
import { FirstPage } from '@cyllo_studio/js/new_app/new_app_templates';
import { PromptDialog } from "../dialog/PromptDialog";

export class AIPage extends Component {
    setup() {
        this.rpc = useService('rpc')
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        this.action = useService("action");
        this.state = useState({
            appName: "",  // Property to store the input from the user
            showModelInput: false,
            modelName:false,
        });
    }
    CreateApp(){
         this.dialogService.add(FirstPage, {
            title: 'Cyllo Studio',
            })
         this.onClose();
    }
    async CreateAppWithAI() {
        this.env.bus.trigger('TOGGLE_MENU_SIDEBAR', { hideMenu: true });
        const currentUrl = window.location.href;
        const fragment = currentUrl.split('#')[1]
        const params = new URLSearchParams(fragment);;
        localStorage.setItem('ExistingStudioPage', [currentUrl, params.get('menu_id')])
        await this.env.bus.trigger("IS_AI", {
            isAI: true,
        });
        this.action.doAction({
            type: "ir.actions.client",
            tag: "PromptDialog",
        });
    }
    onClose() {
        this.props.close();
    }
}
AIPage.template = "cyllo_studio_ai.cyllo_studio_ai_page_content";
AIPage.components = { ...AIPage.components, Dialog };
