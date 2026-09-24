/** @odoo-module **/
/**
 * KanbanComponents
 *
 * This module defines a draggable component panel for Kanban card editing
 * in Cyllo Studio. It allows users to dynamically add, move, and interact
 * with various Kanban elements such as fields, buttons, text, divs, and ribbons.
 *
 * Key Features:
 * 1. Drag-and-Drop Functionality:
 *    - Integrates with sortablejs to support dragging components onto Kanban cards.
 *    - Supports cloning, positioning, and restricting certain draggable elements.
 *    - Handles edge cases such as editing in progress or restricted elements.
 *
 * 2. Dynamic Element Handling:
 *    - Detects element type (field, button, text, div, ribbon) and triggers
 *      the appropriate action or dialog.
 *    - Ribbon elements have dedicated handling for position and styling.
 *
 * 3. Dialog Integration:
 *    - Opens `KanbanFieldDialog` for field selection when adding a field element.
 *    - Supports component-specific dialogs for ribbon, text, or buttons.
 *
 * 4. Undo/Redo Support:
 *    - Uses session storage to track changes for undo/redo functionality.
 *
 * 5. Scaling and Positioning:
 *    - Adjusts component position based on Kanban card scale.
 *    - Dynamically calculates top and left offsets for the draggable panel.
 *
 * 6. Lifecycle and State Management:
 *    - Uses OWL lifecycle hooks (`onMounted`, `useEffect`) to initialize drag-and-drop.
 *    - Maintains component state (`toggle`, `top`, `left`) using `useState`.
 *
 * Dependencies:
 * - RPC, action, dialog, notification, and other OWL services.
 * - KanbanFieldDialog for field insertion.
 * - scaleMapping from CylloKanbanRecord for handling card scaling.
 *
 * Purpose:
 * Enhances the Kanban editing experience in Cyllo Studio by enabling
 * intuitive drag-and-drop of components onto Kanban cards,
 * including dynamic handling of various component types and integration
 * with server-side updates.
 */
import {
    Component,
    useState,
    useRef,
    useEffect,
    onMounted,
} from "@odoo/owl";
import {
    useService
} from "@web/core/utils/hooks";
import {
    KanbanFieldDialog
} from "./kanban _field_dialog"
import {
    scaleMapping
} from "./cyllo_kanban_record"
export class KanbanComponents extends Component {
    static template = "cyllo_studio.KanbanComponents";
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("effect");
        this.componentRef = useRef("ComponentRef")
        this.state = useState({
            toggle: false,
            top: 0,
            left: 0,
        })
        onMounted(() => {
            const self = this
            const draggableComponent = this.componentRef.el
            const kanbanRecord = document.getElementById("cyKanbanRecord")

            const scaleKey = sessionStorage.getItem('kanbanScale') || '100%'
            const scale = scaleMapping[scaleKey] || 1
            this.state.top = kanbanRecord.offsetTop
            this.state.left = kanbanRecord.offsetLeft + scale * kanbanRecord.offsetWidth + 10;

            if (draggableComponent) {
                $(draggableComponent).draggable({
                    handle: ".cy-studio-handle",
                    containment: this.props.rendererRef.el,
                    drag: function(event, ui) {}
                })
            }
            sessionStorage.removeItem('KanbanEdit');
        })
        useEffect(() => {
            if (this.state.toggle) {
                return;
            }
            const self = this;
            const draggableComponent = this.componentRef.el;
            const component = draggableComponent.querySelector('.cy-studio-kanban-component');
            const kanbanRecord = document.getElementById("cyKanbanRecord");
            const divElements = Array.from(kanbanRecord?.querySelectorAll('[data-drag="1"]') || []);

            if (component && divElements.length) {
                let ribbonPath = divElements[0].getAttribute('cy-xpath');
                let ribbonPosition = 'inside';
                if (divElements[0].firstElementChild) {
                    ribbonPath = divElements[0].firstElementChild.getAttribute('cy-xpath');
                    ribbonPosition = 'before';
                }

                const sourceSortable = Sortable.create(component, {
                    group: {
                        name: 'kanban-components',
                        pull: 'clone',
                        put: false,

                    },
                    removeCloneOnHide: true,
                    sort: false,
                    animation: 150,
                    ghostClass: 'sortable-ghost-source',
                    onStart: function (evt) {
                        divElements.forEach((element) => {
                            element.classList.add('cy-studio-kanban-container');
                        });

                        const clone = evt.item;
                        clone.__originalHTML = clone.innerHTML;
                        clone.__originalClassName = clone.className;
                        clone.__originalStyle = clone.getAttribute('style') || '';

                        let Edit = sessionStorage.getItem('KanbanEdit');
                        if (Edit){
                            clone.classList.add('d-none');
                            return self.notification.add({
                                title: "Validation Error",
                                message: "Edit is in progress.",
                                description: "Please save or cancel the current process.",
                                type: "notification_panel",
                                notificationType: "warning",
                                animation: false,
                            });
                        }

                       clone.classList.remove('cy-studio-icon', 'bg-secondary', 'rounded', 'px-2', 'py-1', 'border', 'border-white', 'text-white', 'cy-component-container', 'kanban-component-text');
                       clone.removeAttribute('data-tooltip');
                       if (clone.classList.contains('cy-studio-field')) {
                           clone.classList.add('border-class', 'd-flex', 'justify-content-around', 'align-items-center')
                       } else if (clone.classList.contains('cy-studio-button')) {
                           clone.classList.add('border-class', 'd-flex', 'justify-content-around', 'align-items-center')

                       } else if (clone.classList.contains('cy-studio-text')) {
                           clone.classList.add('border-class', 'd-flex', 'justify-content-around', 'align-items-center')

                       } else if (clone.classList.contains('cy-studio-div')) {
                           clone.classList.add('border-class', 'd-flex', 'justify-content-around', 'align-items-center')
                       } else if (clone.classList.contains('cy-studio-ribbon')) {
                            clone.classList.add('ribbon', 'ribbon-top-right','sortable-ghost-source');
                            clone.style.zIndex = '10';
                            clone.style.opacity = '1';
                            clone.innerHTML = `<span class="text-bg-danger"></span>`;
                        }
                    },
                    onEnd: function (evt) {
                        divElements.forEach((element) => {
                            element.classList.remove('cy-studio-kanban-container');
                        });
                        if (evt.to === evt.from) {
                            const clone = evt.item;
                            if (clone.__originalHTML !== undefined) {
                                clone.innerHTML = clone.__originalHTML;
                                clone.className = clone.__originalClassName;
                                clone.setAttribute('style', clone.__originalStyle);
                            }
                        }
                    },
                });

                const targetSortables = divElements.map((targetEl) => {
                    return Sortable.create(targetEl, {
                        group: {
                            name: 'kanban-components',
                            pull: false,
                            put: function (to, from, dragEl) {
                                if (dragEl.classList.contains('cy-studio-ribbon')) {
                                    return divElements[0] === targetEl;
                                } else {
                                    return true;
                                }
                            },

                        },
                        animation: 150,
                        onAdd: async function (evt) {
                            const el = evt.item;
                            const sibling = el.nextElementSibling;
                            const target = targetEl;

                            // el.remove();

                            let Edit = sessionStorage.getItem('KanbanEdit');
                            if (Edit){
                                return self.notification.add({
                                    title: "Validation Error",
                                    message: "Edit is in progress.",
                                    description: "Please save or cancel the current process.",
                                    type: "notification_panel",
                                    notificationType: "warning",
                                    animation: false,
                                });
                            }

                            const siblingPath = sibling?.getAttribute('cy-xpath');
                            const targetPath = target.getAttribute('cy-xpath');
                            const path = siblingPath || targetPath;
                            const position = siblingPath ? 'before' : 'inside';
                            const matchingClass = Array.from(el.classList).find(cls => cls.startsWith('cy-studio-'));

                            const x2many = self.props.x2many;
                            self.env.bus.trigger('resetProperties');
                            const properties = {
                                elementInfo: {
                                    path,
                                    position,
                                },
                                viewDetails: {
                                    model: self.action.currentController.props.resModel,
                                    view_type: self.env.config.viewType,
                                    view_id: self.env.config.viewId,
                                },
                            };
                            let item;
                            switch (matchingClass) {
                                case 'cy-studio-button':
                                    item = 'button';
                                    break;
                                case 'cy-studio-field':
                                    item = 'field';
                                    break;
                                case 'cy-studio-text':
                                    item = 'text';
                                    break;
                                case 'cy-studio-div':
                                    item = 'div';
                                    break;
                                case 'cy-studio-ribbon':
                                    item = 'ribbon';
                                    properties.elementInfo.path = ribbonPath;
                                    properties.elementInfo.position = ribbonPosition;
                                    break;
                            }
                            if (item == 'field') {
                                self.dialog.add(KanbanFieldDialog, {
                                    ...properties,
                                    fields: self.props.fields,
                                    x2many: x2many,
                                });
                            } else if (item == 'ribbon') {
                                self.env.bus.trigger('KANBAN_COMPONENT', {
                                    type: item,
                                    properties,
                                    element: el,
                                });
                            } else if (item == 'button') {
                                self.env.bus.trigger('KANBAN_COMPONENT', {
                                    type: item,
                                    properties,
                                    newButton: true,
                                });
                            } else if (item == 'text') {
                                self.env.bus.trigger('kanbanSpanDetails', {
                                    type: item,
                                    properties,
                                    element: el,
                                    is_edit: false,
                                });
                            }
                            if (item === 'div') {
                                self.env.services.ui.block();
                                try {
                                    const response = await self.rpc("cyllo_studio/kanban/add/div", {
                                        ...properties.elementInfo,
                                        ...properties.viewDetails,
                                    });
                                    if (response) {
                                        let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                                        let cleanedStr = response.replace(/\s+/g, ' ').trim();
                                        storedArray.push(cleanedStr);
                                        sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                                        sessionStorage.setItem('ReDO', JSON.stringify([]));
                                    }
                                } finally {
                                    self.env.services.ui.unblock();
                                }
                                self.action.doAction('studio_reload');
                            }
                            sessionStorage.setItem('KanbanEdit', true);
                        },
                    });
                });

                return () => {
                try { sourceSortable.destroy(); } catch(e) {}
                    targetSortables.forEach(s => {
                try {
                    if (s.el) s.destroy();
                } catch(e) {}
                });
};
            }
        },
            () => [this.state.toggle]
        )

    }

}