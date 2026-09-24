/* @odoo-module */
import {KanbanRecord, CANCEL_GLOBAL_CLICK} from "@web/views/kanban/kanban_record";
import {useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {registry} from '@web/core/registry';
import {Authentication} from "./authentication"
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";

export class DocRecord extends KanbanRecord {
    static template = "DocRecord"
    static props = [
        ...KanbanRecord.props,
        'selection?',
    ]
    static defaultProps = {
        ...KanbanRecord.defaultProps,
    }
    setup() {
        super.setup()
        this.env.bus.addEventListener("UNSELECT_ALL_RECORD", () => {
            this.state.selected = false;
        })
        this.store = useService("mail.store");
        this.state = useState({
            selected: false
        })
        this.orm = useService('orm')
        this.fileViewer = useFileViewer();
        this.recordData = this.props.record.data;
    }

    async onGlobalClick(ev) {
        const {record, selection} = this.props;
        const clickedLink = ev.target.closest('a');
        if (clickedLink && (selection || record.data.is_locked)) {
            ev.preventDefault();
            ev.stopPropagation();
        } else if (!selection) {
            if (ev.target.closest(CANCEL_GLOBAL_CLICK)) {
                return;
            }
        } else {
            ev.stopPropagation();
        }
        if (selection) {
            if (record.data.is_locked) {
                return this.showWarnMessage("Can't Select the Locked Document", "danger")
            }
            this.state.selected = !this.state.selected;
            record.toggleSelection();
        } else {
            const {offset, limit} = this.env.config.pagerProps
            if (record.data.is_locked) {
                this.dialog.add(Authentication, {
                    title: "Password",
                    resId: record.resId,
                    resModel: record.resModel,
                    method: "validate_password",
                    data: record.data,
                    confirm: () => {
                        if (record.data.extension === "url") {
                            window.open(record.data.brochure_url, "_blank");
                        } else if(record.data.extension === "xlsx") {
                            this.previewXlsx(record)
                        } else if (record.data.extension === "zip") {
                            this.showWarnMessage("Preview is not available for this file format.", "warning");
                        } else{
                            this.previewFiles()
                        }
                    }
                })
            } else {
                if (record.data.extension === "xlsx") {
                    await this.previewXlsx(record)
                } else if (record.data.extension === "zip") {
                    this.showWarnMessage("Preview is not available for this file format.", "warning");
                } else {
                    this.previewFiles()
                }

            }
        }
    }

    async previewXlsx() {
        this.showWarnMessage("Install Spreadsheet App to view the XLSX file", "info")
    }

    previewFiles() {
         const preview = this.store.Attachment.insert({
            id: this.recordData.attachment_id[0],
            filename: this.recordData.name,
            name: this.recordData.name,
            mimetype: this.recordData.mimetype
        });
        this.fileViewer.open(preview)
    }
    get isLocked() {
        return this.props.record.data.is_locked
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