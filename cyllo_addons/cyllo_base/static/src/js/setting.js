/** @odoo-module **/
import { Setting } from "@web/views/form/setting/setting";
import { patch } from "@web/core/utils/patch";
const { onMounted } = owl;

patch(Setting.prototype, {
    setup() {
        super.setup();
        onMounted(() => {
            this.removeEnterprise()
        })
    },

    removeEnterprise() {
        Array.from(this.__owl__.bdom.parentEl.querySelectorAll('.o_setting_box .o_enterprise_label'))
            .forEach(label => label.closest('.o_setting_box').style.display = 'none');
    }
});