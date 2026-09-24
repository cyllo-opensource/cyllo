/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, markup, useState, onWillStart } from "@odoo/owl";
import { ValidateQualityAction } from "@cyllo_quality/js/components/validateQualityAction/validateQualityAction";

export class QualityAction extends Component {
    static components = { ValidateQualityAction }
    setup() {
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            addNote: false,
            isPass: undefined,
        });

        onWillStart(() => {
            this.updateState(this.props);
        });
    }

    onWillUpdateProps(nextProps) {
        this.updateState(nextProps);
    }

    updateState(props) {
        const { status } = props.action;
        if (["fail", "pass"].includes(status)) {
            this.state.isPass = status === "pass";
        } else {
            this.state.isPass = undefined;
        }
    }

    async onClickQualityAction() {

        if (this.state.isPass !== undefined) {
            return;
        }

        const { blocked_by_id } = this.props.action;
        if (blocked_by_id) {
            const blockingAction = this.props.quality_check.quality_check_line_ids.find(l => l.quality_inspection_id[0] === blocked_by_id[0]);
            console.log('Blocking Action State:', blockingAction ? { name: blockingAction.inspection_action_id[1], checked: blockingAction.is_checked } : 'Not Found');
            if (blockingAction && !blockingAction.is_checked) {
                this.notification.add(_t(`This action is blocked by ${blockingAction.inspection_action_id[1]}. Please complete it first.`), {
                    type: "warning",
                });
                return;
            }
        }

        this.props.handleModalToggle(true)
        if (this.state.isPass === undefined) {

            await this.dialog.add(ValidateQualityAction, {
                title: this.props.quality_check.control_type == 'quantity'
                    ? _t(`Quality Check of ${this.props.quality_check.product_id[1]} for ${this.props.action.inspection_action_id[1]} - ${this.props.quality_check.quantity} Units`)
                    : this.props.quality_check.product_id
                        ? _t(`Quality Check of ${this.props.quality_check.product_id[1]} for ${this.props.action.inspection_action_id[1]} `)
                        : _t(`Quality Check for ${this.props.action.inspection_action_id[1]}`),
                quality_check: this.props.quality_check,
                quality_check_action: this.props.action,
                handleModalClose: this.handleModalClose.bind(this),
            })
        }
    }

    handleModalClose(response) {
        this.props.handleModalToggle(false)
        const status = response?.status;
        if (["fail", "pass"].includes(status)) {
            this.state.isPass = status === "pass";
        } else {
            this.state.isPass = undefined;
        }
    }

}
QualityAction.template = "QualityAction";
