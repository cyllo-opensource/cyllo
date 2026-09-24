/** @odoo-module */
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { KanbanSignRecord } from "./kanban_record";
import { KanbanSignRenderer } from "./kanban_renderer";

patch(KanbanController.prototype, {
    setup() {
        super.setup()
        this.orm = useService("orm");
        this.action = useService("action");
    },
    onSignDocumentUpload() {
        const uploadedFile = $(this.__owl__.bdom.el).find(".fileInput").prop('files')[0];
        const self = this;
        const reader = new FileReader();
        reader.onload = function(event) {
            const fileName = uploadedFile.name;
            if (!fileName.endsWith('.pdf')) {
                return;
            }
            const binaryString = event.target.result;
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            pdfjsLib.getDocument({ data: bytes }).promise.then(function(pdf) {
                return pdf.getPage(1);
            }).then(function(page) {
                const viewport = page.getViewport({ scale: 1.0 });
                const canvas = document.createElement('canvas');
                const context = canvas.getContext('2d');
                canvas.height = viewport.height;
                canvas.width = viewport.width;
                const renderContext = {
                    canvasContext: context,
                    viewport: viewport
                };
                return page.render(renderContext).promise.then(function() {
                    const croppedCanvas = document.createElement('canvas');
                    const croppedContext = croppedCanvas.getContext('2d');
                    const croppedWidth = viewport.width;
                    const croppedHeight = viewport.height / 2;
                    croppedCanvas.width = croppedWidth;
                    croppedCanvas.height = croppedHeight;
                    croppedContext.drawImage(canvas, 0, 0, croppedWidth, croppedHeight, 0, 0, croppedWidth, croppedHeight);
                    const thumbnailData = croppedCanvas.toDataURL('image/png');
                    const thumbnailName = uploadedFile.name + '_thumbnail.png';
                    return self.orm.call('sign.template', 'create', [{
                        'name': uploadedFile.name,
                        'data': btoa(binaryString),
                        'image_1920': thumbnailData.split(',')[1]
                    }]);
                });
            }).then(function(template) {
                self.action.doAction({
                    'type': 'ir.actions.client',
                    'name': uploadedFile.name,
                    'tag': 'sign_configure',
                    'params': {
                        "res_model": 'sign.template',
                        "res_id": template,
                    }
                });
            }).catch(function(error) {
                console.error('Error processing PDF:', error);
            });
        };
        reader.onerror = function(error) {
            console.error('Error reading file:', error);
        };
        reader.readAsBinaryString(uploadedFile);
    }
})
registry.category('views').add('cyllo_sign_upload', {
    ...kanbanView,
    Controller: KanbanController,
    KanbanRecord: KanbanSignRecord,
    Renderer: KanbanSignRenderer,
});
