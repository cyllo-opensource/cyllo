/** @odoo-module **/
/**
 * Patch the Odoo Form StatusBarButtons to enable Studio button editing features.
 *
 * This module allows:
 * - Adding, moving, and editing custom buttons in Studio.
 * - Handling drag-and-drop reordering of buttons.
 * - Tracking editing states for normal buttons, smart buttons, and new buttons.
 * - Communicating changes via the Odoo event bus.
 *
 * Uses Owl hooks: useState, useRef, onMounted, and Odoo services for notifications and RPC.
 */
import {
    StatusBarButtons
} from '@web/views/form/status_bar_buttons/status_bar_buttons';
import {
    CylloStatusBarButtons
} from '@cyllo_base/js/status_bar_buttons';

import {
    patch
} from '@web/core/utils/patch';
const {
    useRef,
    useState,
    onMounted
} = owl;
import {
    useService
} from "@web/core/utils/hooks";
import {
    useBus
} from "@web/core/utils/hooks";
import {
    validateEdit
} from "@cyllo_studio/js/root/studio_wrapper";


patch(CylloStatusBarButtons.prototype, {
    setup() {
        super.setup();
        this.notification = useService("effect");
        this.state = useState({
            isVisible: true,
            hasSheet: true,
            isEditingButton: false,
            isEditingSmartButton: false,
            isStudioEdit: false,
            isEditingNewButton:false,
        });
        this.buttonRef = useRef('cy-Button');
        onMounted(() => this.onMounted());
        useBus(this.env.bus, 'REMOVE_BUTTON_PROPERTIES', ({ detail }) => {
            this.state.hasSheet = true
            this.state.isVisible = true
        });
        this.env.bus.addEventListener("SMART_BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingSmartButton = detail.isEditingSmartButton
        })
        this.env.bus.addEventListener("STUDIO_EDIT_STARTED", ({ detail }) => {
            this.state.isStudioEdit = detail.isStudioEdit
        })
        this.env.bus.addEventListener("NEW_BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingNewButton = detail.isEditingNewButton
        })
    },

     onMounted() {
        const sheet = document.querySelector('.o_form_sheet')?.getAttribute('sheet');
        if (sheet) {
            this.state.hasSheet = false;
        }

        const self = this;
        const buttonContainer = this.buttonRef.el;

        if (!buttonContainer) return;

        // Destroy existing sortable if any
        const existingSortable = Sortable.get(buttonContainer);
        if (existingSortable) existingSortable.destroy();

        Sortable.create(buttonContainer, {
            group: {
                name: 'status-bar-buttons',
                pull: false,
                put: false,
            },
            animation: 150,
            ghostClass: 'sortable-ghost',

            // Prevent the "add new button" element from being dragged
            filter: '.cy-add-button',
            preventOnFilter: true,

            // Only allow dropping before an existing button (not at the end)
            onMove: function(evt) {
                // Prevent moving after the last real button
                // (i.e. don't allow dropping after cy-add-button)
                if (evt.related?.classList.contains('cy-add-button')) {
                    return false;
                }
                return true;
            },

            onEnd: async function(evt) {
                // If dropped back to same position, do nothing
                if (evt.oldIndex === evt.newIndex) return;

                const el = evt.item;
                const buttonPath = el.getAttribute('cy-xpath');
                const children = Array.from(buttonContainer.children);
                const sibling = children[evt.newIndex + 1] || null;
                if (!sibling || sibling.classList.contains('cy-add-button')) {
                    const referenceNode = children[evt.oldIndex] || null;
                    buttonContainer.insertBefore(el, referenceNode);
                    return;
                }

                const siblingPath = sibling.getAttribute('cy-xpath');
                const path = siblingPath || '/form/header';
                const position = siblingPath ? 'before' : 'inside';

                self.env.services.ui.block();
                try {
                    const response = await self.env.model.rpc("cyllo_studio/move/button", {
                        method: 'move_button',
                        kwargs: {
                            path,
                            position,
                            buttonPath,
                            model: self.env.model.action.currentController.action.res_model,
                            view_id: self.env.config.viewId,
                            view_type: self.env.config.viewType,
                        }
                    });
                    if (response) {
                        let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                        let cleanedStr = response.replace(/\s+/g, ' ').trim();
                        storedArray.push(cleanedStr);
                        sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                        sessionStorage.setItem('ReDO', JSON.stringify([]));
                    }
                } catch(err) {
                    console.error("Move button RPC error:", err);
                } finally {
                    self.env.services.ui.unblock();
                }

                self.env.model.action.doAction('studio_reload');
            },
        });
    },

    async addNewButton() {
        const notification = this.notification || useService("notification");

        if (
            !validateEdit(this.state, notification, "isEditingButton", "ButtonNew")||
            !validateEdit(this.state, notification, "isEditingSmartButton", "Smart Button") ||
            // !validateEdit(this.state, notification, "isEditingNewButton", "EditingNewButton") ||
            !validateEdit(this.state, notification, "isStudioEdit", "EditingButton")
        ) {
            return;
        }
        const header = this.buttonRef.el.closest('.o_form_statusbar');
        const newHeader = header?.getAttribute('studio-header');
        const cyXpath = header?.getAttribute('cy-xpath');

        if (!header) return;
        this.state.isEditingButton = true;
        this.env.bus.trigger('BUTTON_EDIT_STARTED',{
             isEditingButton : this.state.isEditingButton
        });

        // Hide menu or toolbar if needed
        this.state.isVisible = false;

        this.env.bus.trigger('BUTTON_DETAILS', {
            type: "ButtonProperties",
            path: cyXpath || "",
            position: "inside",
            create: false,
            newButton: true,
            newHeader,
        });
    },
});
StatusBarButtons.template = 'cyllo_studio.Button'
