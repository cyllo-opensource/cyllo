/** @odoo-module **/

import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { FormController } from "@web/views/form/form_controller";
import { ListController } from "@web/views/list/list_controller";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { useBus } from "@web/core/utils/hooks";
import { useResize } from "@cyllo_base/js/hooks"
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { CogMenuItem } from "@cyllo_base/js/cog_menu_item";
import { ExportAll } from "@web/views/list/export_all/export_all";
import { ImportRecords } from "@base_import/import_records/import_records";
const { useState, useRef } = owl

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

    setup() {
        super.setup();
        this.menuRef = useRef("menu");
        this.moreRef = useRef("more");
        this.responsiveRef = useRef("responsive_dropdown");
        useResize("resize", (width) => {
            if (this.responsiveRef.el) {
                const dropdownChildren = this.responsiveRef.el.children;
                let dropdownWidth = 0;
                const menuChildren = this.menuRef.el.children;
                let menuWidth = this.menuRef.el.clientWidth;
                [...dropdownChildren].forEach((item) => {
                    this.menuRef.el.appendChild(item);
                });
                [...menuChildren].forEach((item) => {
                    dropdownWidth += item.clientWidth;
                    if (dropdownWidth > (width - 20)) {
                        this.responsiveRef.el.appendChild(item);
                    }
                });
                this.moreRef.el.style.display = "none"
                if (dropdownChildren.length) {
                    this.moreRef.el.style.display = "block"
                }
            }
        })
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
