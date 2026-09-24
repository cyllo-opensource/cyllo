/** @odoo-module **/
/**
 * CylloFormController
 *
 * Extends Odoo's FormController to provide drag-and-drop field management
 * in Odoo Studio forms, including support for One2many and Many2many fields.
 * Handles field positioning, undo/redo, and x2many record details.
 *
 * Features:
 *   - Drag-and-drop fields within groups.
 *   - Handle multi-path fields (buttons or complex widgets).
 *   - Supports X2Many (One2many/Many2many) inline editing.
 *   - Tracks field movement direction for proper RPC update.
 *   - Integrates with undo/redo functionality via sessionStorage.
 *   - Reloads the view and clears menus after updates.
 *
 * State:
 *   - fieldMove: Tracks field drag toggle state.
 *   - isX2Many: Boolean indicating if currently editing a X2Many field.
 *   - x2ManyDetails: Stores details about the X2Many view being edited.
 *
 * Services:
 *   - rpc: For server-side RPC calls.
 *   - action: For performing Odoo actions.
 */
import {
    FormController
} from "@web/views/form/form_controller";
import {evaluateBooleanExpr} from "@web/core/py_js/py";
import {Layout} from "@web/search/layout";
import {useService} from "@web/core/utils/hooks";
import {CylloListRenderer} from "@cyllo_studio/js/views/cyllo_list/cyllo_list_renderer";
import {CylloKanbanRenderer} from "@cyllo_studio/js/views/cyllo_kanban/cyllo_kanban_renderer";
import {serializeXML} from "@web/core/utils/xml";

const {useState, useEffect, onWillStart} = owl;
const Sortable = window.Sortable;

export class CylloFormController extends FormController {
    async setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.fieldMove = useState({
            toggle: false,
            firstReload: true,
        });
        this.state = useState({
            isX2Many: false,
            CyX2Many: false,
            x2ManyDetails: {}
        });
        this.sortableInstances = [];
        const storedPages = sessionStorage.getItem("cy_studio_active_notebook");
        if (storedPages) {
            try {
                const parsedPages = JSON.parse(storedPages);
                // Ensure the state object exists before trying to merge
                if (this.props.state && this.props.state.activeNotebookPages) {
                    Object.assign(this.props.state.activeNotebookPages, parsedPages);
                }
            } catch (e) {
                console.error("Error restoring notebook pages:", e);
            }
        }

        onWillStart(async () => {
            this.env.bus.trigger("Studio:NotebookChanged")
            if (!this.env.config.viewId) {
                await this.rpc('/cyllo_studio/form/add/form_view', {
                    arch: serializeXML(this.props.arch),
                    model: this.props.resModel,
                })
                sessionStorage.setItem('CyStudioView', this.props.resModel)
                await this.action.doAction('studio_reload')
            }
        })
        const state = this.props.state || {};
        const activeNotebookPages = {
            ...state.activeNotebookPages
        };
        this.onNotebookPageChange = (notebookId, page) => {
            if (page) {
                this.fieldMove.toggle = !this.fieldMove.toggle;
                activeNotebookPages[notebookId] = page;

                sessionStorage.setItem(
                    "cy_studio_active_notebook",
                    JSON.stringify(activeNotebookPages)
                );
            }
        };
        useEffect(() => {
                const self = this;

                // Cleanup previous instances
                self.sortableInstances.forEach(instance => instance?.destroy());
                self.sortableInstances = [];

                const InGrps = document.getElementsByClassName("o_inner_group");

                // Store drag state
                let dragState = {
                    initialIndex: '',
                    initialX: '',
                    draggedElement: null,
                    sourceContainer: null
                };

                Array.from(InGrps).forEach((group, groupIndex) => {
                    const sortableInstance = Sortable.create(group, {
                        group: 'studio-fields',
                        animation: 150,
                        fallbackOnBody: false,
                        fallbackTolerance: 3,
                        swapThreshold: 0.5,
                        invertSwap: false,
                        direction: 'auto',
                        draggable: '.o_wrap_field',
                        ghostClass: 'sortable-ghost',
                        chosenClass: 'sortable-chosen',
                        dragClass: 'sortable-drag',
                        forceFallback: true,
                        fallbackClass: "cyllo-fallback-ghost",
                        scroll: document.querySelector('.o_content'),
                        scrollSensitivity: 90,
                        scrollSpeed: 20,
                        bubbleScroll: true,
                        filter: function (evt, item) {
                            if (evt.target.closest(".cy-studio-icon")) return true;
                            if (evt.target.closest(".add-fields")) return true;
                            const el = evt.target.closest(".o_wrap_field");
                            if (el && el.children.length > 3) return true;
                            return false;
                        },

                        onChoose: function (evt) {
                        },
                        onUnchoose: function (evt) {
                        },
                        onStart: function (evt) {
                            dragState.draggedElement = evt.item;
                            dragState.sourceContainer = evt.from;
                            dragState.initialIndex = evt.oldIndex;
                            dragState.initialX = evt.item.getBoundingClientRect().left;
                            const allInnerGroups = document.querySelectorAll('.o_inner_group');
                            allInnerGroups.forEach(group => {
                                if (group.classList.contains('grid')) {
                                    group.classList.remove('grid');
                                    group.setAttribute('data-had-grid', 'true');
                                }
                            });
                            const allGroups = document.querySelectorAll('.o_inner_group');
                            allGroups.forEach(grp => {
                                const fields = grp.querySelectorAll('.o_wrap_field');
                                fields.forEach(field => {
                                    if (field.classList.contains('d-sm-contents')) {
                                        field.classList.remove('d-sm-contents', 'flex-column');
                                        field.setAttribute('data-was-contents', 'true');
                                    }
                                });
                            });
                            const elementIcon = evt.item.querySelector(".cy-studio-field-icons");
                            elementIcon?.classList.add("d-none");
//                    evt.item.classList.remove("flex-column");
                        },
                        onClone: function (evt) {
                            const ghost = evt.clone;
                            const source = evt.item;

                            // Copy exact bounding box
                            const rect = source.getBoundingClientRect();
                            ghost.style.width = rect.width + "px";
                            ghost.style.height = rect.height + "px";

                            // Copy padding, margin, display
                            const styles = window.getComputedStyle(source);
                            ghost.style.padding = styles.padding;
                            ghost.style.margin = styles.margin;
                            ghost.style.display = styles.display;

                            // OPTIONAL — copy whole computed styles (keeps UI consistent)
                            for (let prop of styles) {
                                ghost.style[prop] = styles[prop];
                            }
                        },

                        onMove: function (evt, originalEvent) {
                            const related = evt.related;


                            // Block drops on trash container and separators
                            if (related && related.classList.contains('cy-inner-trash-container')) {
                                return false;
                            }
                            if (related && related.classList.contains('g-col-sm-2')) {
                                return false;
                            }

                            // Allow drops on o_wrap_field elements
                            if (related && related.classList.contains('o_wrap_field')) {
                                return true;
                            }
                            return true;
                        },
                        onEnd: async function (evt) {
                            const el = evt.item;
                            const elementIcon = el.querySelector(".cy-studio-field-icons");
                            elementIcon?.classList.remove("d-none");
                            const allInnerGroups = document.querySelectorAll('.o_inner_group[data-had-grid="true"]');
                            allInnerGroups.forEach(group => {
                                group.classList.add('grid');
                                group.removeAttribute('data-had-grid');
                            });
                            const allGroups = document.querySelectorAll('.o_inner_group');
                            allGroups.forEach(grp => {
                                const fields = grp.querySelectorAll('.o_wrap_field[data-was-contents="true"]');
                                fields.forEach(field => {
                                    field.classList.add('d-sm-contents');
                                    field.removeAttribute('data-was-contents');
                                });
                            });
                            if (el.getAttribute('data-was-contents') === 'true') {
                                el.classList.add('d-sm-contents');
                                el.removeAttribute('data-was-contents');
                            }
                            el.classList.add("flex-column");
                            // Only process if item was actually moved
                            if (evt.oldIndex === evt.newIndex && evt.from === evt.to) {
                                return;
                            }
                            await self.handleFieldDrop(evt, dragState);
                        }
                    });
                    self.sortableInstances.push(sortableInstance);
                });


                return () => {
                    // self.sortableInstances.forEach(instance => instance?.destroy());
                    //    self.sortableInstances.forEach(instance => {
                    //     try {
                    //         if (instance && instance.el !== null && instance.el !== undefined) {
                    //             instance.destroy();
                    //         }
                    //     } catch(e) {}
                    // });
                    self.sortableInstances.forEach(instance => {
                        try {
                            if (instance) {
                                // Remove from SortableJS global list BEFORE destroying
                                const sortables = Sortable.utils?.sortables || [];
                                const idx = sortables.indexOf(instance);
                                if (idx > -1) sortables.splice(idx, 1);

                                if (instance.el) {
                                    instance.destroy();
                                }
                            }
                        } catch (e) {
                        }
                    });
                    self.sortableInstances = [];
                };
            },
            () => [this.fieldMove.toggle]);
        await this.env.bus.addEventListener('X2ManyDetails', (ev) => {
            this.state.x2ManyDetails = ev.detail
            this.state.isX2Many = true
            this.path = ev.detail.path
        });
    }

    async handleFieldDrop(evt, dragState) {
        const el = evt.item;
        const target = evt.to;
        const source = evt.from;
        const movedInsideSame = source === target;


        const children = Array.from(target.children);
        const droppedIndex = children.indexOf(el);
        if (droppedIndex === -1) {
            console.error('Dropped element not found in target children. Aborting.');
            return;
        }

        // Find next o_wrap_field element after the dropped index
        let sibling = null;
        for (let i = droppedIndex + 1; i < children.length; i++) {
            if (children[i].classList.contains('o_wrap_field')) {
                sibling = children[i];
                break;
            }
        }

        const position = sibling ? 'before' : 'inside';

        // --- 2) Resolve target path (cy-xpath) ---
        let targetPath = target.getAttribute('cy-xpath') || '';

        if (sibling) {
            targetPath =
                sibling.querySelector('[cy-xpath]')?.getAttribute('cy-xpath') ||
                sibling.firstElementChild?.getAttribute('cy-xpath') ||
                sibling.firstElementChild?.firstElementChild?.getAttribute('cy-xpath') ||
                targetPath;
        }

        let item_path = '';
        let has_multipath = false;

        // Try to find direct cy-xpath nodes inside the dropped wrapper
        let subfields;
        try {
            subfields = el.querySelectorAll(':scope > div [cy-xpath]');
        } catch (e) {
            subfields = el.querySelectorAll('div [cy-xpath]');
        }

        if (subfields && subfields.length > 1) {
            has_multipath = true;
            item_path = {
                first_path: subfields[0].getAttribute('cy-xpath'),
                second_path: subfields[1].getAttribute('cy-xpath'),
            };
        } else if (subfields && subfields.length === 1) {
            item_path = subfields[0].getAttribute('cy-xpath');
        } else {
            const direct = el.querySelector('[cy-xpath]');
            if (direct) {
                item_path = direct.getAttribute('cy-xpath');
            } else {
                // 2) maybe the wrapper has nested structure: try a few nested attempts
                const f1 = el.firstElementChild?.querySelector('[cy-xpath]') || el.firstElementChild;
                const f2 = el.firstElementChild?.nextElementSibling?.querySelector('[cy-xpath]');

                if (f1 && f2) {
                    has_multipath = true;
                    item_path = {
                        first_path: f1.getAttribute ? f1.getAttribute('cy-xpath') : null,
                        second_path: f2.getAttribute ? f2.getAttribute('cy-xpath') : null,
                    };
                } else if (f1 && f1.getAttribute && f1.getAttribute('cy-xpath')) {
                    item_path = f1.getAttribute('cy-xpath');
                } else {
                    item_path = '';
                }
            }
        }

        let direction = '';
        if (movedInsideSame) {
            // Prefer Sortable's newIndex vs saved initialIndex
            if (typeof dragState.initialIndex === 'number' && typeof evt.newIndex === 'number') {
                direction = evt.newIndex > dragState.initialIndex ? 'down' : 'up';
            } else {
                direction = evt.newIndex > evt.oldIndex ? 'down' : 'up';
            }
        } else {
            // Compare final x to initialX (dragState should store initialX on dragStart)
            const finalX = el.getBoundingClientRect().left;
            if (typeof dragState.initialX === 'number') {
                direction = finalX > dragState.initialX ? 'right' : 'left';
            } else {
                // fallback: if source index unknown, default to left (safe)
                direction = 'left';
            }
        }

        // --- 5) Validate paths before RPC ---
        if (!targetPath) {
            console.error('No target path found - aborting move.');
            return;
        }
        if (!item_path || (has_multipath && (!item_path.first_path || !item_path.second_path))) {
            console.error('No valid item_path detected - aborting move. Multipath:', has_multipath);
            return;
        }

        // --- 6) Prepare payload and call server ---
        const payload = {
            item_path,
            path: targetPath,
            position,
            has_multipath,
            model: this.props.resModel,
            view_id: this.env.config.viewId,
            direction,
            inSource: movedInsideSame,
        };


        this.env.services.ui.block();
        try {
            const result = await this.rpc('/cyllo_studio/FieldPositionMove', {args: payload});

            if (result && result.FormArch) {
                // store clean arch patch for undo
                let stored = JSON.parse(sessionStorage.getItem('UndoRedo') || '[]');
                // keep patch trimmed to avoid huge whitespace diffs
                const cleaned = (typeof result.FormArch === 'string') ? result.FormArch.replace(/\s+/g, ' ').trim() : JSON.stringify(result.FormArch);
                stored.push(cleaned);
                sessionStorage.setItem('UndoRedo', JSON.stringify(stored));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            } else {
                console.warn('RPC returned no FormArch; server result:', result);
            }
        } catch (err) {
            console.error('RPC Error:', err);
        } finally {
            this.env.services.ui.unblock();
            await this.action.doAction('studio_reload');
            this.env.bus.trigger('resetProperties');
        }
    }


    get rendererX2ManyProps() {
        const props = {
            archInfo: this.state.x2ManyDetails.archInfo,
            list: this.state.x2ManyDetails.list,
            openRecord: (record) => {
            },
            evalViewModifier: (modifier) => {
                return evaluateBooleanExpr(modifier, this.state.x2ManyDetails.list.evalContext);
            },
        };

        if (this.state.x2ManyDetails.viewMode === "kanban") {
            const recordsDraggable = !this.state.x2ManyDetails.readonly && this.state.x2ManyDetails.recordsDraggable;
            props.archInfo = {...props.archInfo, recordsDraggable};
            props.readonly = this.state.x2ManyDetails.readonly;
            // TODO: apply same logic in the list case
            props.deleteRecord = (record) => {
                if (this.state.x2ManyDetails.isMany2Many) {
                    return this.state.x2ManyDetails.list.forget(record);
                }
                return this.state.x2ManyDetails.list.delete(record);
            };

            return props;
        }
        props.activeActions = this.state.x2ManyDetails.archInfo?.activeActions
        return props;
    }

    /*  Rewriting this function as empty for restrict auto save of record when studio on */
    async beforeUnload(ev) {
    }

}

CylloFormController.components = {
    ...FormController.components,
    Layout,
    CylloListRenderer,
    CylloKanbanRenderer,
}
CylloFormController.template = "studio.CylloFormController"