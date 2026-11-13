/* @odoo-module */
import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * Small prompt used by the tile cards to rename a record (a template, a
 * dashboard or a sheet) without opening its form view.
 *
 * Props:
 *  - name      {string}   current name, pre-filled and pre-selected
 *  - title     {string}   dialog title
 *  - onConfirm {Function} called with the trimmed new name
 */
export class TileRenameDialog extends Component {
    setup() {
        this.state = useState({ name: this.props.name || "" });
        this.inputRef = useRef("nameInput");
        onMounted(() => {
            // Pre-select so typing replaces the old name straight away.
            this.inputRef.el?.focus();
            this.inputRef.el?.select();
        });
    }

    /** An empty name would silently blank the record — block it. */
    get isValid() {
        return !!this.state.name.trim();
    }

    async _confirm() {
        if (!this.isValid) {
            return;
        }
        await this.props.onConfirm(this.state.name.trim());
        this.props.close();
    }

    _cancel() {
        this.props.close();
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this._confirm();
        }
    }
}
TileRenameDialog.template = "cyllo_analytics.TileRenameDialog";
TileRenameDialog.components = { Dialog };
TileRenameDialog.defaultProps = {
    title: _t("Rename"),
};
