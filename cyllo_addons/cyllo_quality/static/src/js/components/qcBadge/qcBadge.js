/** @odoo-module */
import { registry } from '@web/core/registry';
import { BadgeField, badgeField } from '@web/views/fields/badge/badge_field';
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { useBus } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

export class QcBadgeField extends BadgeField{
    static  template = "QcBadgeField"
    setup(){
        super.setup();
        this.state = useState({
            tempContext: {},
            value: "",
            isBus: false,
        })
        useBus(this.env.bus, "UPDATE_BADGE_STATUS", this.updateBadge)
    }

    updateBadge({detail}) {
        const {record} = this.props
        if(record.resId === detail.resId && record.resModel === detail.resModel){
            this.state.isBus = true;
            this.state.value = detail.value
            this.state.tempContext = {
                [this.props.name]: detail.key
            }
        }
    }

    get classFromDecorationBus() {
        const evalContext = this.state.tempContext;
        for (const decorationName in this.props.decorations) {
            if (evaluateBooleanExpr(this.props.decorations[decorationName], evalContext)) {
                return `text-bg-${decorationName}`;
            }
        }
        return "";
    }

}
export const qualityCheckBadge = {
    ...badgeField,
    component: QcBadgeField,
};

registry.category("fields").add("qc_badge", qualityCheckBadge);