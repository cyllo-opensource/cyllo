/* @odoo-module */
import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.DocumentPortal = publicWidget.Widget.extend({
    selector: 'div[id="document_portal"]',
    events: {
        'click .fa-share': '_onShare',
        'click .re-upload': '_onRequestAccept',
        'click .re-reject': '_onRequestReject',
        'click .doc-upload': '_onUploadDocument',
    },
    _onShare: function (ev) {
        /**
            * method to copy sharable link
        */
        var record_url = ev.target.dataset.url
        var $temp = $("<input>");
        $("body").append($temp);
        $temp.val(record_url).select();
        document.execCommand("copy");
        $temp.remove();
        this.$el.find('.toast').addClass('show');
        this.$el.find('.toast-body').text(record_url)
    },
    _onRequestAccept: function (ev) {
        /**
        * function to open file upload modal
        */
        this.$el.find('#req_upload_form').modal('show');
        this.$el.find('#workspace').val(ev.target.dataset.workspace)
        this.$el.find('#requested_by_id').val(ev.target.dataset.requested_by_id)
        this.$el.find('#workspace_id').val(ev.target.dataset.workspace_id)
        this.$el.find('#rec_id').val(ev.target.dataset.id)
    },
    /**Handles the request rejection event.
     * @param {Event} ev - The event object.*/
    _onRequestReject: function (ev) {
        // Set the request ID in the corresponding input field
        this.$el.find('#req_id').val(ev.target.dataset.id);
        // Show the request rejection form modal
        this.$el.find('#req_reject_form').modal('show');
    },
    /**
     * Handles the upload of a document.
     *
     * This function is triggered when the user uploads a document. It extracts the file
     * content, converts it to base64 format, and uploads it along with other metadata
     * such as the file name and workspace ID. If the uploaded file is a PDF,
     * it also generates a thumbnail of the first page and uploads it.
     *
     * @param {Event} ev - The event object representing the click event.
     */
    _onUploadDocument: function (ev) {
        var fileInput = this.$el.find('input[name="file"]')?.[0];
        var workspaceId = this.$el.find('#workspace').val();
        if (fileInput.files.length > 0) {
            var file = fileInput.files[0];
            var file_name = file.name;
            var reader = new FileReader();

            reader.onload = (event) => {
                var fileContent = event.target.result;
                var base64String = btoa(fileContent);
                if (file_name.endsWith('.pdf')){
                    pdfjsLib.getDocument({
                        data: fileContent
                    }).promise.then((pdf) => {
                        pdf.getPage(1).then((page) => {
                            var viewport = page.getViewport({ scale: 1.0 });
                            var canvas = document.createElement('canvas');
                            var context = canvas.getContext('2d');
                            canvas.height = viewport.height;
                            canvas.width = viewport.width;

                            var scale = 2;
                            var topMargin = viewport.height / 4;

                            var renderContext = {
                                canvasContext: context,
                                viewport: viewport
                            };

                            var renderTask = page.render(renderContext);
                            renderTask.promise.then(() => {
                                var croppedCanvas = document.createElement('canvas');
                                var croppedContext = croppedCanvas.getContext('2d');
                                var croppedWidth = viewport.width;
                                var croppedHeight = viewport.height / 2;
                                croppedCanvas.width = croppedWidth;
                                croppedCanvas.height = croppedHeight;

                                croppedContext.drawImage(canvas, 0, 0, croppedWidth, croppedHeight,
                                    0, 0, croppedWidth, croppedHeight);

                                var thumbnailData = croppedCanvas.toDataURL('image/png');
                                jsonrpc('/website/documents', {
                                    'thumbnail': thumbnailData.split(',')[1],
                                    'file': base64String,
                                    'file_name': file_name,
                                    'workspace_id': workspaceId,
                                }).then(() => {
                                    location.reload();
                                }).catch((error) => {
                                    console.error('Error uploading thumbnail:', thumbnailName, error);
                                });
                            });
                        });
                    }).catch((error) => {
                        console.error('Error loading PDF:', error);
                    });
                }
                else {
                    jsonrpc('/website/documents', {
                        'thumbnail': false,
                        'file': base64String,
                        'file_name': file_name,
                        'workspace_id': workspaceId,
                    }).then((result) => {
                        location.reload();
                    });
                }
            };
            reader.readAsBinaryString(file);
        } else {
            console.error('No file selected');
        }
    }
})