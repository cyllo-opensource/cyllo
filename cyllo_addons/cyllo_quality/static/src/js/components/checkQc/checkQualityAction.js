/** @odoo-module */
import { registry } from '@web/core/registry';
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ValidateQualityAction } from "@cyllo_quality/js/components/validateQualityAction/validateQualityAction";

export class CheckQualityAction extends Component {
    static components = { ValidateQualityAction }
    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            qualityCheck: false
        })
        onWillStart(async () => {
            await this.getQualityCheck()
        })
    }

    async getQualityCheck() {
        const response = await this.orm.call("quality.check", "get_quality_check_actions", [this.props.record.data.quality_check_id[0]])
        this.state.qualityCheck = response[0]
    }

    async _onClickCheck() {
        if (!this.state.qualityCheck) {
            this.notification.add(_t("Please save the record before performing a quality check."), {
                type: "warning",
            });
            return;
        }

        await this.dialog.add(ValidateQualityAction, {
            title: this.state.qualityCheck?.control_type == 'quantity'
                ? _t(`Quality Check of ${this.state.qualityCheck?.product_id[1]} for ${this.props.record.data.inspection_action_id[1]} - ${this.state.qualityCheck?.quantity} Units`)
                : this.state.qualityCheck?.product_id[1]
                    ? _t(`Quality Check of ${this.state.qualityCheck?.product_id[1]} for ${this.props.record.data.inspection_action_id[1]} `)
                    : _t(`Quality Check for ${this.props.record.data.inspection_action_id[1]}`),
            quality_check: this.state.qualityCheck,
            quality_check_action: this.props.record.data,
            handleModalClose: this.handleModalClose.bind(this)
        })
    }
    async handleModalClose() {
        // todo: Need to check usecase and references
    }
}
CheckQualityAction.template = "CheckQualityAction";
export const checkQualityAction = {
    component: CheckQualityAction,
};
registry.category("view_widgets").add("check_quality_action", checkQualityAction);