/* @odoo-module */

import {ReportDropdown} from "../accounting_report_base/reportDropdown";
import {useState, onWillStart, onWillUpdateProps} from "@odoo/owl";
import {Pager} from "@web/core/pager/pager";

const LIMIT = 100

export class ReportDropdownWithPager extends ReportDropdown {
    setup() {
        super.setup();
        this.pager = useState({
            total: 0,
            offset: 0,
            limit: LIMIT,
            account_id: 0,
        })
        onWillStart(this.setProps)
        onWillUpdateProps((newProps) => {
            const data = newProps.accountDataPage[newProps.account]
            Object.assign(this.pager, data)
        })
    }

    setProps() {
        const data = this.props.accountDataPage[this.props.account]
        Object.assign(this.pager, data)
    }

    async onPagerChanged({offset, limit}, hasNavigated) {
        if (limit >= this.pager.total) return
        this.pager.offset = offset
        this.pager.limit = limit
        const {account} = this.props
        const data = {
            account,
            accountData: {...this.pager, account}
        }
        await this.props.updateMoveLines(data)
    }
}

ReportDropdownWithPager.components = {...ReportDropdown.components, Pager}
