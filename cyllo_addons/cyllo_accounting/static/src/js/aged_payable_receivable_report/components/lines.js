/** @odoo-module */
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";

export class Lines extends Component {
    setup(){
        this.action = useService('action');
    }

    goToJournalEntry(moveId) {
        /**
         * Navigates to the journal entry form view for a specific account move.
         *
         * @param {Number} moveId - The ID of the account move.
         * @returns {Promise} - A promise that resolves to the result of the action.
         */

        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: 'account.move',
            res_id: moveId,
            views: [[false, "form"]],
            target: "current",
        });
    }

}
Lines.template = "Lines"
Lines.components = {Dropdown, DropdownItem}
