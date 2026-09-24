/** @odoo-module */

import { ModelFieldSelectorPopover } from "@web/core/model_field_selector/model_field_selector_popover";
import { onWillDestroy } from "@odoo/owl";

export class StudioFieldSelectorPopover extends ModelFieldSelectorPopover{

    static props = {
        ...ModelFieldSelectorPopover.props,
        complete: { type: Function, optional: true },
    };
    setup(){
        super.setup();
        onWillDestroy(() => {
            this.props.complete();
        });
    }

    selectField(field) {
        const result = super.selectField(field);
        if (result) {
            return result;
        }
        this.props.complete(this.state.page.path);
    }

}