/** @odoo-module **/
import {useRef, useState, useEffect} from "@odoo/owl";
import {KanbanController} from "@web/views/kanban/kanban_controller";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";

export class DocController extends KanbanController {
    static template = "docControllerView"
    static components = {...KanbanController.components, Dropdown, DropdownItem}

    setup() {
        super.setup()
        this.fileInput = useRef("fileInput")
        this.docState = useState({
            selection: false,
        })
        this.orm = useService('orm');
        this.user = useService("user");

        useEffect((nb) => {
            this.searchBarToggler.state.showSearchBar = !Boolean(nb);
        }, () => [this.nbSelected])

        useEffect(() => {
            this.docState.selection = false
        }, () => [this.workSpaceId])
    }

    handleOnChangeUpload(ev) {
        const selectedFile = ev.target.files[0];
        const reader = new FileReader();
        try {
            reader.onload = (event) => {
                const arrayBuffer = event.target.result;
                const byteArray = new Uint8Array(arrayBuffer);

                // Function to convert ArrayBuffer to Base64 string in chunks
                function arrayBufferToBase64(buffer) {
                    let binary = '';
                    const bytes = new Uint8Array(buffer);
                    const len = bytes.byteLength;
                    const chunkSize = 8192; // Set a chunk size

                    for (let i = 0; i < len; i += chunkSize) {
                        binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
                    }

                    return btoa(binary);
                }

                const base64String = arrayBufferToBase64(byteArray.buffer);
                const fileName = selectedFile.name;

                if (fileName.endsWith('.pdf')) {
                    pdfjsLib.getDocument({data: byteArray}).promise.then((pdf) => {
                        pdf.getPage(1).then((page) => {
                            const viewport = page.getViewport({scale: 1.0});
                            const canvas = document.createElement('canvas');
                            const context = canvas.getContext('2d');
                            canvas.height = viewport.height;
                            canvas.width = viewport.width;
                            const renderContext = {
                                canvasContext: context,
                                viewport: viewport
                            };

                            const renderTask = page.render(renderContext);
                            renderTask.promise.then(() => {
                                const croppedCanvas = document.createElement('canvas');
                                const croppedContext = croppedCanvas.getContext('2d');
                                const croppedWidth = viewport.width;
                                const croppedHeight = viewport.height / 2;
                                croppedCanvas.width = croppedWidth;
                                croppedCanvas.height = croppedHeight;

                                croppedContext.drawImage(canvas, 0, 0, croppedWidth, croppedHeight, 0, 0, croppedWidth, croppedHeight);

                                const thumbnailData = croppedCanvas.toDataURL('image/png');
                                const thumbnailName = selectedFile.name + '_thumbnail.png';
                                this.orm.call('document.file', 'action_upload_document', [{
                                    'file': base64String,
                                    'file_name': fileName,
                                    'workspace_id': this.workSpaceId,
                                    'preview_image': thumbnailData.split(',')[1]
                                }]).then((result) => {
                                    this.env.searchModel._notify()
                                }).catch((error) => {
                                    console.error('Error uploading thumbnail:', thumbnailName, error);
                                });
                            });
                        });
                    }).catch((error) => {
                        console.error('Error loading PDF:', error);
                    });
                } else {
                    if (fileName.endsWith(".xlsx") && !this.isSpreadSheetInstalled) {
                        return this.showWarning("You have to install Spreadsheet module to be able to upload xlsx files", "warning");
                    }
                    this.orm.call('document.file', 'action_upload_document', [{
                        'file': base64String,
                        'file_name': fileName,
                        'workspace_id': this.workSpaceId,
                        'preview_image': false
                    }]).then((result) => {
                        this.env.searchModel._notify()
                    }).catch((error) => {
                        console.error('Error uploading file:', error);
                    });
                }
            };

            reader.onerror = (error) => {
                console.error('Error reading file:', error);
            };

            reader.readAsArrayBuffer(selectedFile);
        } catch {
            this.showWarning(`Please upload a valid document`, "danger")
        } finally {
            ev.target.value = "";
        }
    }

    get isSpreadSheetInstalled() {
        return false // avoids unnecessary api request
    }

    get workSpaceId() {
        for (let [key, section] of this.env.searchModel.sections) {
            if (section.fieldName === "workspace_id") {
                return section.activeValueId;
            }
        }
        return false;
    }


    handleUpload() {
        this.fileInput.el.click()
    }

    handleCreateRequest() {
        return this.actionService.doActionButton({
            resModel: 'request.document',
            name: 'open_wizard_view',
            type: "object"
        })
    }

    handleAddUrl() {
        this.actionService.doAction({
            'type': 'ir.actions.act_window',
            'name': _t('Add Url'),
            'res_model': 'document.url',
            'view_mode': 'form',
            'target': 'new',
            'views': [[false, "form"]],
        });
    }

    handleToggleSelection() {
        this.docState.selection = !this.docState.selection;
        if (!this.docState.selection) {
            this.onUnselectAll()
        }
    }

    get isDomainSelected() {
        return this.model.root.isDomainSelected;
    }

    get nbTotal() {
        const list = this.model.root;
        return list.isGrouped ? list.recordCount : list.count;
    }

    get nbSelected() {
        return this.model.root.selection.length;
    }

    get selectedIds() {
        return this.model.root.selection.map(selection => selection.resId);
    }

    onUnselectAll() {
        this.env.bus.trigger("UNSELECT_ALL_RECORD")
        this.model.root.selection.forEach((record) => {
            record.toggleSelection(false);
        });
        this.model.root.selectDomain(false);
        this.docState.selection = false;
    }

    handleShareDoc() {
        return this.actionService.doActionButton({
            resModel: 'document.share',
            name: 'share_url',
            args: `[${JSON.stringify(this.selectedIds)}]`,
            type: "object"
        })
    }

    async handleBackendAction(model, functionName, args = [], kwargs = {}) {
        const response = await this.orm.call(model, functionName, args, kwargs)
        return this.actionService.doAction(response);
    }

    async handleDownloadZip() {
        await this.handleBackendAction('document.file', 'download_zip_function', [this.selectedIds])
    }

    async handleMailDocument() {
        await this.handleBackendAction('document.file', 'on_mail_document', [this.selectedIds])
    }

    async handleCopyDocument() {
        const hasAccess = await this.user.hasGroup('cyllo_documents.group_cyllo_documents_manager')
        if (hasAccess) {
            this.actionService.doAction({
                'type': 'ir.actions.act_window',
                'name': 'copy',
                'res_model': 'work.space',
                'view_mode': 'form',
                'target': 'new',
                'views': [
                    [false, 'form']
                ],
                'context': {
                    'default_doc_ids': this.selectedIds
                }
            });
        } else this.showWarning("You don't have permission to perform this action", "danger")
    }

    showWarning(message, type, sticky = false) {
        this.actionService.doAction({
            type: 'ir.actions.client',
            tag: 'display_notification',
            params: {
                message,
                type,
                sticky,
            }
        })
    }

    notify() {
        this.env.searchModel._notify()
        this.docState.selection = false
    }

    async handleArchiveDocument() {
        await this.orm.call('document.file', 'document_file_archive', [this.selectedIds])
        this.docState.selection = false
        this.notify()
    }

    async handleDocDelete() {
        const hasAccess = await this.user.hasGroup('cyllo_documents.group_cyllo_documents_manager')
        if (hasAccess) {
            await this.orm.call('document.file', 'document_file_delete', [this.selectedIds])
            this.notify()
        } else this.showWarning("You don't have permission to perform this action", "danger")
    }

    async handleAction(model, method, warningMessage, type = "info") {
        const response = await this.orm.call(model, method, [this.selectedIds]);
        if (response) {
            this.notify();
        } else {
            this.showWarning(warningMessage, type);
        }
    }

    async handleCreateTask() {
        await this.handleAction('document.file', 'action_btn_create_task', "Install Project Module to use this function");
    }

    async handleCreateLead() {
        await this.handleAction('document.file', 'action_btn_create_lead', "Install CRM Module to use this function");
    }
}
