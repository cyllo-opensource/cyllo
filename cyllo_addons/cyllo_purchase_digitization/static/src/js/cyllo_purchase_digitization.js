/** @odoo-module */
/* Import necessary modules and components */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useRef } from "@odoo/owl";
import { useBus, useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";


export class PurchaseListController extends ListController {
    setup() {
        super.setup();
        this.uploadFileInputRef = useRef("uploadFileInput");
        this.fileUploadService = useService("file_upload");
        this.action = useService("action");
    }
    async onFileInputChange(ev) {
        if (!ev.target.files.length) {
            return;
        }
        const response = await this.fileUploadService.upload(
            "/cyllo_purchase_digitization/upload_attachment",
            ev.target.files,
            {
                buildFormData: (formData) => {
                    formData.append("res_model", this.props.context.default_res_model);
                    formData.append("res_id", this.props.context.default_res_id);
                },
            },
        );
        const xhr = response.xhr
        xhr.onload = () => {
          if (xhr.readyState === xhr.DONE) {
            if (xhr.status === 200) {
              const purchase_order_id = parseInt(xhr.response);
              this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("Purchase Order"),
                res_model: "purchase.order",
                res_id: purchase_order_id,
                views: [[false, "form"]],
                view_mode: "form",
                target: "current",
            },
        );
            }
          }
        };
        // Reset the file input's value so that the same file may be uploaded twice.
        ev.target.value = "";
    }
}

registry.category("views").add("button_in_tree", {
   ...listView,
   Controller: PurchaseListController,
   buttonTemplate: "cyllo_purchase_digitization.ListView.Buttons",
});
