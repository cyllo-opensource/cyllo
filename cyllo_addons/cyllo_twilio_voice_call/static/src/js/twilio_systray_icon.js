/** @odoo-module **/
import {registry} from "@web/core/registry";
import { Component} from "@odoo/owl";
import { DialPad } from '@cyllo_twilio_voice_call/js/outgoing_call'
import { FetchIncomingCall } from '@cyllo_twilio_voice_call/js/incoming_call'
import { session } from "@web/session";

export class TwilioSystrayIcon extends Component {

    }

TwilioSystrayIcon.template = "dial_button";
TwilioSystrayIcon.components = {
    DialPad,
    FetchIncomingCall
};
registry.category("systray").add("TwilioSystrayIcon", {
    Component: TwilioSystrayIcon,
    isDisplayed: () => session.has_twilio_group_access

});