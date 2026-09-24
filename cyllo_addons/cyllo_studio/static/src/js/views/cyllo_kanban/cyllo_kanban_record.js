/** @odoo-module **/

/**
 * CylloKanbanRecord
 *
 * Extends Odoo's KanbanRecord component to provide advanced functionality
 * for Cyllo Studio's Kanban view editor.
 *
 * Features:
 * 1. Dynamic Scaling: Responds to 'KanbanScale' events to scale Kanban cards
 *    according to user-selected percentages (50%, 100%, 150%, etc.) and
 *    automatically fits cards to the screen width.
 *
 * 2. Drag-and-Drop Editing:
 *    - Supports rearranging Kanban elements and cards via drag-and-drop.
 *    - Integrates with Trash for removing elements.
 *    - Enforces restrictions on fields with 't-if', 't-elif', 't-else', or
 *      'data-restrict' attributes.
 *    - Supports Undo/Redo functionality using sessionStorage.
 *
 * 3. Ribbon Management:
 *    - Handles ribbon click events to open detailed RibbonDialog for editing.
 *    - Detects all ribbons within a record or within the root container.
 *
 * 4. Field & Span Interaction:
 *    - Captures clicks on fields or spans within Kanban cards.
 *    - Triggers detailed events with properties such as name, path, styling,
 *      invisibility, and restrictions.
 *    - Provides formatted display of field values using Odoo utilities.
 *
 * 5. Color Management:
 *    - Determines card classes based on colors or a cardColorField.
 *    - Includes a mapping function to assign consistent colors for string or
 *      numeric values.
 *
 * 6. Integration with Odoo Services:
 *    - Uses rpc, action, dialog, and notification services.
 *    - Communicates with bus events for property updates, field selection,
 *      and scaling.
 *
 * 7. Components & Compiler:
 *    - Uses CylloKanbanCompiler for compiling custom Kanban cards.
 *    - Supports CylloField component for rendering custom fields inside cards.
 *
 * This component is primarily designed for use in Cyllo Studio, where
 * developers and users can visually edit Kanban views, manipulate fields,
 * ribbons, and spans, and preview dynamic behaviors in real-time.
 */
import { KanbanRecord } from "@web/views/kanban/kanban_record";
const { useState, onMounted, useRef } = owl;
import { CylloKanbanCompiler } from "./cyllo_kanban_compiler";
import { useService } from "@web/core/utils/hooks";
import { getFormattedValue } from "@web/views/utils";
import { ColorList } from "@web/core/colorlist/colorlist";
import { CylloField } from "@cyllo_studio/js/view_editor/fields/field";
import { _t } from "@web/core/l10n/translation";
import { RibbonDialog } from "@cyllo_studio/js/view_editor/kanban/ribbon_dialog";


export const scaleMapping = {
    '50%': 0.5,
    '100%': 1,
    '150%': 1.5,
    '200%': 2,
    '250%': 2.5,
    '300%': 3,
};

const { COLORS } = ColorList;

/**
 * Returns the class name of a record according to its color.
 */
function getColorClass(value) {
    return `oe_kanban_color_${getColorIndex(value)}`;
}

/**
 * Returns the index of a color determined by a given record.
 */
function getColorIndex(value) {
    if (typeof value === "number") {
        return Math.round(value) % COLORS.length;
    } else if (typeof value === "string") {
        const charCodeSum = [...value].reduce((acc, _, i) => acc + value.charCodeAt(i), 0);
        return charCodeSum % COLORS.length;
    } else {
        return 0;
    }
}

export class CylloKanbanRecord extends KanbanRecord {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.dialogService = useService('dialog');
        this.notification = useService("effect")
        this.trashRef = useRef("kanbanTrash")
        this.state = useState({
            ...this.state,
            scale: 1,
        })
        this.env.bus.addEventListener('KanbanScale', ({ detail }) => {
            this.state.scale = scaleMapping[detail.scale] || (() => {
                //@Fixme:- Fit screen not correctly fit all kanban view correctly
                //@Todo: debug the scale calculation formula
                const kanbanRenderer = document.querySelector('.o_kanban_renderer');
                const kanbanRendererComputedStyle = window.getComputedStyle(kanbanRenderer);
                if (!this.rootRef.el) {
                    return 1
                }
                let width = this.rootRef.el.offsetWidth
                const kanbanRecordComputedStyle = window.getComputedStyle(this.rootRef.el);
                let marginLeft = parseFloat(kanbanRecordComputedStyle.marginLeft);
                let marginRight = parseFloat(kanbanRecordComputedStyle.marginRight);
                width = marginLeft + width + marginRight
                return parseFloat(kanbanRendererComputedStyle.width) / width;

            })();
        })
        onMounted(() => {
            const self = this;
            try {
                const selectedXPath = sessionStorage.getItem('SelectedRibbonXPath');
                if (selectedXPath && this.rootRef?.el) {
                    this.rootRef.el.querySelectorAll('[data-ribbon], .ribbon').forEach((rb) => {
                        rb.style.display = rb.getAttribute('cy-xpath') === selectedXPath ? '' : 'none';
                    });
                }
            } catch (e) { }
            this.rootRef.el.addEventListener("mousemove", (el) => {
                this.rootRef.el.querySelectorAll(".cy-studio-kanban-border")
                    .forEach(e => e.classList.remove("cy-studio-kanban-border"));
                el.target.closest('[cy-xpath]')?.classList.add('cy-studio-kanban-border');
            });

            const trashEl = this.trashRef.el;
            const divElements = Array.from(this.rootRef.el.querySelectorAll('[data-drag="1"]'));

            divElements.forEach(div => {
                div.addEventListener('click', (event) => {
                    if (event.target === div) {
                        document.querySelectorAll('.border-class')
                            .forEach(e => e.classList.remove('border-class'));
                        div.classList.add('border-class');
                        this.env.bus.trigger("KANBAN_DIV", {
                            view_id: this.env.config.viewId,
                            type: "KanbanDivProperties",
                            view_type: this.env.config.viewType,
                            model: this.action.currentController.props.resModel,
                            path: div.getAttribute('cy-xpath'),
                            div,
                        });
                    }
                });
            });
            const showTrash = () => {
                if (!trashEl) return;
                trashEl.style.setProperty('opacity', '1', 'important');
            };

            const hideTrash = () => {
                if (!trashEl) return;
                trashEl.style.setProperty('opacity', '0', 'important');
                trashEl.style.backgroundImage = '';
            };

            const glowTrash = () => {
                if (!trashEl) return;
                trashEl.style.setProperty('opacity', '100', 'important');
                trashEl.style.backgroundImage = 'radial-gradient(white, #fde0e0, #feaaaa)';
            };

            const unglowTrash = () => {
                if (!trashEl) return;
                trashEl.style.setProperty('opacity', '75', 'important');
                trashEl.style.backgroundImage = '';
            };
            const doRemove = async (el, withFieldCheck = true) => {
                el.classList.add('d-none');
                const path = el.getAttribute('cy-xpath');
                const fieldName = el.getAttribute('name');
                const regex = /field(\[\d+\])?$/;
                const isField = withFieldCheck && regex.test(path);

                let field = "";
                if (isField) {
                    const fieldNodes = self.props.archInfo.fieldNodes;
                    const nameExists = Object.keys(fieldNodes).filter(k => k.startsWith(fieldName));
                    const isPathIncluded = nameExists.some(n => fieldNodes[n].MainPath.includes('/kanban/field'));
                    field = isPathIncluded ? "" : fieldName;
                }
                try {
                    self.env.services.ui.block();
                    const response = await self.rpc("cyllo_studio/kanban/remove", {
                        view_id: self.env.config.viewId,
                        view_type: self.env.config.viewType,
                        model: self.action.currentController.props.resModel,
                        path,
                        field_name: field,
                    });
                    if (response) {
                        let arr = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                        arr.push(response.replace(/\s+/g, ' ').trim());
                        sessionStorage.setItem('UndoRedo', JSON.stringify(arr));
                        sessionStorage.setItem('ReDO', JSON.stringify([]));
                    }
                } catch (err) {
                    console.error("Remove RPC error:", err);
                } finally {
                    self.env.services.ui.unblock();
                }
                self.env.bus.trigger('resetProperties');
                self.action.doAction('studio_reload');
            };
            const doMove = async (el, target, newIndex) => {
                const path = el.getAttribute('cy-xpath');
                const targetChildren = Array.from(target.children);
                let siblingPath = null;
                if (targetChildren.length > newIndex + 1) {
                    siblingPath = targetChildren[newIndex + 1]?.getAttribute('cy-xpath');
                }
                const sibling_path = siblingPath || target.getAttribute('cy-xpath');
                const position = siblingPath ? 'before' : 'inside';

                if (!sibling_path || sibling_path === 'None') {
                    console.error("Invalid sibling_path:", sibling_path);
                    el.remove();
                    return;
                }

                try {
                    self.env.services.ui.block();
                    const response = await self.rpc("cyllo_studio/kanban/move", {
                        view_type: self.env.config.viewType,
                        model: self.action.currentController.props.resModel,
                        view_id: self.env.config.viewId,
                        path,
                        position,
                        sibling_path,
                    });
                    if (response) {
                        let arr = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                        arr.push(response.replace(/\s+/g, ' ').trim());
                        sessionStorage.setItem('UndoRedo', JSON.stringify(arr));
                        sessionStorage.setItem('ReDO', JSON.stringify([]));
                    }
                } catch (err) {
                    console.error("Move RPC error:", err);
                } finally {
                    self.env.services.ui.unblock();
                }
                self.env.bus.trigger('resetProperties');
                self.action.doAction('studio_reload');
            };
            const existingOptionsMap = new Map();
            divElements.forEach((el) => {
                const existing = Sortable.get(el);
                if (existing) {
                    existingOptionsMap.set(el, {
                        onAdd: existing.options.onAdd,
                        onStart: existing.options.onStart,
                        onEnd: existing.options.onEnd,
                    });
                    existing.destroy();
                }
            });
            if (trashEl) {
                const existingTrash = Sortable.get(trashEl);
                if (existingTrash) existingTrash.destroy();

                Sortable.create(trashEl, {
                    group: {
                        name: 'trash',
                        pull: false,
                        put: ['kanban-fields', 'kanban-components'],
                    },
                    animation: 0,
                    onAdd: async function (evt) {
                        hideTrash();
                        const isFromSidebar = !evt.item.getAttribute('cy-xpath');
                        if (isFromSidebar) {
                            evt.item.remove();
                            return;
                        }

                        const isDivDrag = evt.item.tagName.toUpperCase() === 'DIV'
                            && !!evt.item.getAttribute('data-drag');
                        await doRemove(evt.item, !isDivDrag);
                        evt.item.style.visibility = 'visible';
                    },
                });
            }

            divElements.forEach((container) => {
                const savedOptions = existingOptionsMap.get(container);

                Sortable.create(container, {
                    group: {
                        name: 'kanban-fields',
                        pull: true,
                        put: function (to, from, dragEl) {
                            // Always accept drops from the sidebar component panel
                            if (from.options?.group?.name === 'kanban-components') return true;
                            // Reject restricted elements
                            if ((dragEl.tagName === 'BUTTON' || dragEl.closest?.('button'))
                                && dragEl.getAttribute('data-restrict')) return false;
                            return !dragEl.getAttribute('data-restrict');
                        },
                    },
                    animation: 150,
                    ghostClass: 'sortable-ghost',

                    onStart: function (evt) {
                        if (evt.item.getAttribute('data-restrict')) {
                            self.triggerWarning("Elements with 't-if', 't-elif', or 't-else' attributes cannot be moved.");
                            return;
                        }
                        showTrash();
                        divElements.forEach(el => el.classList.add('cy-studio-kanban-container'));
                        savedOptions?.onStart?.call(this, evt);
                    },

                    onMove: function (evt) {
                        if (evt.to === trashEl) {
                            glowTrash();
                        } else {
                            unglowTrash();
                        }
                        return !evt.dragged.contains(evt.related);
                    },

                    onEnd: function (evt) {
                        hideTrash();
                        divElements.forEach(el => el.classList.remove('cy-studio-kanban-container'));
                        savedOptions?.onEnd?.call(this, evt);
                    },

                    onAdd: async function (evt) {

                        if (evt.to === trashEl) return;
                        const isFromSidebar = !evt.item.getAttribute('cy-xpath');
                        if (isFromSidebar) {
                            savedOptions?.onAdd?.call(this, evt);
                            return;
                        }

                        await doMove(evt.item, evt.to, evt.newIndex);
                    },
                });
            });

            divElements.forEach((el, i) => {
                const s = Sortable.get(el);
            });
        })

    }

    /**
     * Displays a warning notification to the user.
     * @param {string} message - The message to display.
     */
    triggerWarning(message) {
        this.notification.add({
            title: _t("Validation Error"),
            message,
            type: "notification_panel",
            notificationType: "warning",
            time: 5000
        });
    }

    /**
     * Computes and returns the CSS classes to be applied to this Kanban card.
     * Includes color classes, draggable state, and global click settings.
     * @returns {string} Space-separated list of CSS class names.
     */
    getRecordClasses() {
        const { archInfo, canResequence, forceGlobalClick, record, progressBarState } = this.props;
        const classes = ["o_kanban_record d-flex", "o_kanban_record_headings"];
        if (canResequence) {
            classes.push("o_draggable");
        }
        if (forceGlobalClick || archInfo.openAction) {
            classes.push("oe_kanban_global_click");
        }
        if (progressBarState) {
            const { fieldName, colors } = progressBarState.progressAttributes;
            const value = record.data[fieldName];
            const color = colors[value];
            classes.push(`oe_kanban_card_${color}`);
        }
        if (archInfo.cardColorField) {
            const value = record.data[archInfo.cardColorField];
            classes.push(getColorClass(value));
        }
        return classes.join(" ");
    }

    /**
    * Handles a click on a field within the Kanban card.
    * Triggers the 'KANBAN_FIELD_DETAILS' event with detailed field information.
    * @param {Event} el - The click event object.
    */
    handleSelectField(el) {
        const getRestrictAttribute = (el, level = 0) => {
            if (level > 5 || !el) {
                return false; // Stop the recursion if level exceeds 5 or no element is found
            }
            const isRestricted = el.getAttribute('data-restrict');
            if (isRestricted) {
                return !!isRestricted;
            }
            return getRestrictAttribute(el.parentElement, level + 1);
        }
        const name = el.target.getAttribute("name") || el.srcElement.parentElement.getAttribute('name')
        if (name) {
            // Only a real <field> placement (field-tag) carries a meaningful invisible
            // modifier. A t-out/t-esc reference (e.g. <span t-out="record.partner_id.value"/>)
            // renders regardless of the field declaration's invisible, so it is always visible.
            const isFieldTag = !!el.target.getAttribute("field-tag");
            this.env.bus.trigger('KANBAN_FIELD_DETAILS', {
                view_id: this.env.config.viewId,
                view_type: this.env.config.viewType,
                active_fields: this.props.list.activeFields,
                model: this.action.currentController.props.resModel,
                name: name,
                path: el.target.getAttribute("cy-xpath") || el.target.parentElement.getAttribute('cy-xpath'),
                invisible: isFieldTag ? (this.props.list.activeFields?.[name]?.invisible || null) : null,
                isRestricted: getRestrictAttribute(el.target),
                isFieldTag: isFieldTag,
                type: "KanbanFieldProperties",
                allfields: this.props.record.fields,
            });
        }
    }

    /**
     * Handles click events on a ribbon element in the Kanban card.
     * Opens the RibbonDialog with all ribbons found within the record or root container.
     * @param {Event} ev - The click event object.
     */
    handleRibbonClick(ev) {
        ev.stopPropagation(); // Prevent card opening
        const ribbonEl = ev.currentTarget;
        const spanEl = ribbonEl.querySelector('span') || ribbonEl;
        if (ribbonEl && ribbonEl.getAttribute('cy-xpath')) {
            this.env.bus.trigger('KANBAN_COMPONENT', {
                type: "ribbon",
                properties: {
                    is_edit: true,
                    elementInfo: { path: ribbonEl.getAttribute('cy-xpath') },
                    string: spanEl ? (spanEl.textContent?.trim() || '') : '',
                    color: spanEl ? (Array.from(spanEl.classList).find(c => c.startsWith('text-bg-')) || 'text-bg-danger') : 'text-bg-danger',
                    invisible: ribbonEl.getAttribute('data-invisible') || 'False',
                },
                element: ribbonEl,
            });
        }
        const kanbanRecord = ribbonEl.closest(
            '.oe_kanban_record, .o_kanban_record, [data-id], .kanban-record'
        );
        let allRibbons = [];

        if (kanbanRecord) {
            allRibbons = kanbanRecord.querySelectorAll('[data-ribbon], .ribbon[cy-xpath]');
        } else {
            const rootElement =
                this.rootRef?.el ||
                this.owl?.bdom?.el ||
                ribbonEl.closest('.cy-studio-kanban-border')?.parentElement;
            if (rootElement) {
                allRibbons = rootElement.querySelectorAll(
                    '[data-ribbon], .ribbon[cy-xpath]'
                );
            }
        }

        if (allRibbons.length) {
            this.openRibbonDialog(Array.from(allRibbons));
        }
    }

    /**
     * Opens a RibbonDialog for the provided ribbon elements.
     * Works for both Kanban and Form views.
     * @param {HTMLElement[]} ribbonElements - List of ribbon DOM elements to edit.
     */
    openRibbonDialog(ribbonElements) {
        // Build fields list
        const fields = [];
        if (this.props.list?.activeFields) {
            for (const [fieldName, field] of Object.entries(this.props.list.activeFields)) {
                fields.push({ value: fieldName, label: field.string });
            }
        }

        this.dialogService.add(RibbonDialog, {
            fields: fields,
            ribbonElement: ribbonElements,
            viewDetails: {
                viewId: this.env?.config?.viewId,
                viewType: this.env?.config?.viewType || 'kanban',
                model: this.action.currentController.props.resModel,
                active_fields: this.props.list?.activeFields || this.props.record?.fields,
            },
        });
    }

    /**
     * Handles a click on a span (text) element inside the Kanban card.
     * Triggers the 'kanbanSpanDetails' event with formatting and content info.
     * @param {Event} el - The click event object.
     */
    handleSelectSpan(el) {
        const spanEl = el.target;
        this.env.bus.trigger('kanbanSpanDetails', {
            string: spanEl.textContent,
            bold: spanEl.classList.contains("fw-bold") || (!spanEl.classList.contains("fw-normal") && (window.getComputedStyle(spanEl)?.fontWeight === "bold" || parseInt(window.getComputedStyle(spanEl)?.fontWeight) >= 500)),
            italic: spanEl.classList.contains("fst-italic") || (!spanEl.classList.contains("fst-normal") && (window.getComputedStyle(spanEl)?.fontStyle === "italic" || window.getComputedStyle(spanEl)?.fontStyle === "oblique")),
            underline: spanEl.classList.contains("text-decoration-underline") || (!spanEl.classList.contains("text-decoration-none") && (window.getComputedStyle(spanEl)?.textDecorationLine?.includes("underline") || window.getComputedStyle(spanEl)?.textDecoration?.includes("underline"))),
            is_edit: true,
            element: spanEl,
            view_id: this.env.config.viewId,
            model: this.action.currentController.props.resModel,
            view_type: this.env.config.viewType,
            type: "text",
        });
    }

    /**
     * Returns a formatted value for a field using Odoo utilities.
     * @param {string} fieldId - The ID of the field node.
     * @returns {string} Formatted string value for the field.
     */
    getFormattedValue(fieldId) {
        const {
            archInfo,
            record
        } = this.props;
        const {
            attrs,
            name,
            string
        } = archInfo.fieldNodes[fieldId];
        return getFormattedValue(record, name, attrs) || string;
    }

}

CylloKanbanRecord.components = {
    ...KanbanRecord.components,
    Field: CylloField
};
CylloKanbanRecord.Compiler = CylloKanbanCompiler;
CylloKanbanRecord.template = "cyllo_studio.KanbanRecord";
