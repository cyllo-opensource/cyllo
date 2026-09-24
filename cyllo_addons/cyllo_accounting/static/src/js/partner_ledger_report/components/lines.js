/** @odoo-module */
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";

export class LinesPartnerLedger extends Component {
    setup(){
        this.action = useService('action');
    }

    async goToJournalEntry(move_id) {
        /**
         * Navigates to the journal entry form view based on the selected event target.
         *
         * @param {Event} ev - The event object triggered by the action.
         * @returns {Promise} - A promise that resolves to the result of the action.
         */
        await this.props.saveSession()
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: 'account.move',
            res_id: move_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}
LinesPartnerLedger.template = "LinesPartnerLedger"
LinesPartnerLedger.components = {Dropdown, DropdownItem}
