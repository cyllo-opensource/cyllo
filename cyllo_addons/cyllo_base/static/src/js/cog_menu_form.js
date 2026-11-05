/** @odoo-module **/

import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { useBus } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { CogMenuItem } from "@cyllo_base/js/cog_menu_item";
import { ExportAll } from "@web/views/list/export_all/export_all";
import { ImportRecords } from "@base_import/import_records/import_records";
const { useState } = owl

// cog_menu_form.xml's web.ExportAll override and importRecords.xml's
// base_import.ImportRecords override only replace the template (still
// rendered by core's own component classes) — CogMenuItem is registered
// here since these are the classes that actually own those templates.
ExportAll.components = {
    ...ExportAll.components,
    CogMenuItem,
}
ImportRecords.components = {
    ...ImportRecords.components,
    CogMenuItem,
}

export class CyCogMenu extends CogMenu {
    async _registryItems() {
        const items = await super._registryItems();
        return items.filter(
            (item) => item.key !== "AddToBoard" && item.Component?.template !== "board.AddToBoard"
        );
    }

    // Reactive viewport flag from the ui service. Reading it from a template
    // (via the getters below) subscribes the component and re-renders the
    // toolbar when the window crosses the small-screen breakpoint.
    get isSmall() {
        return this.env.isSmall;
    }

    // Whether the row renders cog-item pills at all. Every view keeps at
    // least one pill inline; the fold count and fold dropdown differ per
    // class (see maxInlineCogItems / showOverflowMore / caretCogItems).
    get hasInlineCogItems() {
        return true;
    }

    // How many cog items stay inline in the row before the fold. Five is the
    // desktop split the row was built around; CogMenuList trims it to one on
    // phones (CogMenuForm keeps five at every size).
    get maxInlineCogItems() {
        return 5;
    }

    // The pills rendered inline in the row. Whatever they don't cover lives in
    // one of the two fold dropdowns: desktop's classic "More" overflow
    // (showOverflowMore) or the phone's "more ⌄" caret (caretCogItems).
    get inlineCogItems() {
        return this.cogItems.slice(0, this.maxInlineCogItems);
    }

    get overflowCogItems() {
        return this.cogItems.slice(this.maxInlineCogItems);
    }

    // The desktop "More" overflow button. CogMenuList suppresses it on phones
    // so a single fold dropdown (the caret) serves the whole screen.
    get showOverflowMore() {
        return this.cogItems.length > this.maxInlineCogItems;
    }

    // The inline "Print ▾" pill gate. The form view renders it at every size
    // (its caret fold is empty, so print reports need the pill), while
    // CogMenuList folds print items into the caret on phones.
    get showInlinePrintPill() {
        return this.hasInlineCogItems;
    }

    // Whatever the "more ⌄" caret dropdown renders. Empty on the form view and
    // on every desktop screen: CogMenuList is the one filling it for phones.
    get caretCogItems() {
        return [];
    }
}

export class CogMenuForm extends CyCogMenu {
    setup() {
        super.setup()
        this.state = useState({
            fieldIsDirty: false,
        });
        useBus(
            this.props.model.bus,
            "FIELD_IS_DIRTY",
            (ev) => (this.state.fieldIsDirty = ev.detail)
        );
    }

    get indicatorMode() {
        if (this.props.model.root.isNew) {
            return this.props.model.root.isValid ? "dirty" : "invalid";
        } else if (!this.props.model.root.isValid) {
            return "invalid";
        } else if (this.props.model.root.dirty || this.state.fieldIsDirty) {
            return "dirty";
        } else {
            return "saved";
        }
    }

    get displayButtons() {
        return this.indicatorMode !== "saved";
    }

    get isNew() {
        return this.props.model.root.isNew
    }
}

CogMenuForm.template = "cyllo_web.CogMenuForm";
CogMenuForm.components = {
    Dropdown,
    DropdownItem,
    CogMenuItem,
}

CogMenuForm.props = {
    ...CogMenu.props,
    create: { type: Function, optional: true },
    canCreate: { type: Boolean },
    saveButtonClicked: { type: Function, optional: true },
    discard: { type: Function, optional: true },
    edit: { type: Function, optional: true },
    canEdit: { type: Boolean },
    model: { type: Object },
    isEditOn: {type: Boolean,optional: true},
    slots: { type: Object, optional: true }
}

FormController.components = {
    ...FormController.components,
    CogMenuForm
}

export class CogMenuList extends CyCogMenu {
    get displayButtons() {
        return this.props.canEdit
    }

    get isNew() {
        return this.props.canEdit
    }

    // On phones the toolbar shows the fixed "+ New" row plus ONE cog pill
    // inline; the rest lives in the "more ⌄" caret dropdown instead of
    // overflowing the row. Desktop keeps the five-fold as everywhere else.
    get hasInlineCogItems() {
        return true;
    }

    get maxInlineCogItems() {
        return this.isSmall ? 1 : 5;
    }

    // The phone's single inline slot must go to an item that is actually
    // VISIBLE: Component items (Refresh, Split View, Add/Remove Shortcuts)
    // always render, while plain selection actions (Export All, Duplicate…)
    // render only when records are selected — reserving the slot for an
    // invisible item would blank the row.
    get inlineCogItems() {
        if (!this.isSmall) {
            return this.cogItems.slice(0, this.maxInlineCogItems);
        }
        const visible = this.cogItems.filter(
            (item) => item.Component || this.props.isSelected
        );
        return visible.length ? [visible[0]] : [];
    }

    get showOverflowMore() {
        // On phones the caret dropdown is the single fold — the desktop
        // overflow button would duplicate it.
        return !this.isSmall && this.cogItems.length > this.maxInlineCogItems;
    }

    // Print reports belong in the caret on phones; the inline "Print ▾" pill
    // stays a desktop (and form-view)-only affordance.
    get showInlinePrintPill() {
        return !this.isSmall;
    }

    get caretCogItems() {
        if (!this.isSmall) {
            return [];
        }
        // Everything beyond the inline pill. Same visibility rules as before
        // (Component items always, plain selection actions only when records
        // are selected) plus the print reports when they are available.
        const inlineItem = this.inlineCogItems[0];
        const items = this.cogItems.filter(
            (item) => item !== inlineItem && (item.Component || this.props.isSelected)
        );
        if (this.props.isSelected && this.printItems.length) {
            items.push(
                ...this.printItems.map((printItem, index) => ({
                    ...printItem,
                    key: `print-${printItem.key}-${index}`,
                }))
            );
        }
        return items;
    }

    onItemSelected(item) {
        if (this.props.isSelected) {
            super.onItemSelected(...arguments)
        }
    }
}

CogMenuList.template = "cyllo_web.CogMenuList";

CogMenuList.components = {
    Dropdown,
    DropdownItem,
    CogMenuItem,
}

CogMenuList.props = {
    ...CogMenuForm.props,
    isSelected: { type: Boolean, optional: true },
}

ListController.components = {
    ...ListController.components, CogMenuList
}

KanbanController.components = {
    ...KanbanController.components, CogMenuList
}
