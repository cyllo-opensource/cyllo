/** @odoo-module **/
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { connectAccountPlatforms } from "./platform_registry";

export class PlatformPickerDialog extends Component {
    get platforms() {
        return connectAccountPlatforms.getEntries().map(([platform, entry]) => ({ platform, ...entry }));
    }

    selectPlatform(platform) {
        this.props.onSelectPlatform(platform);
        this.props.close();
    }
}
PlatformPickerDialog.template = "cyllo_social_media_marketing.PlatformPickerDialog";
PlatformPickerDialog.components = { Dialog };
PlatformPickerDialog.props = {
    close: { type: Function, optional: true },
    onSelectPlatform: { type: Function },
};
