/** @odoo-module **/
import { registry } from "@web/core/registry";
import {
    many2ManyBinaryField,
    Many2ManyBinaryField,
} from "@web/views/fields/many2many_binary/many2many_binary_field";


export class MediaUploadField extends Many2ManyBinaryField {
    get uploadText() {
        return "Add Media";
    }
}

registry.category("fields").add("media_upload_field", {
    ...many2ManyBinaryField,
    component: MediaUploadField,
});
