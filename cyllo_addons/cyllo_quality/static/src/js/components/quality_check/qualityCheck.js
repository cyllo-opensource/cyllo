/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, useExternalListener, useRef, useEffect, status } from "@odoo/owl";
import { QualityAction } from "@cyllo_quality/js/components/qualityAction/qualityAction";

export class QualityCheck extends Component {
    static components = { QualityAction }
    setup() {
        useExternalListener(document, "click", this.handleExternalClick);
        this.env.bus.addEventListener("GET_QUALITY_ACTIONS", () => {
            this.state.isActive = true
            this.getActions()
        })
        useEffect(() => {
            this.state.isActive = false
            this.getActions()
        }, () => [this.props.resId])

        this.orm = useService("orm");
        this.state = useState({
            qualityActions: false,
            modalOpen: false,
            isActive: false,
        })
        this.root = useRef('root')

        onWillStart(async () => {
            await this.getActions()
        })
    }
    handleExternalClick(ev) {
        if (!this.root.el.contains(ev.target) && !this.state.modalOpen) {
            this.state.isActive = false
        }
    }

    handleModalToggle(value) {
        this.state.modalOpen = value
    }

    handleToggler() {
        this.state.isActive = !this.state.isActive
    }

    async getActions() {
        if (status(this) !== 'destroyed') {
            this.state.qualityActions = await this.orm.call("quality.check", "get_quality_check_actions", [this.props.qualityCheckIds])
        }
    }
}

QualityCheck.template = "QualityCheck";
