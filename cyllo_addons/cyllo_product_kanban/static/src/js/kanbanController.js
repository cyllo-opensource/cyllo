/** @odoo-module */
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { patch } from "@web/core/utils/patch";
const { onMounted } = owl;
patch(KanbanController.prototype, {
    setup() {
        super.setup();
        onMounted(() => {
            this.addProductClass()
        });
    },
    addProductClass() {
        if (this.model.env.searchModel.resModel == 'product.template') {
            this.__owl__.bdom.el.querySelectorAll('.o_kanban_record').forEach(function(element) {
                element.classList.add('cy_o_kanban_record');
            });
        }
    }
})