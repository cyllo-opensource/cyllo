/** @odoo-module */
import {Component, useState, onWillUpdateProps, onMounted} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {Pager} from "@web/core/pager/pager";
import {Lines} from "./lines"

export class LinesHeader extends Component {
    /**
     * Component class for managing the header of move lines.
     */
    move_lines_limit = 100

    setup() {
        this.action = useService('action');
        this.orm = useService('orm');
        this.company = useService("company");
        this.state = useState({
            showLines: false,
        })
        this.pager = useState({
            total: this.props.mlTotal.move_lines_count,
            limit: this.move_lines_limit,
            offset: 0,
        })

        onWillUpdateProps((nextProps) => {
            this.pager.total = nextProps.mlTotal.move_lines_count
            this.pager.limit = this.move_lines_limit
            this.pager.offset = 0
        })

        this.env.bus.addEventListener('UnFoldAll', () => this.state.showLines = true)
        this.env.bus.addEventListener('FoldAll', () => this.state.showLines = false)
         onMounted(() => {
            if (this.props.openAccounts?.length &&
                this.props.openAccounts.includes(this.props.mlTotal.partner_id)) {
                this.state.showLines = true
            }
        })
    }

    async onPagerChanged({offset, limit}, hasNavigated) {
        /**
         * Handles the pager change event.
         *
         * @param {object} pagerData - The pager data including offset and limit.
         * @param {boolean} hasNavigated - Indicates whether navigation has occurred.
         * @returns {Promise<void>} A promise that resolves when the pager change is handled.
         */
        this.pager.offset = offset
        this.pager.limit = limit
        await this.getPartnerMoveLines()
    }

    get boldHeader() {
        /**
         * Returns the CSS class for bolding the header.
         *
         * @returns {string} The CSS class for bolding the header.
         */
        return this.state.showLines && 'fw-bolder';
    }

    get filterContext() {
        /**
         * Returns the filter context.
         *
         * @returns {object} The filter context.
         */
        return {
            date: this.props.date,
            partners: this.props.mlTotal.partner_id,
            company_ids: this.company.activeCompanyIds
        }
    }

    get args() {
        /**
         * Returns the arguments for retrieving move lines.
         *
         * @returns {Array<any>} The arguments for retrieving move lines.
         */
        return [, this.props.accountType, this.pager.offset, this.pager.limit]
    }

    onClickHeader() {
        this.state.showLines = !this.state.showLines
        this.props.callBackFn && this.props.callBackFn(this.props.mlTotal.partner_id, this.state.showLines)
    }

    async getPartnerMoveLines() {
        /**
         * Retrieves the move lines of the partner when changing pages and returns the data for the next page of move lines.
         *
         * @returns {Promise} - A promise that resolves to the move lines data for the next page.
         */
        if (!this.props.date) {
            return;
        }
        this.props.mlTotal.move_lines = await this.orm.call(this.props.model, 'get_partner_move_lines', [...this.args], this.filterContext)
    }

    async openPartner(partnerId) {
        /**
         * Opens the partner form view for a specific partner.
         *
         * @param {Number} partnerId - The ID of the partner.
         * @returns {Promise} - A promise that resolves to the result of the action.
         */
        await this.props.saveSession()
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: 'res.partner',
            res_id: partnerId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async goToJournalItem(partnerId) {
        /**
         * Navigates to the journal items list view filtered by partner ID.
         *
         * @param {Number} partnerId - The ID of the partner to filter the journal items.
         * @returns {Promise} - A promise that resolves to the result of the action.
         */
        await this.props.saveSession()
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: 'account.move.line',
            name: "Journal Items",
            search_view_id: [this.props.searchViewId, 'search'],
            views: [[false, "list"]],
            target: "current",
            context: {
                search_default_partner_id: partnerId,
                search_default_trade_receivable: this.props.accountType === "asset_receivable",
                search_default_trade_payable: this.props.accountType === "liability_payable",
                search_default_date_before: 1,
                date_to: this.props.date,
                search_default_unreconciled: 1
            }
        });
    }
}

LinesHeader.template = "LinesHeader"
LinesHeader.components = {
    Lines,
    Pager
}