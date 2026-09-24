/* @odoo-module */
import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";


export class PartnerSelection extends Component {
    static components = {Dialog, MultiRecordSelector}
    static template = 'PartnerSelection'
    setup() {
        this.state = useState({
            selectedPartners: this.props.selectedPartners || []
        })
    }
    addPartner(partnerIds){
        this.state.selectedPartners = partnerIds;
        this.props.addPartner(partnerIds);
    }
}
