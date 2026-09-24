/** @odoo-module **/
import {ListRenderer} from "@web/views/list/list_renderer";
import {registry} from "@web/core/registry";
import {Pager} from "@web/core/pager/pager";
import {KanbanRenderer} from "@web/views/kanban/kanban_renderer";
import {X2ManyField, x2ManyField} from "@web/views/fields/x2many/x2many_field";
import {ConfirmationDialog} from "@web/core/confirmation_dialog/confirmation_dialog";
import {useService} from '@web/core/utils/hooks';
import {_t} from "@web/core/l10n/translation";

const {useRef} = owl;

/** Extends X2ManyField to create class SearchX2ManyField to filter O2m records **/
export class SearchX2ManyField extends X2ManyField {
    setup() {
        super.setup()
        this.root = useRef("X2ManyFieldRoot");
    }

    /** Function to filter One2many records(Possible for number and alphabets) **/
    onInputKeyUp(ev) {
        var input_text = ev.target.value.toLowerCase();
        $(this.root.el).find('tr:not(:lt(1)):not(:last-child)').filter(function () {
            $(this).toggle($(this).text().toLowerCase().indexOf(input_text) > -1)
        });
    }
};
SearchX2ManyField.template = "O2MSearchTemplate";
export const SearchX2ManyFields = {
    ...x2ManyField,
    component: SearchX2ManyField,
};
registry.category("fields").add("one2many_search", SearchX2ManyFields);

/** Extends ListRenderer to create new class O2MListRenderer to show selection bow
 in One2many fields **/
export class O2MListRenderer extends ListRenderer {
    /** Replace the existing function to show selection in the One2many field
     when delete possible **/
    get hasSelectors() {
        if (this.props.activeActions.delete) {
            this.props.allowSelectors = true
        }
        let list = this.props.list
        list.selection = list.records.filter((rec) => rec.selected)
        list.selectDomain = (value) => {
            list.isDomainSelected = value;
            list.model.notify();
        }
        return this.props.allowSelectors && !this.env.isSmall;
    }

    toggleSelection() {
        const list = this.props.list;
        if (!this.canSelectRecord) {
            return;
        }
        const allSelected = list.selection.length === list.records.length;
        list.records.forEach(record => {
            record.toggleSelection(!allSelected);
            if (allSelected) list.selectDomain(false);
        });
    }

    /** Function that returns if selected any records **/
    get selectAll() {
        const list = this.props.list;
        const nbDisplayedRecords = list.records.length;
        if (list.isDomainSelected) {
            return true;
        } else {
            return false
        }
    }
}

/** Extends X2ManyField to create new class O2mMultiDelete for delete O2m records **/
export class O2mMultiDelete extends X2ManyField {
    /** Super the setup to replace the ListRenderer component with custom class(O2MListRenderer) **/
    setup() {
        super.setup();
        X2ManyField.components = {Pager, KanbanRenderer, ListRenderer: O2MListRenderer};
        this.orm = useService('orm');
        this.dialog = useService("dialog");
    }

    /** Function to return selected records **/
    get Selected() {
        return this.list.records.filter((rec) => rec.selected).length
    }

    /** Function to delete **/
    DltSelected() {
        let selectedRecords = this.list.records.filter((rec) => rec.selected)
        /** Confirmation popup, on confirm: delete selected records **/
        this.dialog.add(ConfirmationDialog, {
            body: _t('Are you sure you want to delete selected records?'),
            confirm: () => selectedRecords.forEach((rec) => {
                if (this.activeActions.onDelete) {
                    selectedRecords.forEach((rec) => {
                        this.activeActions.onDelete(rec);
                    })
                }
            }),
            cancel: () => {
            },
        });
    }
}

export const O2manyMultiDelete = {
    ...x2ManyField,
    component: O2mMultiDelete,
};

O2mMultiDelete.template = "O2mMultiDelete";
registry.category("fields").add("one2many_delete", O2manyMultiDelete);

/** Extend X2ManyField & create class O2mSearchDelete to create O2m delete and search widget **/
export class O2mSearchDelete extends X2ManyField {
    /** Super the setup **/
    setup() {
        super.setup();
        X2ManyField.components = {Pager, KanbanRenderer, ListRenderer: O2MListRenderer};
        this.orm = useService('orm');
        this.dialog = useService("dialog");
        this.root = useRef("X2ManyFieldRoot");
    }

    /** Function to filter One2many records(Based on number and alphabets) **/
    onInputKeyUp(ev) {
        var input_text = ev.target.value.toLowerCase();
        $(this.root.el).find('tr:not(:lt(1)):not(:last-child)').filter(function () {
            $(this).toggle($(this).text().toLowerCase().indexOf(input_text) > -1)
        });
    }

    /** Function to return selected records **/
    get Selected() {
        return this.list.records.filter((rec) => rec.selected).length
    }

    /** Function to delete selected records**/
    DltSelected() {
        let selectedRecords = this.list.records.filter((rec) => rec.selected)
        /** Confirmation popup, on confirm: delete selected records **/
        this.dialog.add(ConfirmationDialog, {
            body: _t('Are you sure you want to delete selected records?'),
            confirm: () => selectedRecords.forEach((rec) => {
                if (this.activeActions.onDelete) {
                    selectedRecords.forEach((rec) => {
                        this.activeActions.onDelete(rec);
                    })
                }
            }),
            cancel: () => {
            },
        });
    }
}

export const O2manySearchDelete = {
    ...x2ManyField,
    component: O2mSearchDelete,
};
O2mSearchDelete.template = "O2mSearchDelete";
registry.category("fields").add("one2many_search_delete", O2manySearchDelete);