/** @odoo-module **/
import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";
import { useBus, useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.spil = useState({
            split_view_enable: false
        })
        useBus(this.env.bus, "split_view_record_clicked", this.enableSplitView);
        useBus(this.env.bus, "split_view_close_clicked", this.disableSplitView);
        useBus(this.env.bus, "force_edit_o2m", this.enableEditO2M);
    },

    isRecordReadonly(record) {
        // FIXME: Override of isRecordReadonly to support manual Edit button workflow for One2many fields.
        //
        // Context:
        // Odoo by default enables auto-editing when a field is changed. In our implementation,
        // we have disabled auto-edit and enforced manual editing — users must explicitly click
        // the "Edit" button to modify any record, including One2many fields in list views.
        //
        // Issue:
        // Odoo's original `isRecordReadonly` logic (in addons/web/static/src/views/list/list_renderer.js)
        // blocks One2many record editing even after the parent form is in edit mode.
        // This interferes with our manual edit control, keeping x2many lists in readonly mode.
        //
        // Original Code:
        // --------------------------------------------------
        // isRecordReadonly(record) {
        //     if (record.isNew) {
        //         return false;
        //     }
        //     if (this.props.activeActions?.edit === false) {
        //         return true;
        //     }
        //     if (record.isInEdition && !this.isInlineEditable(record) && !record.model.multiEdit) {
        //         return true;
        //     }
        //     return false;
        // }
        // --------------------------------------------------
        //
        // Problem in this logic:
        // - The check `this.props.activeActions?.edit === false` forcibly sets records to readonly,
        //   even when we have already triggered manual edit mode via the "Edit" button.
        // - The `record.isInEdition && !this.isInlineEditable(...)` condition blocks
        //   One2many records shown in dialogs or nested lists.
        //
        // Fix Applied in cyllo.ListRenderer:
        // --------------------------------------------------
        // isRecordReadonly(record) {
        //     if (record.isNew) {
        //         return false;
        //     }
        //     if (!this.isInlineEditable(record) && !record.model.multiEdit) {
        //         return true;
        //     }
        //     return false;
        // }
        // --------------------------------------------------
        //
        // Result:
        // ✅ Respects manual "Edit" button workflow.
        // ✅ Allows One2many records to become editable inside form view lists when the user clicks Edit.
        // ✅ Keeps records readonly by default, preserving the no-auto-edit behavior.
        //
        // NOTE for future developers:
        // - If One2many records are not editable after clicking the Edit button, review this override first.
        // - Ensure that `isInlineEditable(record)` and `multiEdit` are correctly configured for your setup.
        // - If you're facing **any issues with list views or operations related to list rendering/editing**,
        //   inspect this function carefully, as it controls whether records are editable or readonly.
        if (record.isNew) {
            return false;
        }
        if (!this.isInlineEditable(record) && !record.model.multiEdit) {
            // in a x2many non editable list, a record is in edition when it is opened in a dialog,
            // but in the list we want it to still be displayed in readonly.
            return true;
        }
        return false;
    },

    async enableSplitView() {
        const modelName = this.props.list?.resModel || this.env.searchModel?.resModel || (window.location.href.includes('#') ? new URLSearchParams(window.location.href.split('#')[1]).get('model') : null);
        if (modelName) {
            this.is_split_view = await this.orm.call("ir.model", "get_split_view_mode", [modelName]);
            this.spil.split_view_enable = Boolean(this.is_split_view && this.is_split_view[0]?.list_split_view);
        } else {
            this.spil.split_view_enable = true;
        }
        if (this.spil.split_view_enable && this.rootRef?.el) {
            this.rootRef.el.style.flex = '1 1 0';
            this.rootRef.el.style.width = 'auto';
            this.rootRef.el.style.maxWidth = 'none';
            this.rootRef.el.style.overflowX = 'auto';
            this.rootRef.el.classList.remove('col-6');
        }
    },

    disableSplitView() {
        this.spil.split_view_enable = false;
        if (this.rootRef?.el) {
            this.rootRef.el.style.flex = '';
            this.rootRef.el.style.width = '';
            this.rootRef.el.style.maxWidth = '';
            this.rootRef.el.style.overflowX = '';
            this.rootRef.el.classList.remove('col-6');
        }
    },

    enableEditO2M() {
        this.props.listEditable = true;
        this.props.editable = true;
    },
})