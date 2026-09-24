/** @odoo-module */

/**
 * CylloListRenderer
 *
 * Custom List (Tree) view renderer for Cyllo Studio, extending the default Odoo
 * listView.Renderer. Provides enhanced capabilities for dynamic field manipulation,
 * drag-and-drop reordering, session-based visibility, and interactive UI behaviors.
 *
 * Features:
 * 1. Field Management:
 *    - Handles adding new fields dynamically to the list view.
 *    - Triggers "FIELDS_DETAILS" events with field metadata for side panels.
 *    - Tracks edit state using sessionStorage to prevent concurrent edits.
 *
 * 2. Drag-and-Drop:
 *    - Integrates dragula for reordering columns in non-grouped lists.
 *    - Supports custom drag constraints to prevent moving non-draggable elements.
 *    - Sends updated field positions to the server via RPC calls.
 *
 * 3. Column Visibility:
 *    - Respects session-based visibility toggles using 'invisible' flag.
 *    - Evaluates column_invisible attributes using evalViewModifier.
 *
 * 4. Mouse Hover Effects:
 *    - Highlights columns on hover for better UX during list editing.
 *
 * 5. Column Width Management:
 *    - Computes and sets default widths for columns based on relative or absolute sizes.
 *    - Adjusts widths dynamically depending on whether selectors are enabled.
 *
 * 6. Integration with Cyllo Studio:
 *    - Triggers "LIST_DETAILS" event with list configuration for the Studio sidebar.
 *    - Tracks new elements and edits using sessionStorage flags for undo/redo consistency.
 *
 * Services Used:
 * - rpc: For server communication when moving fields.
 * - action: For triggering client-side actions like 'studio_reload'.
 * - effect: For showing notifications to the user.
 *
 * Components and Templates:
 * - template: "cyllo_studio.CylloListRenderer"
 * - rowsTemplate: "cyllo_studio.CylloListRenderer.Rows"
 * - recordRowTemplate: "cyllo_studio.CylloListRenderer.RecordRow"
 *
 * Purpose:
 * Enables a fully interactive list view editor within Cyllo Studio, allowing
 * drag-and-drop field reordering, dynamic visibility toggling, and live field
 * property editing.
 */
import { listView } from "@web/views/list/list_view";
import { onMounted, useRef, useState, onWillRender } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import { useService } from "@web/core/utils/hooks";


export class CylloListRenderer extends listView.Renderer {
  setup() {

    super.setup();
    this.list_trRef = useRef("list-tr");
    this.rpc = useService('rpc');
    this.action = useService("action");
    this.notification = useService("effect");
    this.state = useState({
      ...this.state,
      invisible_session: false,
      editable_field: false
    })
    this.state.invisible_session = sessionStorage.getItem("invisible");
    document.body.classList.toggle("cy-hide-invisible", !this.state.invisible_session);
    useBus(this.env.bus, "CYLLO:SHOW_INVISIBLE_TOGGLED", (ev) => {
      const isChecked = ev.detail ? ev.detail[0] : ev;
      this.state.invisible_session = isChecked;
    });
    onWillRender(() => {
      this.state.invisible_session = sessionStorage.getItem('invisible')
    })
    onMounted(() => {
      const checked = !!sessionStorage.getItem("invisible");
      document.body.classList.toggle("cy-hide-invisible", !checked);
      sessionStorage.removeItem("newListElement");
      this.env.bus.trigger("LIST_DETAILS", {
        mode: this.props.archInfo,
        model: this.env.model?.config.resModel,
        viewId: this.env.config.viewId,
        viewType: "tree",
        allFields: this.props.list.fields,
        activeFields: this.props.list.activeFields,
      });
      const self = this
      const treeEl = self.list_trRef.el
      if (self.props.activeActions.type === "view" && treeEl) {
        // Odoo-style column drag: a floating clone follows the cursor and a
        // drop indicator marks the target column. The real headers do NOT
        // reshuffle while dragging — the move is committed on drop via RPC +
        // studio_reload (which re-renders in the new order).
        const isDraggableTh = (th) =>
          th && th.tagName === 'TH' &&
          treeEl.contains(th) &&
          !th.classList.contains('add-fields') &&
          !th.classList.contains('o_list_open_form_view') &&
          !th.classList.contains('o_list_controller') &&
          !th.classList.contains('o_list_record_selector');

        const thFieldPath = (th) =>
          th.getAttribute('cy-xpath') ||
          th.querySelector('.cy-listBtn')?.getAttribute('cyxpath') || null;

        const table = treeEl.closest('table');

        let dropIndicator = null;

        const clearIndicator = () => {
          if (dropIndicator) { dropIndicator.remove(); dropIndicator = null; }
        };

        const showDropIndicator = (th, side) => {
          const tableEl = table || treeEl.closest('table') || treeEl;
          const tableRect = tableEl.getBoundingClientRect();
          const thRect = th.getBoundingClientRect();
          const x = side === 'after' ? thRect.right : thRect.left;
          if (!dropIndicator) {
            dropIndicator = document.createElement('div');
            dropIndicator.className = 'cy-drop-indicator';
            document.body.appendChild(dropIndicator);
          }
          Object.assign(dropIndicator.style, {
            top: `${tableRect.top}px`,
            left: `${x}px`,
            height: `${tableRect.height}px`,
          });
        };

        const onColumnPointerDown = (ev) => {
          if (ev.button !== 0) return;
          if (ev.target.closest('.o_resize')) return;
          const source = ev.target.closest('th');
          if (!isDraggableTh(source)) return;

          const startX = ev.clientX;
          const startY = ev.clientY;
          let started = false;
          let ghost = null;
          let dropTarget = null;
          let dropPosition = 'before';

          // Column index of the source th — computed once, reused in all helpers
          const srcColIdx = [...treeEl.querySelectorAll('th')].indexOf(source);

          const setSourceDimmed = (dim) => {
            source.classList.toggle('cy-col-dragging', dim);
            if (!table || srcColIdx < 0) return;
            table.querySelectorAll('tbody tr').forEach(tr => {
              const td = tr.cells[srcColIdx];
              if (td) td.classList.toggle('cy-col-dragging', dim);
            });
          };

          const onMove = (e) => {
            if (!started) {
              if (Math.hypot(e.clientX - startX, e.clientY - startY) < 5) return;
              started = true;
              const r = source.getBoundingClientRect();
              ghost = document.createElement('table');
              ghost.classList.add('cy-col-drag-ghost');
              ghost.style.width = `${r.width}px`;

              const thead = document.createElement('thead');
              const theadRow = document.createElement('tr');
              theadRow.appendChild(source.cloneNode(true));
              thead.appendChild(theadRow);
              ghost.appendChild(thead);

              if (table && srcColIdx >= 0) {
                const tbody = document.createElement('tbody');
                [...table.querySelectorAll('tbody tr')].slice(0, 6).forEach(tr => {
                  const td = tr.cells[srcColIdx];
                  if (td) {
                    const row = document.createElement('tr');
                    row.appendChild(td.cloneNode(true));
                    tbody.appendChild(row);
                  }
                });
                if (tbody.children.length) ghost.appendChild(tbody);
              }

              document.body.appendChild(ghost);
              ghost.style.setProperty('left', '0px', 'important');
              ghost.style.setProperty('top', '0px', 'important');
              ghost.style.setProperty('pointer-events', 'none', 'important');
              setSourceDimmed(true);
            }

            e.preventDefault();
            const under = document.elementFromPoint(e.clientX, e.clientY);
            ghost.style.setProperty('transform', `translate(calc(${e.clientX}px - 50%), calc(${e.clientY}px - 20px))`, 'important');

            const targetTh = under && under.closest('th');

            let newDropTarget = null;
            let newDropPosition = 'before';
            let newIndicatorTh = null;
            let newIndicatorSide = 'before';

            if (targetTh && targetTh.classList.contains('add-fields')) {
              const allDraggable = [...treeEl.querySelectorAll('th')].filter(isDraggableTh);
              const lastTh = allDraggable[allDraggable.length - 1];
              if (lastTh && lastTh !== source) {
                newDropTarget = lastTh;
                newDropPosition = 'after';
                newIndicatorTh = lastTh;
                newIndicatorSide = 'after';
              }
            } else if (isDraggableTh(targetTh) && targetTh !== source) {
              newDropTarget = targetTh;
              // FIX: left/right half detection — right half → insert after, left half → before
              const rect = targetTh.getBoundingClientRect();
              if (e.clientX > rect.left + rect.width / 2) {
                newDropPosition = 'after';
                newIndicatorTh = targetTh;
                newIndicatorSide = 'after';
              } else {
                newDropPosition = 'before';
                newIndicatorTh = targetTh;
                newIndicatorSide = 'before';
              }
            }

            if (dropTarget !== newDropTarget || dropPosition !== newDropPosition) {
              dropTarget = newDropTarget;
              dropPosition = newDropPosition;
              if (dropTarget) {
                showDropIndicator(newIndicatorTh, newIndicatorSide);
              } else {
                clearIndicator();
              }
            }
          };

          const onUp = async () => {
            document.removeEventListener('pointermove', onMove);
            document.removeEventListener('pointerup', onUp);
            document.removeEventListener('pointercancel', onUp);
            if (ghost) ghost.remove();
            setSourceDimmed(false);
            clearIndicator();
            if (!started || !dropTarget) return;

            const fieldPath = thFieldPath(source);
            const siblingField = thFieldPath(dropTarget);
            if (!fieldPath || !siblingField || fieldPath === siblingField) return;

            if (self.state.drop === true) {
              self.env.bus.trigger("CLEAR-MENU");
            }

            self.env.services.ui.block();
            try {
              const response = await self.rpc("/cyllo_studio/move/tree", {
                method: 'move_tree',
                model: self.props.list.model.config.resModel,
                view_id: self.env.config.viewId,
                view_type: self.env.config.viewType === 'list'
                  ? 'tree'
                  : self.env.config.viewType,
                args: [],
                kwargs: {
                  path: siblingField,
                  position: dropPosition,
                  fieldPath,
                  viewType: self.env.config.viewType,
                  view_id: self.env.config.viewId,
                  model: self.props.list.model.config.resModel,
                }
              });
              if (response) {
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                storedArray.push(response.replace(/\s+/g, ' ').trim());
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
              }
            } finally {
              self.env.services.ui.unblock();
            }
            self.action.doAction('studio_reload');
          };

          document.addEventListener('pointermove', onMove);
          document.addEventListener('pointerup', onUp);
          document.addEventListener('pointercancel', onUp);
        };

        treeEl.addEventListener('pointerdown', onColumnPointerDown);
      }

    });
  }

  /**
 * Clears hover-based highlight styles when leaving the table.
 */
  tableLeave(ev) {
    const elements = document.querySelectorAll(".border-class-list");
    elements.forEach((e) => {
      e.classList.remove("border-class-list");
    });
  }

  getColumnLabel(column) {
    const field = this.props.list.fields?.[column.name] || this.props.list._config?.fields?.[column.name];
    return (
      column.label ||
      column.string ||
      column.attrs?.string ||
      field?.string ||
      column.name
        ?.split("_")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ") ||
      ""
    );
  }

  isFalseModifier(value) {
    return value === false || value === undefined || value === null || ["", "0", "false", "False"].includes(value);
  }

  isTrueModifier(value) {
    return value === true || value === 1 || ["1", "true", "True"].includes(value);
  }

  isColumnHidden(column) {
    const modifier = column.column_invisible;
    if (this.isFalseModifier(modifier)) {
      return false;
    }
    if (this.isTrueModifier(modifier)) {
      return true;
    }
    return this.evalColumnInvisible(modifier);
  }

  /**
 * Computes active columns for rendering.
*
* @param {Object} list - List view object.
* @returns {Array} - Array of active/visible columns.
*/
  getActiveColumns(list) {
    return this.allColumns.filter((col) => {
      if (list.isGrouped && col.widget === "handle") {
        return false; // no handle column if the list is grouped
      }
      return true;
    });
  }

  /**
 * Safely evaluates column invisibility expressions.
 *
 * @param {String} columnInvisible - Expression for column visibility.
 * @returns {Boolean} - Whether the column should be invisible.
 */

  /**
   * Override: Ensure data rows render exactly the same columns as the header.
   * Standard Odoo filters out hidden optional columns, causing data cells to shift.
   */
  getColumns(record) {
    return this.state.columns;
  }

  evalColumnInvisible(columnInvisible) {
    try {
      return this.props.evalViewModifier(columnInvisible);
    } catch (e) {
      console.warn("Column invisible eval failed:", e.message, columnInvisible);

      if (columnInvisible && columnInvisible.includes("parent")) {
        return false; // keep column visible
      }
      throw e;
    }
  }
  /**
* Highlights the hovered column across the entire table.
*
* @param {Event} ev - Mouseover event.
*/
  onMouseHover(ev) {
    const elements = document.querySelectorAll(".border-class-list");
    elements.forEach((e) => {
      e.classList.remove("border-class-list");
    });

    const currentElement = ev.target.closest("th") || ev.target.closest("td");
    const headers = ev.target
      .closest("tr")
      .querySelectorAll(currentElement.tagName);
    const colIndex = Array.from(headers).indexOf(currentElement);
    const rows = document.querySelectorAll("tr");
    rows.forEach((row) => {
      let cells = row.querySelectorAll("td");
      cells = cells.length ? cells : row.querySelectorAll("th");
      if (
        cells[colIndex] &&
        parseInt(cells[colIndex].getAttribute("colspan") || 0) <= 1
      ) {
        cells[colIndex].classList.add("border-class-list");
      }
    });
  }

  /**
   * Triggers FIELDS_DETAILS event for the selected column.
   * Ensures no concurrent edit is active before opening the sidebar.
   *
   * @param {Event} ev - Click event.
   * @param {Object} column - Selected column metadata.
   */
  listFieldDetails(ev, column) {
    let Edit = sessionStorage.getItem("newListElement");
    if (Edit) {
      return this.notification.add({
        title: "Validation Error",
        message: "Edit is in progress.",
        description: "Please save or cancel the current process.",
        type: "notification_panel",
        notificationType: "warning",
        animation: false,
      });
    }

    // Persistent highlight on the selected column so the active column
    // stays identifiable even when not hovering it.
    const current = ev.target.closest("th") || ev.target.closest("td");
    if (current) {
      document.querySelectorAll(".cy-active-col").forEach((e) =>
        e.classList.remove("cy-active-col")
      );
      const headers = current.closest("tr").querySelectorAll(current.tagName);
      const colIndex = Array.from(headers).indexOf(current);
      document.querySelectorAll(".o_list_table tr").forEach((row) => {
        let cells = row.querySelectorAll("td");
        cells = cells.length ? cells : row.querySelectorAll("th");
        if (
          cells[colIndex] &&
          parseInt(cells[colIndex].getAttribute("colspan") || 0) <= 1
        ) {
          cells[colIndex].classList.add("cy-active-col");
        }
      });
    }

    const fieldType = this.props.list._config.fields[column.name]?.type || "";
    const relational_fields = this.props.list._config.fields[column.name]?.relation || "";
    this.env.bus.trigger("FIELDS_DETAILS", {
      mode: column.attrs || {},
      name: column.name || "",
      label: this.getColumnLabel(column),
      widget: column.widget || "",
      options: column.options || "",
      fieldType: fieldType || "",
      context: column?.context || "",
      related_model: relational_fields || "",
      type: "Properties",
      edit: true,
      cy_path: column?.attrs["cy-xpath"],
      help: column.help || "",
      placeholder: column.attrs["placeholder"] || "",
      dynamic_placeholder: column.attrs["dynamic_placeholder"] || "",
      column_invisible: column.column_invisible || 'false',
      invisible: column.invisible || 'false',
      readonly: column.readonly || 'false',
      required: column.required || 'false',
    });
  }

  /**
   * Creates a placeholder "new field" column in the list.
   * Used when the user initiates adding a new field from the UI.
   *
   * @param {Event} ev - Click event on add-field trigger.
   */
  itemOnClick(ev) {
    if (sessionStorage.getItem("newListElement")) {
      return this.notification.add({
        title: "Validation Error",
        message: "Edit is in progress.",
        description: "Please save or cancel the current process.",
        type: "notification_panel",
        notificationType: "warning",
        animation: false,
      });
    }
    sessionStorage.setItem("newListElement", true);

    const newth = document.createElement('th');
    const newtd = document.createElement('td');

    newth.setAttribute('data-tooltip-delay', '1000');

    newth.setAttribute('tabindex', '-1');
    newtd.setAttribute('tabindex', '-1');
    newth.setAttribute('data-name', 'tax_id');
    newth.className = 'add-fields align-middle cursor-default o_many2many_tags_cell opacity-trigger-hover';
    newth.style.width = '150px';
    newth.innerHTML = `
            <div class="d-flex">
                <span class="d-block min-w-0 text-truncate flex-grow-1">Select Field</span>
                <i class="d-none fa-angle-down opacity-0 opacity-75-hover"></i>
            </div>
            <span class="o_resize position-absolute top-0 end-0 bottom-0 ps-1 bg-black-25 opacity-0 opacity-50-hover z-index-1"></span>
        `;
    let targetContainer = ev.target.parentElement;
    let specificElement = ev.target
    let parentXpath = '/tree'
    const viewArch = this.env.config.viewArch.attributes
    let truncatedPath = ""
    const path = ev.target.parentElement.parentElement.children[0].getAttribute('cy-xpath');
    if (targetContainer) {
      this.env.bus.trigger("FIELDS_DETAILS", {
        type: "Properties",
        create: true,
        cy_path: '/tree',
      })
    }
  }
  /**
  * Sets default column widths based on their type (absolute/relative).
  * Handles proportional distribution for relative widths.
  */
  setDefaultColumnWidths() {
    const widths = this.state.columns.map((col) =>
      this.calculateColumnWidth(col)
    );
    const sumOfRelativeWidths = widths
      .filter(({ type }) => type === "relative")
      .reduce((sum, { value }) => sum + value, 0);

    const columnOffset = this.hasSelectors ? 2 : 1;
    widths.forEach(({ type, value }, i) => {
      const headerEl = this.tableRef.el.querySelector(
        `th:nth-child(${i + columnOffset})`
      );
      if (type === "absolute" && headerEl) {
        if (this.isEmpty) {
          headerEl.style.width = value;
        } else {
          headerEl.style.minWidth = value;
        }
      } else if (type === "relative" && this.isEmpty) {
        headerEl.style.width = `${((value / sumOfRelativeWidths) * 100).toFixed(
          2
        )}%`;
      }
    });
  }
  get getEmptyRowIds() {
    return [];
  }

  getCellClass(column, record) {
    let classes;
    try {
      classes = super.getCellClass(...arguments);
    } catch (e) {
      classes = '';
    }
    if (column.widget == "handle") {
      classes += ' pe-none';
    }
    return classes;
  }
}
CylloListRenderer.template = "cyllo_studio.CylloListRenderer";
CylloListRenderer.rowsTemplate = "cyllo_studio.CylloListRenderer.Rows";
CylloListRenderer.recordRowTemplate =
  "cyllo_studio.CylloListRenderer.RecordRow";
CylloListRenderer.groupRowTemplate =
  "cyllo_studio.CylloListRenderer.GroupRow";

CylloListRenderer.components = {
  ...listView.Renderer.components,
};
