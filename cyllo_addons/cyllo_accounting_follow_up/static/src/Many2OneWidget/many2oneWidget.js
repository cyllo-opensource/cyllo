/* @odoo-module */
import { registry } from '@web/core/registry';
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


export class Many2OneButton extends Component {
    static template = "Many2OneButtonTemplate"

    setup(){
        this.orm = useService("orm");
    }
    async onClickFollowupAction(){
        if (this.canClick){
            const followup_id = this.props.record.data[this.props.name][0];
            await this.orm.call(this.props.record.resModel, 'many2one_action', [this.props.record.resId])
            this.env.searchModel._notify();
        }
    }

    get canClick() {
        return this.props.mode !== "readonly" && this.props.clickable
    }
}

export const many2oneField = {
    component: Many2OneButton,
    supportedTypes: ["many2one"],
    extractProps: (fieldInfo, dynamicInfo) => ({
        clickable: fieldInfo.options?.clickable !== undefined ? fieldInfo.options.clickable : true,
    }),
};

registry.category("fields").add("many2one_button", many2oneField);
