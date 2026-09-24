/** @odoo-module  */
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ButtonBox } from "@web/views/form/button_box/button_box";
const { onWillRender } = owl;

patch(ButtonBox.prototype, {
    setup() {
        super.setup();
        const ui = useService("ui");
        onWillRender(() => {
            let maxVisibleButtons = [3, 3, 3, 7, 3, 4, 7][ui.size] || 7;
            if (this.props.slots.slot_0.__ctx.__comp__.this.splitView) {
                maxVisibleButtons = 2
            }
            const allVisibleButtons = Object.entries(this.props.slots)
                .filter(([_, slot]) => slot.isVisible)
                .map(([slotName]) => slotName);
            if (allVisibleButtons.length <= maxVisibleButtons) {
                this.visibleButtons = allVisibleButtons;
                this.additionalButtons = [];
                this.isFull = allVisibleButtons.length === maxVisibleButtons;
            } else {
                // -1 for "More" dropdown
                this.visibleButtons = allVisibleButtons.slice(0, maxVisibleButtons - 1);
                this.additionalButtons = allVisibleButtons.slice(maxVisibleButtons - 1);
                this.isFull = true;
            }
        });
    },
})