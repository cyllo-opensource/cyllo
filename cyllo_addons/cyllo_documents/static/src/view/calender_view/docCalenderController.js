/** @odoo-module */

import {CalendarController} from "@web/views/calendar/calendar_controller";
import {Authentication} from "../doc_view/authentication";
import {useFileViewer} from "@web/core/file_viewer/file_viewer_hook";
import {useService} from "@web/core/utils/hooks";

export class DocCalenderController extends CalendarController {
    setup() {
        super.setup();
        this.fileViewer = useFileViewer()
        this.dialog = useService('dialog');
        this.store = useService("mail.store");
    }

    async previewXlsx() {
        this.showWarnMessage("Install Spreadsheet App to view the XLSX file", "info")
    }

    async editRecord(record, context = {}, shouldFetchFormViewId = true) {
        const openAttachment = async (record) => {
            if (record.rawRecord.extension === "url") {
                window.open(record.rawRecord.brochure_url, "_blank");
            } else if (record.rawRecord.extension === "xlsx") {
                await this.previewXlsx(record)
            } else {
                const preview = this.store.Attachment.insert({
                    id: record.rawRecord.attachment_id[0],
                    filename: record.rawRecord.display_name,
                    name: record.rawRecord.display_name,
                    mimetype: record.rawRecord.mimetype
                });
                this.fileViewer.open(preview);
            }
        };
        if (record.isLocked) {
            this.addConfirmDialog(record, "Authenticate", openAttachment)
        } else {
            await openAttachment(record);
        }
    }

    addConfirmDialog(record, title, confirm) {
        this.dialog.add(Authentication, {
            title,
            resId: record.id,
            resModel: this.model.resModel,
            method: "validate_password",
            data: record,
            confirm
        });
    }

    deleteRecord(record) {
        const confirm = () => this.model.unlinkRecord(record.id)
        if (record.isLocked) {
            this.addConfirmDialog(record, "Confirm Your Password", confirm);
        } else confirm()
    }

    showWarnMessage(message, type, sticky = false) {
        this.action.doAction({
            type: 'ir.actions.client',
            tag: 'display_notification',
            params: {
                message,
                type,
                sticky,
            }
        })
    }
}
