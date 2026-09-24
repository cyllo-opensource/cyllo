/** @odoo-module */
import * as spreadsheet from "@odoo/o-spreadsheet";
import {_t} from "@web/core/l10n/translation";
import {NameComponent} from "./NameComponent/NameComponent";
import {BackButtonComponent} from "./BackButtonComponent/BackButtonComponent";

const {topbarMenuRegistry, topbarComponentRegistry} = spreadsheet.registries;

topbarMenuRegistry.addChild("Save", ["file"], {
    name: _t("Save"),
    execute: (env) => env.saveSheet(),
    icon: "cyllo_spreadsheet.Save",
    sequence: 1,
});
topbarMenuRegistry.addChild("Download", ["file"], {
    name: _t("Download"),
    execute: (env) => env.download(),
    icon: "cyllo_spreadsheet.Download",
    sequence: 2,
});
export const addShareToMenu = () => {
    const Share = topbarMenuRegistry.content.file.children.find(item => item.name === "Share")
    if (!Share)
        topbarMenuRegistry.addChild("Share", ["file"], {
            name: _t("Share"),
            execute: (env) => env.share(),
            icon: "cyllo_spreadsheet.Share",
            sequence: 3,
        });
}

topbarComponentRegistry.add("name_component", {
    component: NameComponent,
    isVisible: (env) => true,
});
topbarComponentRegistry.add("back_component", {
    component: BackButtonComponent,
    isVisible: (env) => true,
});