/** @odoo-module */
import {
    ListController
} from '@web/views/list/list_controller';
import {
    Authentication
} from "../doc_view/authentication";
import {
    registry
} from '@web/core/registry';
import {
    onWillDestroy
} from "@odoo/owl";
import {
    useService
} from "@web/core/utils/hooks";
import {
    useFileViewer
} from "@web/core/file_viewer/file_viewer_hook";

const cogMenuRegistry = registry.category("cogMenu");
const SELECTION_MESSAGE = "Can't group select the locked items";

export class DocListController extends ListController {
    setup() {
        super.setup();
        this.fileViewer = useFileViewer();
        this.store = useService("mail.store");
        let splitView = null;
        if (cogMenuRegistry.contains('splitview-menu')) {
            splitView = cogMenuRegistry.get('splitview-menu');
            cogMenuRegistry.remove('splitview-menu');
        }
        let spreadSheet = {};
        const hasSpreadSheetView = cogMenuRegistry.contains('spreadsheet-cog-menu');
        if (hasSpreadSheetView) {
            spreadSheet = cogMenuRegistry.get('spreadsheet-cog-menu');
            cogMenuRegistry.remove('spreadsheet-cog-menu');
        }
        onWillDestroy(() => {
            if (splitView) {
                cogMenuRegistry.add('splitview-menu', splitView, {
                    sequence: 11
                });
            }
            if (hasSpreadSheetView) {
                cogMenuRegistry.add('spreadsheet-cog-menu', spreadSheet, {
                    sequence: 1
                });
            }
        });
    }

    async onDeleteSelectedRecords() {
        const {
            selection
        } = this.model.root
        if (selection.length > 1 && selection.some(item => item.data.is_locked)) {
            this.showWarnMessage()
        } else if (selection.length === 1 && selection.some(item => item.data.is_locked)) {
            const confirm = (attachment) => super.onDeleteSelectedRecords();
            this.addConfirmDialog(selection[0], "Password", confirm)
        } else {
            super.onDeleteSelectedRecords();
        }
    }

    showWarnMessage(message = SELECTION_MESSAGE, type = "danger") {
        this.actionService.doAction({
            type: 'ir.actions.client',
            tag: 'display_notification',
            params: {
                message,
                type,
                sticky: false,
            }
        })
    }

    getStaticActionMenuItems() {
        const result = super.getStaticActionMenuItems();
        delete result["export"]
        return result;
    }

    async openRecord(record) {
        const openAttachment = async (attachment) => {
            if (attachment.data.extension === "url") {
                window.open(attachment.data.brochure_url, "_blank");
            } else if (attachment.data.extension === "xlsx") {
                await this.previewXlsx(attachment)
            } else {
                const preview = this.store.Attachment.insert({
                    id: record.data.attachment_id[0],
                    filename: record.data.name,
                    name: record.data.name,
                    mimetype: record.data.mimetype
                });
                this.fileViewer.open(preview)
            }
        };

        if (record.data.is_locked) {
            this.addConfirmDialog(record, "Authenticate", openAttachment)
        } else {
            await openAttachment(record)
        }
    }

    addConfirmDialog(record, title, confirm) {
        this.dialogService.add(Authentication, {
            title,
            resId: record.resId,
            resModel: this.model.root.resModel,
            method: "validate_password",
            data: record,
            confirm,
        });
    }

    async previewXlsx(attachment) {
        this.showWarnMessage("Install Spreadsheet App to view the XLSX file", "info")
    }
}