/** @odoo-module */

import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { CustomCreateModelFieldSelectorPopover } from "./custom_model_field_selector_popover";
import { usePopover } from "@web/core/popover/popover_hook";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";

export class CustomCreateModelFieldSelector extends ModelFieldSelector{
    setup(){
        super.setup()
        const loadFieldInfo = useLoadFieldInfo();
        this.popover = usePopover(CustomCreateModelFieldSelectorPopover, {
            popoverClass: "o_popover_field_selector",
            onClose: async () => {
                if (this.newPath !== null) {
                    const fieldInfo = await loadFieldInfo(this.props.resModel, this.newPath);
                    this.props.update(this.newPath, fieldInfo);
                }
            },
        });
    }
}