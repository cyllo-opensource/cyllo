/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";


export class CallOptionModal extends Component {
    static template = "cyllo_twilio_voice_call.CallOptionModal";
    static components = { Dialog };

    static props = {
        phoneNumber: String,
        onSelect: Function,
        close: Function,
    };

    setup() {
    this.dialog = useService("dialog");
    }
    select(option) {
        this.props.onSelect(option);
        this.env.services.dialog.closeAll();
    }
    closeModal(){
    this.env.services.dialog.closeAll();
    }
}