/** @odoo-module **/
import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
const {onMounted } = owl;
patch(FormController.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                this.addClassStyle()
            })
        },
        addClassStyle(){
            if (this.__owl__.bdom.parentEl.parentElement.querySelector('.change-pwd-btn')){
                this.__owl__.bdom.parentEl.parentElement.querySelector('.change-pwd-btn').parentElement.parentElement.parentElement.classList.add("change-pwd-btn-modal")
            }
            if (this.__owl__.bdom.parentEl.parentElement.querySelector('.confirm-pwd')){
                this.__owl__.bdom.parentEl.parentElement.querySelector('.confirm-pwd').parentElement.parentElement.parentElement.classList.add("confirm-pwd-modal")
            }
        }
    }
);

FormController.components = {
    ...FormController.components,
};
