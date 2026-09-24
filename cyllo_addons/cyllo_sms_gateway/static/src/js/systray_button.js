/** @odoo-module**/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
/**
 * We define this module for the function of wizard button
 *
 */
export class SendSMS extends Component {
    static props = ["*"];
    /**
     * Click function for opening wizard and returning back to the user
     */
    onClickAction() {
        this.env.services.action.doAction({
            name: 'Send SMS',
            type: "ir.actions.act_window",
            res_model: "send.sms",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        })
    }
}
SendSMS.template = "SendSMS"
registry.category("systray").add("send_SMS", {Component: SendSMS}, {sequence: 23});