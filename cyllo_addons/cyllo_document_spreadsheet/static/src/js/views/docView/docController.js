/** @odoo-module */

import {DocController} from "@cyllo_documents/view/doc_view/docController";
import {patch} from "@web/core/utils/patch";

patch(DocController.prototype, {
    async handleAddSpreadSheet() {
        await this.actionService.doAction("cyllo_document_spreadsheet.action_view_create_spreadsheet")
    },
    get isSpreadSheetInstalled() {
        return true // avoids unnecessary api request
    }
})