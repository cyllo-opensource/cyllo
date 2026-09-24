/** @odoo-module */

/**
 * CylloNotebook
 *
 * Extends Odoo's Notebook component to support Studio editing features.
 * Provides functionality to:
 *   - Add, select, and drag-and-drop notebook pages
 *   - Track editing state for buttons, smart buttons, and Studio mode
 *   - Integrate undo/redo for page operations
 *   - Trigger Studio events with the selected notebook page information
 *
 * Features:
 *   - `initDragDrop()`: Initializes drag-and-drop for notebook pages
 *   - `addNewPage(e)`: Adds a new page to the notebook and saves state via RPC
 *   - `onSelectPage(e)`: Handles selecting a page and triggers Studio bus events
 *
 * Props:
 *   - cyXpath (optional): The xpath for Studio tracking
 *   - groups (optional): Group information
 *   - autofocus (optional): Autoselect property for pages
 *   - invisible (optional): Visibility flag for the notebook
 */
import {Notebook} from "@web/core/notebook/notebook";
import {useService} from "@web/core/utils/hooks";
import { handleUndoRedo } from "@cyllo_studio/js/utils/undo_redo_utils";
import { useState }from "@odoo/owl";
const {useRef, onMounted} = owl;
import { validateEdit } from "@cyllo_studio/js/root/studio_wrapper";


export class CylloNotebook extends Notebook {
    static template = "cyllo_studio.Notebook";
    setup() {
        super.setup()
        this.pageRef = useRef('cy-Page');
        this.notification = useService("effect");
        this.action = useService("action");

        this.state.isEditingButton = false;
        this.state.isEditingSmartButton = false;
        this.state.isStudioEdit = false;
        onMounted(()=>{
            this.initDragDrop()
            this.env.bus.trigger("Studio:NotebookChanged")
        })
         this.env.bus.addEventListener("BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingButton = detail.isEditingButton
        })
        this.env.bus.addEventListener("SMART_BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingSmartButton = detail.isEditingSmartButton
        })
       this.env.bus.addEventListener("STUDIO_EDIT_STARTED", ({ detail }) => {
            this.state.isStudioEdit = detail.isStudioEdit
       })

    }

    initDragDrop() {
    const self = this;
    const page = this.pageRef.el;
    if (!page) return;

    // Destroy existing sortable if any
    const existingSortable = Sortable.get(page);
    if (existingSortable) existingSortable.destroy();

    Sortable.create(page, {
        animation: 150,
        ghostClass: 'sortable-ghost',
        filter: '.add-page',
        preventOnFilter: true,

        // Only allow dropping before an existing sibling (not at the end)
        onMove: function(evt) {
            if (!evt.related || evt.related.classList.contains('add-page')) {
                return false;
            }
            return true;
        },

        onEnd: async function(evt) {
            const view_id = self.env.config.viewId;
            const el = evt.item;
            const pagePath = el.getAttribute('cy-xpath');

            // Get sibling now after the dropped element
            const sibling = el.nextElementSibling || null;
            const siblingPath = sibling?.getAttribute('cy-xpath') || null;
            const sourcePath = page.getAttribute('cy-xpath');

            if (!sibling || sibling.classList.contains('add-page')) {
                const children = Array.from(page.children);
                const referenceNode = children[evt.oldIndex] || null;
                page.insertBefore(el, referenceNode);
                return;
            }

            const path = siblingPath || sourcePath;
            const position = siblingPath ? 'before' : 'inside';
            self.env.services.ui.block();
            const response = await self.env.model.rpc("cyllo_studio/move/page", {
                method: 'move_page',
                model: self.env.model.action.currentController.action.res_model,
                view_id: self.env.config.viewId,
                args: [],
                kwargs: {
                    path,
                    position,
                    pagePath,
                    model: self.env.model.action.currentController.action.res_model,
                    view_id: view_id ? view_id : null,

                }
            });
            if (response) {
                handleUndoRedo(response);
            }
            self.env.services.ui.unblock();
            self.action.doAction('studio_reload');
        },
    });
}
    /**
     * Add a new page to the notebook
     * @param {Event} e - Click event
     */
    async addNewPage(e) {
      const notification = this.notification || useService("notification");

        if (
            !validateEdit(this.state, notification, "isEditingButton", "Button") ||
//            !validateEdit(this.state, notification, "isStudioEdit", "Editing") ||
            !validateEdit(this.state, notification, "isEditingSmartButton", "Smart Button")
        ) {
            return;
        }

        const self = this
        const view_id = self.env.config.viewId
        var parent = event.target.closest('.cy-add-page');
        parent.insertAdjacentHTML('beforebegin', '<li class="nav-item flex-nowrap cursor-pointer"><a class="nav-link" href="#" role="tab" tabindex="0" name="">New Page</a></li>');
        this.env.services.ui.block();
        const response = await this.env.model.rpc("cyllo_studio/add/page", {
            method: 'add_page',
            model: this.env.model.action.currentController.action.res_model,
            view_id: self.env.config.viewId,
            view_type: self.env.config.viewType,
            args: [],
            kwargs: {
                path: parent.parentNode.getAttribute('cy-xpath'),
                model: this.env.model.action.currentController.action.res_model,
                view_id: view_id ? view_id : null,

            }
        })
       if(response){
          handleUndoRedo(response)
        }
        this.env.services.ui.unblock();
        this.env.model.action.doAction('studio_reload')
    }
    /**
     * Handle selection of a notebook page
     * @param {Event} e - Click event
     */
    onSelectPage(e) {
            const activeFields =
                this.env?.model?.root?.env?.activeFields ||
                this.env?.model?.env?.activeFields ||
                this.env?.model?.action?.currentController?.activeFields ||
                this.env?.model?.action?.currentController?.props?.activeFields ||
                {};
            const notification = this.notification || useService("notification");
            let autofocus = false;
            Object.values(this.props.slots).forEach(value => {
             if(value.autofocus){
                autofocus = true
             }
            });
            this.env.bus.trigger("Studio:NotebookChanged")
            if (e.isTrusted) {
                let newPath = this.props.slots[this.state.currentPage].cyXpath
                sessionStorage.setItem('cylloActivePagePath', newPath);
                const elements = document.querySelectorAll('.border-class');
                if (!e.target.parentElement.classList.contains('nav-tabs')) {
                    elements.forEach(e => {
                        e.classList.remove('border-class');
                    });
                    e.target.parentElement.classList.add('border-class')
                    }

            if (
                !validateEdit(this.state, notification, "isEditingSmartButton", "Smart Button") ||
                !validateEdit(this.state, notification, "isStudioEdit", "Editing")
            ) {
                return;
            }
            this.env.bus.trigger('SELECT_NOTEBOOK', {
                        properties: this.props.slots[this.state.currentPage],
                        type:"notebook_details",
                        autofocus: autofocus,
            });
            this.env.bus.trigger("STUDIO_EDIT_BUTTON_HIDE");

        }

    }
}
CylloNotebook.props = {
    ...Notebook.props,
    cyXpath: {type: String, optional: true},
    groups: {type: String, optional: true},
    autofocus: {type: String, optional: true},
    invisible: {type: String, optional: true},
};
Notebook.template = 'cyllo_studio.Notebook'
