/** @odoo-module **/

import { onWillRender } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ButtonBox } from "@web/views/form/button_box/button_box";

patch(ButtonBox.prototype, {
    setup() {
        const ui = useService("ui");
        onWillRender(() => {
            const allVisibleButtons = Object.entries(this.props.slots)
                .filter(([_, slot]) => this.isSlotVisible(slot))
                .map(([slotName]) => slotName);
            let maxVisibleButtons;
            if (this.props.slots.slot_0.__ctx.__comp__.this.splitView) {
                maxVisibleButtons = 1;
            } else {
                maxVisibleButtons = [3, 4, 5, 7, 4, 5, 8][ui.size] || 8;
            }
            if (allVisibleButtons.length <= maxVisibleButtons) {
                this.visibleButtons = allVisibleButtons;
                this.additionalButtons = [];
                this.isFull = allVisibleButtons.length === maxVisibleButtons;
            } else {
                this.visibleButtons = allVisibleButtons.slice(0, maxVisibleButtons - 1);
                this.additionalButtons = allVisibleButtons.slice(maxVisibleButtons - 1);
                this.isFull = true;
            }
        });
    },

    isSlotVisible(slot) {
        return !("isVisible" in slot) || slot.isVisible;
    },
});