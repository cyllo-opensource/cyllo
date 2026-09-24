/** @odoo-module */
import {Component, useState, onWillUpdateProps, onMounted} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {LinesPartnerLedger} from "./lines"
import {Pager} from "@web/core/pager/pager";


export class LinesHeaderPartnerLedger extends Component {
    setup() {
        this.action = useService('action');
        this.orm = useService('orm');
        this.state = useState({
            show_lines: false
        })

        this.env.bus.addEventListener('UnFoldAll', () => this.state.show_lines = true)
        this.env.bus.addEventListener('FoldAll', () => this.state.show_lines = false)
        this.pager = useState({
            total: this.props.partner_ledger_total.move_lines_count,
            limit: 100,
            offset: 0,
        })
        onWillUpdateProps((nextProps) => {
            //Something like custom dates change
            this.pager.total = nextProps.partner_ledger_total.move_lines_count
            this.pager.limit = 100
            this.pager.offset = 0
        })
        onMounted(() => {
            if (this.props.openAccounts?.length &&
                this.props.openAccounts.includes(this.props.partner_ledger_total.partner_id)) {
                this.state.show_lines = true
            }
        })
    }

    onClickHeader() {
        this.state.show_lines = !this.state.show_lines
        this.props.callBackFn && this.props.callBackFn(this.props.partner_ledger_total.partner_id, this.state.show_lines)
    }

    async onPagerChanged({offset, limit}, hasNavigated) {
        this.pager.offset = offset
        this.pager.limit = limit
        await this.getPartnerMoveLines()
    }

    get filterContext() {
        return {
            pager: true,
            startDate: this.props.filters.startDate,
            endDate: this.props.filters.endDate,
            partner_id: [this.props.partner_ledger_total.partner_id],
            account_type: this.props.account_type,
            parent_state: this.props.parentState
        }
    }

    get args() {
        return [this.pager.offset, this.pager.limit]
    }

    async getPartnerMoveLines() {
        this.props.partner_ledger_total.move_lines = await this.orm.call(this.props.model, 'get_report', [...this.args], this.filterContext)
    }

    async openPartner(partner_id) {
        /**
         * Opens the partner form view based on the selected event target.
         *
         * @param {Event} ev - The event object triggered by the action.
         * @returns {Promise} - A promise that resolves to the result of the action.
         */
        await this.props.saveSession()
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: 'res.partner',
            res_id: partner_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async goToJournalItem(partner_id) {
        /**
         * Navigates to the journal items list view based on the selected event target.
         *
         * @param {Event} ev - The event object triggered by the action.
         * @returns {Promise} - A promise that resolves to the result of the action.
         */
         await this.props.saveSession()
        let account_type = this.props.account_type;
        if (account_type && account_type.length > 0) {
            account_type = account_type.slice(0, 2);
        } else {
            account_type = ['asset_receivable', 'liability_payable']; // ^^
        }
        let parentState = this.props.parentState
        if (parentState) {
            parentState = ['draft', 'posted']
        } else {
            parentState = ['posted']
        }
        //TODO: FIXME?? why 2 account_type values for the payable and receivable ^^
        const payable = account_type.includes("Payable") || account_type.includes("liability_payable")
        const receivable = account_type.includes("Receivable") || account_type.includes("asset_receivable")
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: 'account.move.line',
            name: "Journal Items",
            search_view_id: [this.props.searchViewId, 'search'],
            views: [[false, "list"]],
            target: "current",
            context: {
                search_default_partner_id: partner_id,
                search_default_date_between: 1,
                date_from: this.props.filters.startDate,
                date_to: this.props.filters.endDate,
                search_default_group_by_account: 1,
                search_default_trade_payable: payable,
                search_default_trade_receivable: receivable,
                search_default_posted: parentState.length === 1
            }
        });
    }
}

LinesHeaderPartnerLedger.template = "LinesHeaderPartnerLedger"
LinesHeaderPartnerLedger.components = {
    LinesPartnerLedger,
    Pager
}