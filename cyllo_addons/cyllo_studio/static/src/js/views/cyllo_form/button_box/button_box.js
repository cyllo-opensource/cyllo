/** @odoo-module  */

/**
 * ButtonBox Patch for Cyllo Studio
 *
 * Extends the default Odoo ButtonBox to provide additional Studio-specific functionality:
 *  - Drag-and-drop reordering of Smart Buttons
 *  - Adding new Smart Buttons dynamically
 *  - Edit mode validation before performing actions
 *  - Undo/Redo support via sessionStorage
 *  - Custom bus events to notify Studio about button changes
 *
 * Props:
 *  - cyXpath: optional string, the xpath of the ButtonBox
 *  - striped: optional boolean, enables striped styling
 *
 * State:
 *  - addSmartButtonIcon: boolean, show/hide "Add Smart Button" icon
 *  - clicked: boolean, indicates if a smart button is being added
 *  - isX2Many: string, xpath of X2Many field (from sessionStorage)
 *  - isEditingButton: boolean, true if a button is being edited
 *  - isEditingSmartButton: boolean, true if a smart button is being edited
 *  - isStudioEdit: boolean, true if Studio is in edit mode
 *
 * Events:
 *  - SMART_BUTTON_EDIT_STARTED: triggers when a Smart Button edit starts
 *  - SMART_BUTTON_DETAILS: triggers to provide Smart Button details to Studio
 */
import {
    ButtonBox
} from "@web/views/form/button_box/button_box";
import {
    patch
} from '@web/core/utils/patch';
import {
    useService
} from "@web/core/utils/hooks";
import {
    onWillUnmount
} from "@odoo/owl";
import {
    _t
} from "@web/core/l10n/translation";
import {
    validateEdit
} from "@cyllo_studio/js/root/studio_wrapper";


const {
    useRef,
    useState,
    onWillRender,
    onMounted
} = owl;

patch(ButtonBox.prototype, {
    setup() {
        this.action = useService("action");
        this.rpc = useService("rpc");
        this.ref = useRef('cy-ButtonBox')
        this.notification = useService("effect");
        this.state = useState({
            addSmartButtonIcon: true,
            clicked: false,
            isX2Many: sessionStorage.getItem('CyX2ManyPath'),
            isEditingButton: false,
            isEditingSmartButton: false,
        });
        onWillRender(() => {
            this.state.isX2Many = sessionStorage.getItem('CyX2ManyPath')
            this.visibleButtons = Object.entries(this.props.slots)
                .filter(([_, slot]) => this.isSlotVisible(slot))
                .map(([slotName]) => slotName)
            this.additionalButtons = [];
            this.isFull = true;
        });
        onMounted(this.onMounted)
    },
    /**
     * Initialize drag-and-drop for Smart Buttons
     * Handles reordering and updates via RPC
     */
    onMounted() {
    const self = this;
    const smart_button = this.ref.el;

    // Ref element may be absent (button box not rendered for this form).
    // Sortable.get(null) reads an expando off null and throws, so bail out.
    if (!smart_button) {
        return;
    }

    // Destroy existing sortable if any
    const existingSortable = Sortable.get(smart_button);
    if (existingSortable) existingSortable.destroy();

    Sortable.create(smart_button, {
        animation: 150,
        ghostClass: 'sortable-ghost',

        // Prevent the "add smart button" element from being dragged
        filter: '.cy-add-smart-button',
        preventOnFilter: true,

        // Only allow dropping before an existing sibling (not at the end)
        onMove: function(evt) {
            if (!evt.related || evt.related.classList.contains('cy-add-smart-button')) {
                return false;
            }
            return true;
        },

        onEnd: function(evt) {
            const {
                config,
                services,
                bus
            } = self.env;
            const model = self.action.currentController.action.res_model;
            const viewId = config.viewId || null;

            const el = evt.item;
            const smartButtonPath = el?.getAttribute('cy-xpath');

            // Get sibling that is now after the dropped element
            const sibling = el.nextElementSibling || null;
            const siblingPath = sibling?.getAttribute('cy-xpath');
            const sourcePath = smart_button?.getAttribute('cy-xpath');

            if (!(siblingPath || sourcePath) || !smartButtonPath || !model) {
                return;
            }
            if (!sibling || sibling.classList.contains('cy-add-smart-button')) {
                const children = Array.from(smart_button.children);
                const referenceNode = children[evt.oldIndex] || null;
                smart_button.insertBefore(el, referenceNode);
                return;
            }

            const position = siblingPath ? 'before' : 'inside';

            services.ui.block();

            self.rpc("cyllo_studio/move/smart_button", {
                kwargs: {
                    sourcePath: siblingPath || sourcePath,
                    position,
                    smartButtonPath,
                    model,
                    view_id: viewId,
                    viewType: 'form',
                }
            }).then((response) => {
                if (response?.trim()) {
                    const undoList = sessionStorage.getItem('UndoRedo');
                    const storedArray = undoList ? JSON.parse(undoList) : [];
                    storedArray.push(response.replace(/\s+/g, ' ').trim());
                    sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                    sessionStorage.setItem('ReDO', '[]');
                }
                services.ui.unblock();
                self.action.doAction('studio_reload');
                bus.trigger('resetProperties');
            }).catch((err) => {
                services.ui.unblock();
            });
        },
    });

    this.env.bus.addEventListener("BUTTON_EDIT_STARTED", ({ detail }) => {
        this.state.isEditingButton = detail.isEditingButton;
    });

    this.env.bus.addEventListener("STUDIO_EDIT_STARTED", ({ detail }) => {
        this.state.isStudioEdit = detail.isStudioEdit;
    });
},

    /**
     * Add a new Smart Button
     * Validates editing state, inserts dummy button, and triggers Studio events
     */
    async addSmartButton(e) {
       const notification = this.notification || useService("notification");
        if (
            !validateEdit(this.state, notification, "isEditingButton", "Button") ||
            !validateEdit(this.state, notification, "isEditingSmartButton", "Smart Button")
//            !validateEdit(this.state, notification, "isStudioEdit", "Editing")
        ) {
            return;
        }

        this.state.isEditingSmartButton = true;
        this.env.bus.trigger('SMART_BUTTON_EDIT_STARTED',{
             isEditingSmartButton : this.state.isEditingSmartButton
        });

        this.state.clicked = true
        const buttonBoxExists = document.querySelector('.button-box-container') !== null;
        const pathElement = document.querySelector('.o-form-buttonbox');

        const path = pathElement?.getAttribute('cy-xpath');
        const parent = e.target.closest(".oe_stat_button");

        if (parent) {
            parent.insertAdjacentHTML('beforebegin', `
                <button class="btn dummy-smart-button oe_stat_button btn-outline-secondary flex-grow-1 flex-lg-grow-0">
                    <i class="o_button_icon fa fa-fw fa-file-text-o me-1"></i>
                    <div class="o_field_widget o_readonly_modifier o_field_statinfo" id="SmartButtonLabel">
                        <span class="o_stat_info o_stat_value">0</span>
                        <span class="o_stat_text">Smart Button</span>
                    </div>
                </button>
            `);
        }

        this.env.bus.trigger('SMART_BUTTON_DETAILS', {
            properties: {
                new_button: true
            },
            addButtonBox: buttonBoxExists,
            path,
            type: "SmartButtonProperties",
            new_button: true
        });
    },
});

ButtonBox.props = {
    ...ButtonBox.props,
    cyXpath: {
        type: String,
        optional: true
    },
    striped: {
        type: Boolean,
        optional: true
    },
}
ButtonBox.template = 'cyllo_studio.ButtonBox'