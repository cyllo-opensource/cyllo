/** @odoo-module */
import {ListController} from "@web/views/list/list_controller";
import {useSpreadsheet} from "../../hooks/useSpreadsheet";
import {_t} from "@web/core/l10n/translation";
import {UserShare} from "../userShare/userShare";

export class SheetListController extends ListController {
    static template = "SheetListController";

    setup() {
        super.setup();
        this.spreadsheet = useSpreadsheet()
    }

    getStaticActionMenuItems() {
        return {
            ...super.getStaticActionMenuItems(),
            share: {
                isAvailable: () => true,
                sequence: 42,
                icon: "ri-share-line",
                description: _t("Share"),
                callback: () => this.dialogService.add(UserShare, {
                    selected: this.model.root.selection.map(item => item.resId)
                }),

            },
        }
    }
}