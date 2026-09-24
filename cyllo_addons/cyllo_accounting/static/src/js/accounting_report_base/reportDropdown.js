/* @odoo-module */


import {Component, useState} from "@odoo/owl";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";

export class ReportDropdown extends Component {
    static props = ['*']

    setup() {
        this.env.bus.addEventListener("UNFOLD_ALL:REPORT_LINE", () => this.state.showChildren = true);
        this.env.bus.addEventListener("FOLD_ALL:REPORT_LINE", () => this.state.showChildren = false);
        this.state = useState({
            showChildren: false
        })
        if (this.props.openAccounts?.length) {
            const {account_id} = this.props.sumRecords[this.props.account][0]
            if (this.props.openAccounts.includes(account_id)) {
                this.state.showChildren = true
            }
        }
        if (this.props.subAccounts?.length) {
            const accountId = this.props.accountDataPage[this.props.account]?.account_id
            if (this.props.subAccounts.includes(accountId)) {
                this.state.showChildren = true
            }
        }
    }

    get caretDropdown() {
        return this.state.showChildren ? "fa fa-caret-down" : "fa fa-caret-right"
    }

    onClickParent() {
        this.state.showChildren = !this.state.showChildren
        if (this.props.callBackKey && typeof this[`${this.props.callBackKey}`] === 'function') {
            this[`${this.props.callBackKey}`]()
        }
    }
    generalLedger() {
        const {account_id} = this.props?.sumRecords[this.props.account][0]
        this.props.onClickAccount && this.props.onClickAccount(account_id, this.state.showChildren)
    }
    bankBook() {
        const accountId = this.props.accountDataPage[this.props.account]?.account_id
        this.props.onClickAccount && this.props.onClickAccount(accountId, this.state.showChildren)
    }
    cashBook() {
        this.bankBook()
    }
}

ReportDropdown.template = "ReportDropdown";
ReportDropdown.components = {Dropdown, DropdownItem}