/** @odoo-module */

/**
 * CylloInnerGroup & StudioOuterGroup
 *
 * These components extend the default Odoo form InnerGroup and OuterGroup
 * to provide Studio editing capabilities, including hover effects,
 * adding/deleting fields, panel menus, and sibling elements.
 *
 * Features:
 *  - Hover effects to highlight editable areas.
 *  - Add sibling fields with proper field metadata.
 *  - Delete form elements with Undo/Redo support.
 *  - Trigger bus events to update properties in the Studio panel.
 *
 * Props:
 *  - cy-xpath (optional): The xpath of the group/element for Studio tracking.
 *
 * Services:
 *  - rpc: Server-side calls for adding/deleting elements.
 *  - action: Trigger client-side actions like reloading the view.
 *
 * Methods:
 *  - over / overoff: Toggle hover state.
 *  - onAddClick: Toggle add field button icon.
 *  - addSibling: Add a sibling field in the form.
 *  - handlePanelMenu: Toggle panel menu visibility.
 *  - deleteElement: Remove a form element with Undo/Redo support.
 *  - itemOnDelete: Remove a component programmatically from the server.
 */
const {
    useState,
    useRef,
    onMounted
} = owl
import {
    InnerGroup, OuterGroup
} from "@web/views/form/form_group/form_group";
import {
    registry
} from "@web/core/registry";
import {
    patch
} from '@web/core/utils/patch';
import {
    useService
} from "@web/core/utils/hooks";
import {
    ConfirmationDialog
} from "@web/core/confirmation_dialog/confirmation_dialog";
import {
    _t
} from "@web/core/l10n/translation";

OuterGroup.props = [
    ...OuterGroup.props,
    "cy-xpath?"];
OuterGroup.template = "cyllo_studio.Form.StudioOuterGroup";

export class CylloInnerGroup extends InnerGroup {
    static template = "cyllo_studio.Form.StudioInnerGroup";
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.state = useState({
            hover: false,
            addField: true,
            panelMenu: '',
            sibling: '',
        });
        this.action = useService("action");
        this.dialog = useService("dialog");
        onMounted(() => {
            this.env.bus.trigger("allWidgets", {
                widgets: this.content,
            });
        });
    }

    /** Hover effect */
    over(ev) {
        this.state.hover = true
    }

    /** Remove hover effect */
    overoff(ev) {
        this.state.hover = false
    }

    /** Toggle add field icon */
    onAddClick(ev) {
        this.state.sibling = !this.state.sibling
        ev.target.classList.toggle('ri-add-circle-line');
        ev.target.classList.toggle('ri-close-circle-line');
    }

    /** Trigger adding sibling field */
    addSibling(ev, cell) {
        let parent = ev.target.closest(".o_wrap_field");
        let path = parent?.firstElementChild.getAttribute("cy-xpath");
        let itemType = 'normal'
        let field_info = {}
        if (!path) {
            itemType = ''
            let child = parent?.firstElementChild
            path = child.nextElementSibling?.firstElementChild.getAttribute('cy-xpath')
        } else {
            field_info = {
                string: cell.props.fieldInfo?.string,
                name: cell.props.fieldInfo?.name,
                help: cell.props.fieldInfo?.help,
                widget: cell.props.fieldInfo?.widget,
                placeholder: cell.props.fieldInfo?.placeholder,
                invisible: cell.props.fieldInfo?.invisible,
                readonly: cell.props.fieldInfo?.readonly,
                required: cell.props.fieldInfo?.required,
                context: cell.props.fieldInfo?.context,
                options: cell.props.fieldInfo?.options,
                domain: cell.props.fieldInfo?.domain,

            }

        }
        if (path) {
            this.env.bus.trigger("SIBLING_DETAILS", {
                type: "Properties",
                cy_path: path,
                sibling: true,
                item_type: itemType,
                field_info: field_info,
                create: true,
                sibling_edit: false,
                bold: false,
                italic: false,
                underline: false,
                classNames: "",
                string: "",
                is_edit: false,
                invisible: false,
            })
        }
    }

    /** Toggle panel menu */
    handlePanelMenu(ev) {
        if (ev.target.parentElement.nextElementSibling) {
            this.state.panelMenu = false
        } else {
            this.state.panelMenu = true
        }
        ev.target.classList.toggle('ri-arrow-left-s-fill');
        ev.target.classList.toggle('ri-arrow-right-s-fill');
    }
    /** Delete form element with undo support */
    async deleteElement(ev) {
        let parent = ev.target.closest(".o_wrap_field");
        let item_path = parent.firstElementChild.getAttribute("cy-xpath") || "";
        let has_multipath = false;
        if (!item_path) {
            let child = parent.firstElementChild;
            if (child.firstElementChild.nodeName == "BUTTON") {
                item_path = child.firstElementChild.getAttribute("cy-xpath");
            } else {
                has_multipath = true;
                item_path = {
                    first_path: child.firstElementChild.getAttribute("cy-xpath"),
                    second_path: child.nextElementSibling?.firstElementChild.getAttribute("cy-xpath"),
                };
            }
        }

        this.env.services.ui.block();
        try {
            const response = await this.rpc("/cyllo_studio/remove/form_element", {
                item_path,
                has_multipath,
                model: this.env.model.config.resModel,
                view_id: this.env.config.viewId,
            });
            if (response) {
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr)
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            }
        } finally {
            this.env.services.ui.unblock();
        }
        this.env.bus.trigger('resetProperties');
        this.action.doAction("studio_reload");
    }

    /**
     * Ask before removing a whole column — it takes every field in it along,
     * and the trash sits one stray click away from the fields themselves.
     * Read the xpath now: the dialog is async and the DOM may re-render.
     */
    itemOnDelete(ev) {
        const path = ev.target.parentElement.parentElement.attributes["cy-xpath"].value;
        this.dialog.add(ConfirmationDialog, {
            title: _t("Remove Column"),
            body: _t(
                "Are you sure you want to remove this column? Every field it contains will be removed from the view with it."
            ),
            confirm: () => this._doItemDelete(path),
            cancel: () => { },
        });
    }

    async _doItemDelete(path) {
        this.env.bus.trigger('resetProperties');
        const view_id = this.env.model.env.searchModel.env.config.viewId;
        const response = await this.env.model.rpc("cyllo_studio/delete/component", {
            method: "delete_component",
            model: this.env.model.config.resModel,
            view_id: this.env.model.env.searchModel.env.config.viewId,
            view_type: "form",
            args: [],
            kwargs: {
                viewType: "form",
                path,
                model: this.env.model.config.resModel,
                view_id: view_id ? view_id : null,
            },
        });
        if (response) {
            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
            let cleanedStr = response.replace(/\s+/g, ' ').trim();
            storedArray.push(cleanedStr)
            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
            sessionStorage.setItem('ReDO', JSON.stringify([]));
        }
        this.action.doAction("studio_reload");
    }

}
var value = window.location.href
var searchParams = new URLSearchParams(value.split("?")[1]);
CylloInnerGroup.props = [...InnerGroup.props, "cy-xpath?", "striped?", "cy-studio-striped?"];
for (const [, fieldDef] of registry.category("fields").getEntries()) {
    const FieldComponent = fieldDef.component || fieldDef;
    if (FieldComponent?.props) {
        if (!('placeholder' in FieldComponent.props)) {
            FieldComponent.props = {
                ...FieldComponent.props,
                placeholder: { type: String, optional: true },
            };
        }
        if (!('striped' in FieldComponent.props)) {
            FieldComponent.props = {
                ...FieldComponent.props,
                striped: { type: [Boolean, Number, String], optional: true },
            };
        }
    }
}

