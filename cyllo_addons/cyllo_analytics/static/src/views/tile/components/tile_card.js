/* @odoo-module */
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { SheetDeleteDialog } from "@cyllo_analytics/js/cyllo_sheet";
import { TileRenameDialog } from "./tile_rename_dialog";
import { Component } from "@odoo/owl";
import { getImageSrcFromRecordInfo } from "@web/views/kanban/kanban_record";

export class TileCard extends Component {
    setup() {
        this.action = useService('action')
        this.dialogService = useService('dialog')
        this.id = this.props.value.evalContext.id
    }
    get Image() {
        const {
            value: record,
            model,
            imageField
        } = this.props
        return getImageSrcFromRecordInfo(record, model, imageField || "image_1920", this.id) //Todo: Make image_1920 dynamic field
    }
    get tileData() {
        return this.props.value.data;
    }
    openView() {
        if (this.props.model == "dashboard.sheet") {
            this.action.doAction("cyllo_analytics.cyllo_dashboard_sheet", {
                target: "fullscreen",
                additionalContext: {
                    rec_id: this.id
                }
            })
        }
        if (this.props.model == "dashboard.config") {
            this.action.doAction({
                type: "ir.actions.client",
                tag: "cy_analytic_dashboard",
                target: "current",
                context: {
                    rec_id: this.id
                }
            })
        }
    }
    /** Rename in place, so the name can be fixed without opening the record. */
    onClickRename() {
        const { value: { data } } = this.props
        this.dialogService.add(TileRenameDialog, {
            name: data.name,
            title: _t("Rename"),
            onConfirm: (name) => this.props.onRename(this.props, name),
        })
    }
    onClickDelete() {
        const { value: { data } } = this.props
        this.dialogService.add(SheetDeleteDialog, {
            id: data.id,
            callBackAction: () => {
                this.props.onDelete([this.props])
            },
            model: this.props.model,
            body: `Are You Sure you Want To Delete "${data.name}" ?`,
        })
    }
}
TileCard.template = `TileCard`;