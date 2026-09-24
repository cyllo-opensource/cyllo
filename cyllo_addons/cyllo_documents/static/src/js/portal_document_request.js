/* @odoo-module */
import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.documentUploadButton = publicWidget.Widget.extend({
    selector: 'div[id="document_upload_button"]',
    events: {
        'click #web_docs_upload': '_onUploadButtonClick',
    },
    _onUploadButtonClick: function () {
        /* Method to handle upload button click*/
        var self = this;
        $('#docs_upload_form').modal('show');
        jsonrpc(`/web/dataset/call_kw/document.workspace/work_spaces`, {
         model: "document.workspace",
         method: "work_spaces",
         args: [],
         kwargs: {},
         }).then(function (result) {
            $('#workspace').empty();
            result.forEach(element => {
                $('#workspace').append(`
                    <option value="${element['id']}">${element['name']}</option>`
                )
            })
        })
    }
})