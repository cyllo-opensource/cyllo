/** @odoo-module **/

/**
 * FormOverall
 *
 * Odoo Studio component for managing overall form layout and interactions.
 * Provides drag-and-drop functionality for form elements, including:
 *   - Fields
 *   - Inner groups
 *   - Notebook pages
 *   - Chatter component
 *   - Tree view components (for X2Many)
 *
 * Handles component setup, state management, and interaction with Odoo services:
 *   - rpc: For server calls related to form modifications.
 *   - dialogService: For opening dialogs, such as FormTreeDialog.
 *   - action: For triggering Odoo actions and reloading the studio view.
 *   - notification: For effect notifications.
 *
 * State Properties:
 *   - can_create, can_edit, can_delete: Permissions for CRUD operations.
 *   - invisible: Tracks elements visibility status.
 *   - position: Tracks editable position of elements.
 *   - massedit: Enables multi-edit functionality.
 *   - view: Current view type (form, tree, kanban, etc.).
 *   - active_field: Currently selected field.
 *   - orders: Sorting order for the view.
 *   - groupBy: Grouping configuration.
 *   - showLink: Whether to open linked form view.
 *   - view_type: Determines form view type (tree, kanban, or standard form).
 *   - isChatterAvailable, hasChatter: Chatter availability.
 *   - isNotebookPageChange: Tracks notebook page changes.
 *   - fieldDropped: Indicates if a field was dropped in the form.
 *
 * Key Functionalities:
 *   - onWillStart: Initializes chatter availability and invisible state from server/session.
 *   - useEffect: Sets up drag-and-drop functionality for form elements.
 *   - Drag-and-drop handling:
 *       - Provides visual feedback while dragging.
 *       - Handles cloning, shadowing, and dropping of components.
 *       - Supports dynamic addition of notebook pages, inner groups, and fields.
 *       - Integrates with server-side RPC for adding/removing components.
 *       - Manages Undo/Redo history via sessionStorage.
 *   - Listens to events such as 'Studio:NotebookChanged' to update state accordingly.
 *
 * Overall, FormOverall provides a central orchestration layer for building and editing forms
 * dynamically in Odoo Studio, ensuring user-friendly interactions and seamless integration
 * with the backend.
 */
import { Component, onWillStart, useRef, useState, onMounted, useEffect, onWillUpdateProps } from "@odoo/owl";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { FormTreeDialog } from "@cyllo_studio/js/view_editor/dialog/form_tree_dialog";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import { RibbonProperties } from "@cyllo_studio/js/view_editor/kanban/ribbon_properties";
import { RibbonDialog } from "@cyllo_studio/js/view_editor/kanban/ribbon_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
const Sortable = window.Sortable;

export class FormOverall extends Component {
    static template = "cyllo_studio.FormOverall";

    setup() {
        this.rpc = useService("rpc");
        this.dialogService = useService("dialog");
        this.action = useService("action");
        this.notification = useService('effect')
        this.isPreviewModeActive = false
        this.state = useState({
            can_create: this.props.mode.activeActions?.create || this.props.mode.create,
            can_edit: this.props.mode.activeActions?.edit || this.props.mode.edit,
            can_delete: this.props.mode.activeActions?.delete || this.props.mode.delete,
            invisible: false,
            position: this.props.mode.editable || "",
            massedit: this.props.mode.multiEdit,
            view: "",
            active_field: this.props.mode.defaultOrder?.[0]?.name || null,
            orders: this.props.mode.defaultOrder?.[0]?.asc,
            groupBy: this.props.mode.defaultGroupBy,
            showLink: this.props.mode.openFormView,
            view_type: this.props.x2many ? (this.props.x2many === 'list' ? 'tree' : 'kanban') : this.props.view_type,
            isChatterAvailable: true,
            hasChatter: this.props.isChatterAvailable,
            isNotebookPageChange: true,
            fieldDropped: false,
            hasStudioChanges: false,
            isPreviewMode: false,
            buttonLimitEnabled: false,
            buttonLimitValue: '',
            hasButtonLimitAttribute: false,
        });
        this.state.deactivatedViews = [];
        this.state.selectedDeactivatedViewId = null;
        this.loadDeactivatedViews();
        this.state.recordNameOptions = [];
        this.state.currentRecName = null;
        this.loadRecordNameData();
        const model =
            this.props?.viewInfo?.action?.res_model ||
            this.props?.archInfo?.model ||
            this.props?.resModel ||
            this.props?.model ||
            null;
        this.state.isStudioModel = model && model.startsWith("x_");

        onWillStart(async () => {
            await this.loadButtonLimitAttribute();
            this.state.invisible = sessionStorage.getItem('invisible');
            const storedUndo = JSON.parse(sessionStorage.getItem('UndoRedo') || "[]");
            if (storedUndo.length > 0) {
                this.state.hasStudioChanges = true;
            }

            const view_id = this.props.viewDetails?.viewId || this.props.viewId;
            if (view_id) {
                try {
                    const result = await this.rpc("/cyllo_studio/check_view_customized", {
                        view_id: view_id,
                    });
                    this.state.hasStudioChanges = !!result || storedUndo.length > 0;
                } catch (error) {
                    console.error("check_view_customized failed:", error);
                }
            }

            if (this.props.model) {
                const result = await this.rpc("/cyllo_studio/check/chatter", {
                    model: this.props.model
                });
                this.state.isChatterAvailable = !!result;
            } else {
                this.state.isChatterAvailable = false;
            }
        });

        const self = this;
        document.addEventListener('click', async (event) => {
            if (!self.state.isPreviewMode || !self.isPreviewModeActive) {
                return;
            }
            const clickText = (event.target.textContent || '').toLowerCase();
            if (clickText.includes('activate') ||
                clickText.includes('cancel') ||
                event.target.closest('select')) {
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            await self.cancelPreview();
            this.action.doAction("studio_reload");

        }, false);

        this.env.bus.addEventListener('Studio:NotebookChanged', (ev) => {
            setTimeout(() => {
                this.state.isNotebookPageChange = !this.state.isNotebookPageChange
            }, 100)

        })
        useEffect(() => {
            const self = this;
            const sortableInstances = [];

            const styleId = 'cyllo-ribbon-custom-styles';
            if (!document.getElementById(styleId)) {
                const s = document.createElement('style');
                s.id = styleId;
                s.textContent = `
                    /* Removed absolute positioning constraint to allow ghost to follow cursor during drag */
                `;
                document.head.appendChild(s);
            }


            if (!window._cy_sortable_gbcr_patched) {
                const originalGBCR = Element.prototype.getBoundingClientRect;
                Element.prototype.getBoundingClientRect = function () {
                    if (this.classList && this.classList.contains('o_wrap_field') && this.classList.contains('d-sm-contents')) {
                        let rect = { top: Infinity, left: Infinity, right: -Infinity, bottom: -Infinity };
                        let hasChildren = false;
                        for (let i = 0; i < this.children.length; i++) {
                            let childRect = originalGBCR.call(this.children[i]);
                            if (childRect.width > 0 || childRect.height > 0) {
                                hasChildren = true;
                                rect.top = Math.min(rect.top, childRect.top);
                                rect.left = Math.min(rect.left, childRect.left);
                                rect.right = Math.max(rect.right, childRect.right);
                                rect.bottom = Math.max(rect.bottom, childRect.bottom);
                            }
                        }
                        if (hasChildren) {
                            return {
                                top: rect.top, left: rect.left, right: rect.right, bottom: rect.bottom,
                                width: rect.right - rect.left, height: rect.bottom - rect.top,
                                x: rect.left, y: rect.top, toJSON: () => ({})
                            };
                        }
                    }
                    return originalGBCR.call(this);
                };
                window._cy_sortable_gbcr_patched = true;
            }

            const getXpath = (el) => {
                if (!el) return null;
                return el.getAttribute('cy-xpath') || el.querySelector('[cy-xpath]')?.getAttribute('cy-xpath');
            };

            const getDropXpath = (target) => {
                if (!target) return null;
                const directPath = target.getAttribute('cy-xpath');
                if (directPath) return directPath;
                if (target.classList?.contains('o_form_sheet')) return 'form/sheet';
                const path = getXpath(target);
                if (path) return path;
                return 'form';
            };

            const createRibbonPreview = (target) => {
                document.querySelector('.cy-unsaved-ribbon-preview')?.remove();
                const preview = document.createElement('div');
                preview.className = 'ribbon ribbon-top-right cy-unsaved-ribbon-preview';
                preview.style.position = 'absolute';
                preview.style.top = '0';
                preview.style.right = '0';
                preview.style.zIndex = '5';
                preview.style.margin = '0';
                preview.style.padding = '8px 12px';
                preview.style.pointerEvents = 'auto';
                preview.style.cursor = 'pointer';
                preview.innerHTML = '<span class="text-bg-danger"></span>';

                if (getComputedStyle(target).position === 'static') {
                    target.style.position = 'relative';
                }
                target.appendChild(preview);
                return preview;
            };

            // 1. Helpers for styling ghosts and clones
            const applyGhostAppearance = (ghost, original) => {
                ghost.classList.remove('cy-components-column');
                if (original.classList.contains('cy-studio-ribbon')) {
                    ghost.classList.add('ribbon', 'ribbon-top-right');
                    ghost.style.zIndex = '10';
                    ghost.style.opacity = '1';
                    ghost.innerHTML = `<span class="text-bg-danger"></span>`;
                } else if (original.classList.contains('column-1')) {
                    ghost.innerHTML = col1;
                } else if (original.classList.contains('column-2')) {
                    ghost.innerHTML = col2;
                } else if (original.classList.contains('tab')) {
                    ghost.innerHTML = tab;
                } else if (original.classList.contains('field')) {
                    ghost.removeAttribute('style');
                    ghost.classList.remove('cy-studio-component-btn', 'cy-studio-move');
                    ghost.classList.add('add-fields', 'o_wrap_field', 'd-flex', 'd-sm-contents', 'flex-column', 'mb-3', 'mb-sm-0', 'dd-box', 'cy-container');
                    ghost.innerHTML = field;
                } else if (original.classList.contains('chatter')) {
                    ghost.innerHTML = chatter;
                } else if (original.classList.contains('kanban')) {
                    ghost.innerHTML = x2manyKanban;
                } else {
                    ghost.innerHTML = x2many;
                }
            };

            const applyCloneAppearance = (clone, original) => {
                clone.style.color = "black";
                if (original.classList.contains('cy-studio-ribbon')) {
                    return; // DO NOT mutate the clone left in the sidebar!
                }
            };

            // Custom ribbon drag — fully bypasses SortableJS to detach preview from cursor
            const startCustomRibbonDrag = (ribbonBtn, mousedownEvt) => {
                mousedownEvt.preventDefault();
                mousedownEvt.stopPropagation();

                // Create floating visual that looks exactly like a dropped ribbon
                const ghost = document.createElement('div');
                ghost.className = 'cy-ribbon-floating ribbon ribbon-top-right';
                ghost.innerHTML = `<span class="text-bg-danger"></span>`;
                ghost.style.position = 'absolute';
                ghost.style.zIndex = '9999';
                ghost.style.pointerEvents = 'none'; // let mouse events pass through to find hover targets
                ghost.style.opacity = '0'; // hidden until we enter a valid container
                document.body.appendChild(ghost);

                const validContainers = () => [
                    ...document.querySelectorAll('.tab-pane.active[cy-xpath]'),
                    ...document.querySelectorAll('.o_form_sheet')
                ].filter((container) => {
                    const rect = container.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                });

                let hoveredTarget = null;
                const relativeTargetStyles = new Map();

                const ensureRibbonTargetPosition = (target) => {
                    if (getComputedStyle(target).position !== 'static') return;
                    if (!relativeTargetStyles.has(target)) {
                        relativeTargetStyles.set(target, target.style.position || '');
                    }
                    target.style.position = 'relative';
                };

                const restoreRibbonTargetPosition = (target) => {
                    if (!target || !relativeTargetStyles.has(target)) return;
                    target.style.position = relativeTargetStyles.get(target);
                    relativeTargetStyles.delete(target);
                };

                const onMove = (e) => {
                    // Find which valid container the cursor is over
                    let found = null;
                    for (const c of validContainers()) {
                        const r = c.getBoundingClientRect();
                        if (e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom) {
                            found = c;
                            break;
                        }
                    }

                    if (found) {
                        if (hoveredTarget !== found) {
                            if (hoveredTarget) {
                                hoveredTarget.classList.remove('cy-ribbon-drop-target');
                                restoreRibbonTargetPosition(hoveredTarget);
                            }
                            hoveredTarget = found;
                            hoveredTarget.classList.add('cy-ribbon-drop-target');
                        }

                        ensureRibbonTargetPosition(found);
                        if (ghost.parentElement !== found) {
                            found.appendChild(ghost);
                        }
                        ghost.style.position = 'absolute';
                        ghost.style.left = 'auto';
                        ghost.style.top = '0';
                        ghost.style.right = '0';
                        ghost.style.opacity = '1';
                    } else {
                        // Not over a valid container, let it follow the cursor translucently
                        if (ghost.parentElement !== document.body) {
                            document.body.appendChild(ghost);
                        }
                        ghost.style.position = 'absolute';
                        ghost.style.right = 'auto';
                        ghost.style.left = (e.clientX - 50 + window.scrollX) + 'px';
                        ghost.style.top = (e.clientY - 50 + window.scrollY) + 'px';
                        ghost.style.opacity = '0.5';

                        if (hoveredTarget) {
                            hoveredTarget.classList.remove('cy-ribbon-drop-target');
                            restoreRibbonTargetPosition(hoveredTarget);
                            hoveredTarget = null;
                        }
                    }
                };

                const onUp = async (e) => {
                    document.removeEventListener('pointermove', onMove);
                    document.removeEventListener('pointerup', onUp);
                    document.removeEventListener('mousemove', onMove);
                    document.removeEventListener('mouseup', onUp);
                    isRibbonDragActive = false;
                    ghost.remove();
                    if (hoveredTarget) hoveredTarget.classList.remove('cy-ribbon-drop-target');

                    if (!hoveredTarget) {
                        relativeTargetStyles.forEach((position, target) => {
                            target.style.position = position;
                        });
                        relativeTargetStyles.clear();
                        return; // dropped outside valid zone
                    }

                    // Send the ribbon directly to handleDrop using our custom logic
                    await handleDrop(ribbonBtn, hoveredTarget, null);
                };

                // Initialize position immediately
                onMove(mousedownEvt);

                document.addEventListener('pointermove', onMove);
                document.addEventListener('pointerup', onUp);
                document.addEventListener('mousemove', onMove);
                document.addEventListener('mouseup', onUp);
            };

            // 4. Containers and HTML templates
            const forms = document.getElementsByClassName('o_form_sheet');
            const form_tabs = document.getElementsByClassName('tab-pane');
            const innerGroup = document.getElementsByClassName('o_inner_group');
            const component = document.getElementById('cyComponents');
            const componentElement = document.getElementById('cyComponents-elements-1');
            const componentElement2 = document.getElementById('cyComponents-elements-2');
            const chatterComponent = document.getElementById('chatterComponent');
            const form = forms ? forms[0] : forms;

            const col1 = '<div class="o_inner_group grid dd-container cy-studio-inner"></div>';
            const col2 = '<div class="o_group row align-items-start"><div class="o_inner_group grid dd-container cy-studio-inner border-class col-lg-6 py-2"></div><div class="o_inner_group grid dd-container cy-studio-inner border-class col-lg-6 py-2"></div></div>';
            const tab = '<div class="o_notebook d-flex w-100 horizontal flex-column"><div class="o_notebook_headers"><ul class="nav nav-tabs flex-row flex-nowrap"><li class="nav-item flex-nowrap cursor-pointer"><a class="nav-link active" href="#" role="tab" tabindex="0" name="">New Page</a></li><li class="nav-item flex-nowrap cursor-pointer"><a class="nav-link ri-add-line"></a></li></ul></div><div class="o_notebook_content tab-content"><div class="tab-pane active"></div></div></div>';
            const x2many = '<div class="o_field_widget o_field_one2many"><div class="o_list_view o_field_x2many o_field_x2many_list"><div class="o_x2m_control_panel d-empty-none mb-4"></div><div class="o_list_renderer o_renderer table-responsive o_list_renderer_5 col-12" tabindex="-1" style=""><table class="o_list_table table table-sm table-hover position-relative mb-0 o_list_table_ungrouped table-striped" style="table-layout: fixed;"><thead><tr><th tabindex="-1" class="align-middle o_column_sortable position-relative cursor-pointer o_list_number_th o_handle_cell opacity-trigger-hover" style="width: 33px;"></th><th tabindex="-1" class="align-middle o_column_sortable position-relative cursor-pointer opacity-trigger-hover" style="width: 33.33%;"><div class="d-flex"><span class="d-block min-w-0 text-truncate flex-grow-1">Product</span><i class="fa fa-lg fa-angle-down opacity-0 opacity-75-hover"></i></div><span class="o_resize position-absolute top-0 end-0 bottom-0 ps-1 bg-black-25 opacity-0 opacity-50-hover z-index-1"></span></th><th tabindex="-1" class="align-middle o_column_sortable position-relative cursor-pointer o_list_number_th opacity-trigger-hover" style="width: 92px;"><div class="d-flex flex-row-reverse"><span class="d-block min-w-0 text-truncate flex-grow-1 o_list_number_th">Quantity</span><i class="fa fa-lg fa-angle-down opacity-0 opacity-75-hover"></i></div><span class="o_resize position-absolute top-0 end-0 bottom-0 ps-1 bg-black-25 opacity-0 opacity-50-hover z-index-1"></span></th><th tabindex="-1" class="align-middle o_column_sortable position-relative cursor-pointer opacity-trigger-hover" style="width: 33.33%;"><div class="d-flex"><span class="d-block min-w-0 text-truncate flex-grow-1">Description</span><i class="fa fa-lg fa-angle-down opacity-0 opacity-75-hover"></i></div><span class="o_resize position-absolute top-0 end-0 bottom-0 ps-1 bg-black-25 opacity-0 opacity-50-hover z-index-1"></span></th><th tabindex="-1" class="align-middle o_column_sortable position-relative cursor-pointer o_list_number_th opacity-trigger-hover" style="width: 92px;"><div class="d-flex flex-row-reverse"><span class="d-block min-w-0 text-truncate flex-grow-1 o_list_number_th">Unit Price</span><i class="fa fa-lg fa-angle-down opacity-0 opacity-75-hover"></i></div><span class="o_resize position-absolute top-0 end-0 bottom-0 ps-1 bg-black-25 opacity-0 opacity-50-hover z-index-1"></span></th><th class="o_list_button" style="width: 33.33%;"></th><th class="o_list_controller o_list_actions_header position-sticky end-0"><div class="o-dropdown dropdown o_optional_columns_dropdown text-center border-top-0 o-dropdown--no-caret"><button type="button" class="dropdown-toggle btn p-0" tabindex="-1" aria-expanded="false"><i class="o_optional_columns_dropdown_toggle oi oi-fw oi-settings-adjust"></i></button></div></th></tr></thead><tbody class="ui-sortable"><tr><td></td><td class="o_field_x2many_list_row_add" colspan="6"><a href="#" role="button" tabindex="0">Add a product</a></td></tr><tr><td colspan="7">​</td></tr><tr><td colspan="7">​</td></tr><tr><td colspan="7">​</td></tr></tbody><tfoot class="o_list_footer cursor-default"><tr><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr></tfoot></table></div></div></div>';
            const x2manyKanban = '<div class="o_kanban_view" style="width: 100%;"><div class="d-flex flex-wrap gap-3" style="width:100%;"><div class="o_kanban_record shadow-sm p-3 rounded" style="width:calc(50% - 12px); min-height:120px;"><div class="o_kanban_primary fw-bold text-truncate mb-1">Product:</div><div class="o_kanban_primary text-muted small mb-1">Quantity:</div><div class="o_kanban_primary text-muted small mb-1">Description:</div><div class="o_kanban_primary text-muted small">Unit Price:</div></div><div class="o_kanban_record shadow-sm p-3 rounded" style="width:calc(50% - 12px); min-height:120px;"><div class="o_kanban_primary fw-bold text-truncate mb-1">Product:</div><div class="o_kanban_primary text-muted small mb-1">Quantity:</div><div class="o_kanban_primary text-muted small mb-1">Description:</div><div class="o_kanban_primary text-muted small">Unit Price:</div></div><div class="o_kanban_record shadow-sm p-3 rounded" style="width:calc(50% - 12px); min-height:120px;"><div class="o_kanban_primary fw-bold text-truncate mb-1">Product:</div><div class="o_kanban_primary text-muted small mb-1">Quantity:</div><div class="o_kanban_primary text-muted small mb-1">Description:</div><div class="o_kanban_primary text-muted small">Unit Price:</div></div><div class="o_kanban_record shadow-sm p-3 rounded" style="width:calc(50% - 12px); min-height:120px;"><div class="o_kanban_primary fw-bold text-truncate mb-1">Product:</div><div class="o_kanban_primary text-muted small mb-1">Quantity:</div><div class="o_kanban_primary text-muted small mb-1">Description:</div>      <div class="o_kanban_primary text-muted small">Unit Price:</div></div></div></div>';
            const chatter = '<div class="o-mail-Form-chatter oe_chatter o-isInFormSheetCy w-auto o-aside"><div class="o-mail-Chatter w-100 h-100 flex-grow-1 d-flex flex-column overflow-auto"></div></div>';
            const field = '<div class=" new_field o_cell flex-grow-1 o_wrap_label w-100  text-900 cursor-pointer opacity-75"><label class="o_form_label oe_inline">New Field</label></div><div class=" new_field o_cell flex-grow-1 flex-sm-grow-0 cursor-pointer opacity-75" style="width: 100%;"><div class="o_row o_row_readonly"><div name="new_field"><div class="d-inline-flex w-100"><input class="o_input" type="text" autocomplete="off" id="new_field_0" readonly="1"/></div></div></div></div>';
            const dragField = '<label class="text-nowrap">New Field</label>';

            // 5. Initialize Source Sortables
            const sources = [component, componentElement, componentElement2, chatterComponent].filter(Boolean);
            const sourceRibbonHandlers = [];
            let isRibbonDragActive = false;

            // Attach custom pointer handling before SortableJS can filter out ribbon.
            sources.forEach(src => {
                const sourceRibbonHandler = (e) => {
                    const ribbonBtn = e.target.closest('.cy-studio-ribbon');
                    if (!ribbonBtn || isRibbonDragActive) return;
                    isRibbonDragActive = true;
                    startCustomRibbonDrag(ribbonBtn, e);
                };
                src.addEventListener('pointerdown', sourceRibbonHandler, true);
                src.addEventListener('mousedown', sourceRibbonHandler, true);
                sourceRibbonHandlers.push({ src, sourceRibbonHandler });
            });

            sources.forEach(src => {
                const sortableInstance = Sortable.create(src, {
                    group: { name: 'form-components', pull: 'clone', put: false },
                    sort: false,
                    animation: 150,
                    filter: '.cy-studio-ribbon', // Completely exclude Ribbon from SortableJS
                    preventOnFilter: true,
                    ghostClass: 'sortable-ghost-source',
                    onStart: (evt) => {
                        const el = evt.item;

                        if (el.classList.contains('chatter')) {
                            chatterComponent.classList.add('chatterContainer');
                            const dropHereDiv = document.createElement('div');
                            dropHereDiv.textContent = 'Drop Here';
                            dropHereDiv.classList.add('drop-here-container');
                            chatterComponent.appendChild(dropHereDiv);
                        }
                    },
                    onClone: (evt) => applyCloneAppearance(evt.clone, evt.item),
                    onEnd: (evt) => {
                        chatterComponent?.classList.remove('chatterContainer');
                        document.querySelector('.drop-here-container')?.remove();

                        // Kanban style: Restore the dragged element if not dropped
                        if (evt.to === evt.from) {
                            const clone = evt.item;
                            if (clone.__originalHTML !== undefined) {
                                clone.innerHTML = clone.__originalHTML;
                                clone.className = clone.__originalClassName;
                                clone.setAttribute('style', clone.__originalStyle);
                            }
                        }
                    }
                });
                sortableInstances.push(sortableInstance);
            });

            const targetContainers = [form, ...Array.from(form_tabs), ...Array.from(innerGroup)].filter(Boolean);
            targetContainers.forEach(target => {
                const sortableInstance = Sortable.create(target, {
                    group: {
                        name: 'form-components',
                        put: (to, from, dragEl) => {
                            if ([...innerGroup].includes(from.el) || dragEl.classList.contains('cy-chatter-exist')) return false;
                            if (dragEl.classList.contains('chatter')) return to.el === chatterComponent;
                            if (dragEl.classList.contains('cy-studio-ribbon')) return to.el.classList.contains('o_form_sheet') || to.el.classList.contains('tab-pane');
                            if (dragEl.classList.contains('field')) return to.el.classList.contains('o_inner_group');
                            if (dragEl.classList.contains('tab')) return to.el.classList.contains('o_form_sheet');
                            return to.el.classList.contains('o_form_sheet') || to.el.classList.contains('tab-pane');
                        }
                    },
                    animation: 150,
                    // Without these options, SortableJS only fires a swap when the cursor
                    // enters the *bottom* half of the element above, making dragging upward
                    // feel blocked or impossible.
                    // direction: 'vertical',
                    // swapThreshold: 0.65,  // trigger zone covers 65% of each item height
                    // invertSwap: true,      // top 35% of an item triggers "insert before" it
                    ghostClass: 'sortable-ghost',
                    chosenClass: 'sortable-chosen',
                    onAdd: async (evt) => {
                        const el = evt.item;
                        const targetEl = evt.to;

                        // SortableJS has already placed el at the correct DOM position by the
                        // time onAdd fires. Walk el.nextElementSibling (not evt.nextSibling,
                        // which is stale and wrong for upward drags) to find the real backend
                        // anchor node.
                        let rawSibling = el.nextElementSibling;
                        while (rawSibling && !getXpath(rawSibling)) {
                            rawSibling = rawSibling.nextElementSibling;
                        }
                        const sibling = rawSibling || null;

                        applyGhostAppearance(el, el);
                        await handleDrop(el, targetEl, sibling);

                        // Clean up ribbon overlay after drop
                        document.getElementById('cy-ribbon-drag-preview')?.remove();
                        // Remove the temporarily inserted ribbon element — the view
                        // reloads after save so it will re-render from the saved arch.
                        if (el.classList.contains('cy-studio-ribbon') && el.parentNode) {
                            el.remove();
                        }
                    }
                });
                sortableInstances.push(sortableInstance);
            });

            // 7. Drop Handler Logic
            const handleDrop = async (el, target, sibling) => {
                if (el.classList.contains("cy-studio-ribbon")) {
                    const viewId = self.props.viewId;
                    const viewType = self.props.viewType || self.props.view_type || 'form';
                    const model = self.props.model || self.action.currentController.props.resModel;
                    const ribbonPath = sibling ? getXpath(sibling) : getDropXpath(target);
                    const ribbonPosition = sibling ? "before" : "inside";
                    if (!ribbonPath) return;
                    const ribbonElement = createRibbonPreview(target);
                    self.env.bus.trigger("KANBAN_COMPONENT", {
                        type: "ribbon",
                        properties: { elementInfo: { path: ribbonPath, position: ribbonPosition } },
                        viewDetails: {
                            model,
                            viewId,
                            viewType,
                            view_id: viewId,
                            view_type: viewType,
                            allFields: self.props.allFields,
                        },
                        element: ribbonElement,
                        model,
                        viewId,
                        viewType,
                        allFields: self.props.allFields,
                    });
                    self.props.updateState?.("type", "ribbon");
                    self.props.updateState?.("edit", true);
                    return;
                }

                let item = '', position = sibling ? 'before' : 'inside';
                let path = sibling ? getXpath(sibling) : getXpath(target);
                self.state.fieldDropped = true;

                if (el.classList.contains('chatter')) path = '/form';
                if (el.classList.contains('column-1')) item = '<group></group>';
                else if (el.classList.contains('column-2')) item = '<group><group></group><group></group></group>';
                else if (el.classList.contains('tab')) item = '<notebook><page string="New Page"></page></notebook>';

                if (item || el.classList.contains('field') || el.classList.contains('chatter')) {
                    if (el.classList.contains('chatter')) {
                        self.env.services.ui.block();
                        try {
                            const add_remove = await self.rpc("cyllo_studio/add_remove/chatter", {
                                model: self.props.model, view_id: self.props.viewId, path: "/form", view_type: "form", position: "inside"
                            });
                            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo') || "[]");
                            storedArray.push(add_remove.replace(/\s+/g, ' ').trim());
                            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                            sessionStorage.setItem('ReDO', JSON.stringify([]));
                        } finally {
                            self.env.services.ui.unblock();
                            self.action.doAction('studio_reload');
                        }
                    } else if (el.classList.contains('field')) {
                        const fieldPath = sibling ? getXpath(sibling) : getXpath(target);
                        self.env.bus.trigger("FIELDS_DETAILS", { cy_path: fieldPath, position, create: true, type: "Properties" });
                    } else {
                        // Store notebook state if applicable
                        const currentNotebook = document.querySelector('.o_notebook .nav-link.active');
                        if (currentNotebook) {
                            const notebookContainer = currentNotebook.closest('.o_notebook');
                            const notebookId = notebookContainer?.getAttribute('data-notebook-id') || 'default';
                            const pageIndex = Array.from(currentNotebook.parentElement.parentElement.children).indexOf(currentNotebook.parentElement);
                            const storedPages = JSON.parse(sessionStorage.getItem("cy_studio_active_notebook") || "{}");
                            storedPages[notebookId] = pageIndex;
                            sessionStorage.setItem("cy_studio_active_notebook", JSON.stringify(storedPages));
                        }

                        self.env.services.ui.block();
                        const response = await self.rpc("cyllo_studio/add/component", {
                            method: 'add_component',
                            args: [{ view_type: 'form', view_id: self.props.viewId, path, position, item, model: self.action.currentController.action.res_model }]
                        });
                        self.env.services.ui.unblock();
                        self.action.doAction('studio_reload');
                        let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo') || "[]");
                        storedArray.push(response.replace(/\s+/g, ' ').trim());
                        sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                        sessionStorage.setItem('ReDO', JSON.stringify([]));

                        if (sessionStorage.getItem('cylloActivePagePath')) {
                            const newPath = sessionStorage.getItem('cylloActivePagePath');
                            const element = document.querySelector(`[cy-xpath="${newPath}"]`);
                            element?.firstElementChild?.click();
                        }
                    }
                } else if (el.classList.contains('kanban') || el.classList.contains('tree')) {
                    self.dialogService.add(FormTreeDialog, {
                        resModel: self.action.currentController.props.resModel,
                        isKanban: el.classList.contains('kanban'),
                        onConfirm: async (result) => {
                            self.env.services.ui.block();
                            const response = await self.rpc("cyllo_studio/add/form_tree", {
                                kwargs: { ...result, path, position, view_id: self.props.viewId, view_type: el.classList.contains('kanban') ? 'kanban' : 'form', model: self.action.currentController.props.resModel }
                            });
                            self.env.services.ui.unblock();
                            if (response) {
                                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo') || "[]");
                                storedArray.push(response.replace(/\s+/g, ' ').trim());
                                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                                sessionStorage.setItem('ReDO', JSON.stringify([]));
                            }
                            self.action.doAction("studio_reload");
                        },
                        onDiscard: () => {
                            if (el && el.parentNode) {
                                el.remove();
                            }
                        },
                        onClose: () => {
                            if (el && el.parentNode) {
                                el.remove();
                            }
                        },
                    });
                }
            };

            const selectedRibbonPath = sessionStorage.getItem('SelectedRibbonXPath');
            if (selectedRibbonPath) {
                const selectedRibbon = document.querySelector(`div.ribbon[cy-xpath="${selectedRibbonPath}"]`);
                if (selectedRibbon) {
                    const formSheet = selectedRibbon.closest('.o_form_sheet');
                    if (formSheet) {
                        formSheet.querySelectorAll('div.ribbon[cy-xpath]').forEach(rb => {
                            rb.style.display = rb === selectedRibbon ? '' : 'none';
                        });
                    }
                }
                sessionStorage.removeItem('SelectedRibbonXPath');
            }

            return () => {
                const s = document.getElementById('cyllo-ribbon-custom-styles');
                if (s) s.remove();
                const invDrag = document.getElementById('cy-invisible-drag');
                if (invDrag) invDrag.remove();
                sourceRibbonHandlers.forEach(({ src, sourceRibbonHandler }) => {
                    src.removeEventListener('pointerdown', sourceRibbonHandler, true);
                    src.removeEventListener('mousedown', sourceRibbonHandler, true);
                });
                sortableInstances.forEach(s => s.destroy());
            };
        }, () => [this.state.isNotebookPageChange])
    }

    /**
     * Returns all ribbon elements currently present in the form view DOM.
     * Used to detect whether the Ribbons edit row should be shown in the sidebar.
     *
     * @returns {Array<HTMLElement>} List of ribbon DOM elements with cy-xpath.
     */
    get formRibbons() {
        return Array.from(document.querySelectorAll('div.ribbon[cy-xpath]'));
    }

    /**
     * Opens the RibbonDialog to edit existing ribbons in the form view,
     * mirroring the kanban view's editRibbon() behaviour.
     */
    editRibbon() {
        const allRibbons = this.formRibbons;
        const fields = [];
        if (this.props.allFields) {
            for (const [fieldName, field] of Object.entries(this.props.allFields)) {
                fields.push({ value: fieldName, label: field.string });
            }
        }
        const model =
            this.props.model ||
            this.action?.currentController?.props?.resModel ||
            null;
        this.dialogService.add(RibbonDialog, {
            fields,
            ribbonElement: allRibbons,
            viewDetails: {
                viewId: this.props.viewId,
                viewType: this.props.viewType || 'form',
                model,
                active_fields: this.props.allFields,
            },
        });
    }

    /**
     * Loads available model fields and the currently configured display name.
     * Updates `state.recordNameOptions` and `state.currentRecName`.
     */
    async loadRecordNameData() {
        const model = this.props.model;
        if (!model) {
            this.state.recordNameOptions = [];
            this.state.currentRecName = null;
            return;
        }
        const fields = await this.rpc("/cyllo_studio/get_model_fields", { model });
        this.state.recordNameOptions = fields.map(f => ({
            label: f.label,
            value: f.name,
        }));
        const data = await this.rpc("/web/dataset/call_kw/ir.model/search_read", {
            model: "ir.model",
            method: "search_read",
            args: [[["model", "=", model]], ["cy_display_field"]],
            kwargs: {},
        });
        this.state.currentRecName = data?.[0]?.cy_display_field || "";
    }

    /**
     * Saves the selected field as the display name for the model.
     * Updates backend and reloads the view to reflect the change.
     */
    onRecordNameChange = async (newValue) => {
        const model = this.props.model;
        if (!model || !newValue) return;
        await this.rpc("/cyllo_studio/set_display_name", {
            model: model,
            field: newValue,
        });
        this.state.currentRecName = newValue;
        window.location.reload();
    };

    async resetView() {
        this.dialogService.add(ConfirmationDialog, {
            title: "Reset View",
            body: "Are you sure you want to reset this view to the default version? All studio changes will be lost.",
            confirmLabel: "Reset",
            cancelLabel: "Cancel",
            confirm: async () => {
                try {
                    let view_type = this.props.viewType;
                    let view_id = this.props.viewId;

                    const searchViewId = sessionStorage.getItem("searchViewId");
                    if (searchViewId) {
                        view_type = "search";
                        view_id = searchViewId;
                    }

                    await this.rpc("/cyllo_studio/reset_view", {
                        model: this.props.model,
                        view_type: view_type,
                        view_id: view_id,
                    });

                    sessionStorage.removeItem("UndoRedo");
                    sessionStorage.removeItem("ReDO");

                } finally {
                    sessionStorage.removeItem("UndoRedo");
                    sessionStorage.removeItem("ReDO");
                    this.state.hasStudioChanges = false;
                    this.action.doAction("studio_reload");
                    window.location.reload();
                }
            },
        });
    }

    async loadDeactivatedViews() {
        const view_id = this.props.viewId;
        if (!view_id) return;
        const views = await this.rpc("/cyllo_studio/get_deactivated_views", { view_id });
        this.state.deactivatedViews = (views || []).map(v => ({
            ...v,
            displayName: `Created: ${v.create_date} [ID: ${v.id}] ${v.name} `
        }));
        this.state.selectedDeactivatedViewId = views?.[0]?.id || null;
    }

    broadcastPreviewMode = () => {
        this.env.bus.trigger('PREVIEW_MODE_CHANGED', {
            isPreviewMode: this.state.isPreviewMode
        });
    }

    onDeactivatedViewSelect = async (viewId) => {
        const baseViewId = this.props.viewDetails?.viewId || this.props.viewId;
        if (!viewId || !baseViewId) return;

        this.state.selectedDeactivatedViewId = viewId;
        this.state.isPreviewMode = true;
        this.isPreviewModeActive = true;
        this.broadcastPreviewMode();
        await this.rpc("/cyllo_studio/preview_view", {
            view_id: viewId,
            base_view_id: baseViewId,
        });

        this.action.doAction("studio_reload");
    }


    async cancelPreview() {
        await this.rpc("/cyllo_studio/cancel_preview", {});
        this.state.isPreviewMode = false;
        this.state.selectedDeactivatedViewId = null;
        this.broadcastPreviewMode();
        this.action.doAction("studio_reload");
    }

    async activateSelectedView() {
        const viewId = this.state.selectedDeactivatedViewId;
        const baseViewId = this.props.viewDetails?.viewId || this.props.viewId;
        if (!viewId || !baseViewId) return;

        this.dialogService.add(ConfirmationDialog, {
            title: "Activate Studio View",
            body: "This will permanently activate the previewed view. Continue?",
            confirmLabel: "Activate",
            cancelLabel: "Cancel",
            confirm: async () => {
                try {
                    // Already active from preview, just clear session + undo history
                    await this.rpc("/cyllo_studio/cancel_preview", {}); // clear session only
                    // Re-activate cleanly via the proper route
                    await this.rpc("/cyllo_studio/activate_single_view", {
                        view_id: viewId,
                        base_view_id: baseViewId,
                    });
                    this.state.isPreviewMode = false;
                    this.isPreviewModeActive = false;

                    sessionStorage.removeItem("UndoRedo");
                    sessionStorage.removeItem("ReDO");
                } finally {
                    window.location.reload()
                }
            },
        });
    }

    /**
     * Load the current button_limit attribute from the header element
     */
    async loadButtonLimitAttribute() {
        try {
            const view_id = this.props.viewId || this.props.viewDetails?.viewId;
            const model = this.props.model;

            if (!view_id || !model) {
                this.state.buttonLimitEnabled = false;
                this.state.buttonLimitValue = '';
                return;
            }

            const result = await this.rpc("/cyllo_studio/get_button_limit", {
                view_id: view_id,
                model: model
            });

            if (result && result.button_limit) {
                this.state.buttonLimitEnabled = true;
                this.state.buttonLimitValue = result.button_limit.toString();
                this.state.hasButtonLimitAttribute = true;
            } else {
                this.state.buttonLimitEnabled = false;
                this.state.buttonLimitValue = '';
                this.state.hasButtonLimitAttribute = false;
            }
        } catch (error) {
            console.error("Error loading button limit attribute:", error);
        }
    }

    /**
     * Handle checkbox toggle for button limit
     */
    async toggleButtonLimit(event) {
        const isChecked = event.target.checked;
        this.state.buttonLimitEnabled = isChecked;

        if (!isChecked) {
            await this.removeButtonLimitAttribute();
            this.state.buttonLimitValue = '';
            this.state.hasButtonLimitAttribute = false;
        }
    }

    /**
     * Handle input field changes for button limit value
     */
    async updateButtonLimitValue(event) {
        const value = event.target.value.trim();

        if (!value) {
            return;
        }

        const numValue = parseInt(value);
        if (isNaN(numValue) || numValue <= 0) {
            return;
        }

        this.state.buttonLimitValue = numValue.toString();

        try {
            this.env.services.ui.block();
            await this.saveButtonLimitAttribute(numValue);
            this.action.doAction("studio_reload");
        } catch (error) {
            console.error("Error updating button limit:", error);
        } finally {
            this.env.services.ui.unblock();
        }
    }

    /**
     * Save button_limit attribute to header element via RPC
     */
    async saveButtonLimitAttribute(value) {
        const view_id = this.props.viewId || this.props.viewDetails?.viewId;
        const model = this.props.model;

        if (!view_id || !model) {
            throw new Error("Missing required parameters: view_id or model");
        }

        const result = await this.rpc("/cyllo_studio/set_button_limit", {
            view_id: view_id,
            model: model,
            button_limit: value
        });

        if (!result.success) {
            throw new Error(result.message || "Failed to save button limit");
        }

        this.state.hasButtonLimitAttribute = true;
    }

    /**
     * Remove button_limit attribute from header element via RPC
     */
    async removeButtonLimitAttribute() {
        const view_id = this.props.viewId || this.props.viewDetails?.viewId;
        const model = this.props.model;

        if (!view_id || !model) {
            console.warn("Missing parameters for removing button limit");
            return;
        }

        try {
            this.env.services.ui.block();
            const result = await this.rpc("/cyllo_studio/remove_button_limit", {
                view_id: view_id,
                model: model
            });

            if (result.success) {
                this.state.hasButtonLimitAttribute = false;
                this.action.doAction("studio_reload");
            }
        } catch (error) {
            console.error("Error removing button limit:", error);
        } finally {
            this.env.services.ui.unblock();
        }
    }

}

FormOverall.components = {
    ...FormOverall.components,
    CylloStudioDropdown
}
