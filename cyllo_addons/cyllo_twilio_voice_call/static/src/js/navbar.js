/* @odoo-module */
import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { useService } from "@web/core/utils/hooks";
import { useState, useSubEnv, onWillStart } from "@odoo/owl";
import { DialPad } from '@cyllo_twilio_voice_call/js/outgoing_call';
import { FetchIncomingCall } from '@cyllo_twilio_voice_call/js/incoming_call';


patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.user = useService("user");
        this.state = useState({
            showKeypad: false,
            number: null,
            showIncomingCall: false
        });
        this.props.showIncomingCall = this.state.showIncomingCall;
        useSubEnv({
            toggle_keypad: this.toggle_keypad.bind(this),
        });
        onWillStart(async () => {
            this.isAdmin = await this.user.hasGroup("cyllo_twilio_voice_call.group_cyllo_twilio_voice_call_admin");
            this.isUser = await this.user.hasGroup("cyllo_twilio_voice_call.group_cyllo_twilio_voice_call_user");
        });

        this.env.bus.addEventListener("CALL_ACTION", (ev) => {
              const detail = ev.detail || {};
              this.state.showKeypad = false
              this.toggle_keypad(detail.number);
        });


    },
    toggle_keypad(number) {
        this.state.showKeypad = !this.state?.showKeypad;
        this.state.number = number;

    }

});

NavBar.components = { ...NavBar.components, DialPad, FetchIncomingCall };
