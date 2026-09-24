/** @odoo-module */

import {DocRecord} from "@cyllo_documents/view/doc_view/docRecord";
import {patch} from "@web/core/utils/patch";

patch(DocRecord.prototype, {
    async previewXlsx(attachment) {
        const response = await this.orm.search('spreadsheet.sheet', [["document_file_id", "=", attachment.resId]])
        if (response.length) {
            this.action.doAction({
                type: "ir.actions.client",
                tag: "main_spreadsheet",
                context: {
                    resId: response[0]
                }
            })
        }
        else {
            this.showWarnMessage("Access Denied: You do not have permission to access this spreadsheet. Please contact the administrator to request access or to share the record from the spreadsheet application.", "danger")
        }

    }
})