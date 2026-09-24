/** @odoo-module **/

/**
 * RibbonDialog Component
 *
 * Provides a dialog interface for managing Kanban ribbon elements in Studio.
 * Supports editing text, colors, visibility conditions, preview updates, and saving
 * ribbon definitions to the backend. Also integrates with Expression Editor for domain logic.
 *
 * Key features:
 *  - Parse ribbon DOM elements into editable state objects
 *  - Inline editing of ribbon labels and colors
 *  - Manage visibility conditions via domain expressions
 *  - Live preview updates for selected ribbon
 *  - Persist changes via RPC calls with undo/redo support
 */
import { Dialog } from "@web/core/dialog/dialog";
const { Component, onWillStart, useState, useEffect, onMounted, useRef } = owl;
import {useService, useOwnedDialogs} from "@web/core/utils/hooks";
import { ExpressionEditorDialog } from "@web/core/expression_editor_dialog/expression_editor_dialog";

export class RibbonDialog extends Component {
    static template = 'cyllo_studio.RibbonDialog';
    static components = {
        Dialog
    }
    static props = {
        ribbonElement: { type: Array, optional: true },
        viewDetails: { type: Object },
        close: { type: Function },
        '*': true,
    }
    setup(){
        this.state = useState({
            ribbons: [],
            selectedIndex: 0,
            hasEdit: false,
            showDropdown: false,
        })
        this.addDialog = useOwnedDialogs();
        this.previewRef = useRef('PreviewRef')
        onMounted(() => {
            this.state.ribbons = Array.from(this.props.ribbonElement || []).map(this.getElementDetails.bind(this));
            const element = this.state.ribbons[this.state.selectedIndex].element;
            this.addPreviewStyle()
        })

        this.rpc = useService('rpc')
        this.action = useService('action')

    }

    // Reflect current selection in the live kanban record DOM
    applyRibbonStateToDOM(ribbon){
        try {
            const element = ribbon.element;
            if (!element) return;
            // Ensure only the selected ribbon is visible within this record
            const kanbanRecord = element.closest('.oe_kanban_record, .o_kanban_record, [data-id], .kanban-record');
            if (kanbanRecord) {
                const allRibbons = kanbanRecord.querySelectorAll('[data-ribbon], .ribbon');
                allRibbons.forEach((rb) => {
                    if (rb === element) {
                        rb.style.display = '';
                    } else {
                        rb.style.display = 'none';
                    }
                });
            }
            const children = Array.from(element.children || []);
            const firstChild = children.find((c) => (c.textContent || '').trim().length > 0) || children[0];
            if (firstChild) {
                if (ribbon.firstElementContent != null) {
                    firstChild.textContent = ribbon.firstElementContent;
                }
                if (ribbon.color) {
                    Array.from(firstChild.classList).forEach((cls) => {
                        if (cls.startsWith('text-bg-')) firstChild.classList.remove(cls);
                    });
                    firstChild.classList.add(ribbon.color);
                }
            }
            if (ribbon.invisible != null) {
                element.setAttribute('data-invisible', ribbon.invisible);
            }
        } catch(e) {
            console.warn('Failed to apply ribbon state to DOM:', e);
        }
    }

    get colors(){
        return {
            'text-bg-primary': 'Primary',
            'text-bg-secondary': 'Secondary',
            'text-bg-success': 'Success',
            'text-bg-info': 'Info',
            'text-bg-warning': 'Warning',
            'text-bg-danger': 'Danger'
        }
    }

     /**
     * Check if an element or its children have conditional rendering attributes
     * (`t-if`, `t-else`, `t-elif`).
     *
     * @param {HTMLElement} element - Ribbon DOM element
     * @returns {Boolean} - True if conditions are present
     */
    hasConditionAttributes(element){
        const conditionAttributes = ['data-t-if', 'data-t-else', 'data-t-elif'];

        // Check the element itself
        for (let attr of conditionAttributes) {
            if (element.hasAttribute(attr)) {
                return true;
            }
        }

        // Check the children
        for (let child of element.children) {
            for (let attr of conditionAttributes) {
                if (child.hasAttribute(attr)) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * Parse a DOM element into a structured ribbon object.
     * Extracts text, xpath, classes, color, and condition flags.
     *
     * @param {HTMLElement} element - Ribbon DOM element
     * @param {Number} index - Index of the ribbon
     * @returns {Object} Parsed ribbon definition
     */
   getElementDetails(element, index) {
       const children = element.children;
       const hasConditionAttributes = this.hasConditionAttributes(element);
       let firstElementContent = null, firstElementPath = null, firstElementClass = null, color = null;
       // Loop through children to find the first valid one with content
       for (let i = 0; i < children.length; i++) {
           const child = children[i];
           const childText = child.textContent.trim();
           if (childText) {
               firstElementContent = childText;
               firstElementPath = child.getAttribute('cy-xpath');
               firstElementClass = child.className;
               color = Array.from(child.classList).find(cls => cls.startsWith('text-bg-'));
               break;
           }
       }
       return {
           arrayIndex: index,
           path: element.getAttribute('cy-xpath'),
           invisible: element.getAttribute('data-invisible'),
           hasMultipleChildElement: children.length > 1,
           class: firstElementClass,
           color,
           firstElementContent,
           firstElementPath,
               hasDelete: false,
               hasEdit: false,
               hasConditionAttributes,
               element
           };
   }

    onDomainRadioClick({target}){
        this.state.ribbons[this.state.selectedIndex].hasEdit = true
        this.state.ribbons[this.state.selectedIndex].invisible = target.checked ? 'True' : 'False'
        this.applyRibbonStateToDOM(this.state.ribbons[this.state.selectedIndex])
    }

    handleSelectColor(color){
        this.state.ribbons[this.state.selectedIndex].hasEdit = true
        this.state.ribbons[this.state.selectedIndex].color = color
        this.state.showDropdown = false
        this.addPreviewStyle()
        this.applyRibbonStateToDOM(this.state.ribbons[this.state.selectedIndex])
    }

    onChangeText(value){
        this.state.ribbons[this.state.selectedIndex].hasEdit = true
        this.state.ribbons[this.state.selectedIndex].firstElementContent = value
        this.addPreviewStyle()
        this.applyRibbonStateToDOM(this.state.ribbons[this.state.selectedIndex])
    }

    onDomainClick() {
        this.state.ribbons[this.state.selectedIndex].hasEdit = true

        const fieldsWithNames = {};
        const sourceFields = this.props.viewDetails.active_fields || {};
        for (const [key, value] of Object.entries(sourceFields)) {
            fieldsWithNames[key] = { ...value, name: key };
        }

        this.addDialog(ExpressionEditorDialog, {
          resModel: this.props.viewDetails.model,
          fields: fieldsWithNames,
          expression: this.state.ribbons[this.state.selectedIndex].invisible,
          onConfirm: (expression) => this.state.ribbons[this.state.selectedIndex].invisible = expression,
        });
    }

    /**
     * Apply updated text and color styles to the preview element.
     */
    addPreviewStyle(){
        const ribbon = this.state.ribbons[this.state.selectedIndex]
        this.previewRef.el.innerHTML = ribbon.firstElementContent
        this.previewRef.el.className = ribbon.color
    }

    handleRibbon(index){
        this.state.selectedIndex = index
        const element = this.state.ribbons[index].element;
        this.state.ribbons[index].hasEdit = true
        this.addPreviewStyle()
        this.applyRibbonStateToDOM(this.state.ribbons[index])
    }

    handleDelete(index){
        this.state.ribbons[index].hasDelete = true
    }

    handleEdit(ribbon){
        this.state.hasEdit = true
        this.state.selectedIndex = ribbon.arrayIndex
        this.addPreviewStyle()
    }

    handleDone(){
        if(this.state.ribbons[this.state.selectedIndex].firstElementContent){
             this.state.hasEdit = false
        }
        else{
            return this.action.doAction({
               'type': 'ir.actions.client',
               'tag': 'display_notification',
               'params': {
                   'message': 'The label should not be empty',
                   'type': 'warning',
                   'sticky': false,
               }
            })
        }
    }
    /**
     * Normalize and filter ribbon objects before persisting.
     *
     * @param {Array} ribbons - Current ribbon state objects
     * @returns {Array} Cleaned array ready for RPC
     */

        filterAndModifyArray(ribbons) {
            return ribbons.map((ribbon, idx) => ({
                path: ribbon.path || "",
                child_xpath: ribbon.firstElementPath || "",
                firstElementContent: ribbon.firstElementContent || "",
                color: ribbon.color || "text-bg-primary",
                invisible: ribbon.invisible != null ? ribbon.invisible : 'False', // preserve expression
                hasEdit: !!ribbon.hasEdit,
                hasDelete: !!ribbon.hasDelete,
                selected: idx === this.state.selectedIndex,
            }));
        }



async handelSave() {
    try {
        // Don't manipulate DOM here - let the backend handle it
        // The preview updates in applyRibbonStateToDOM are enough

        // Prepare ribbons data for backend
        const ribbonsToSave = this.filterAndModifyArray(this.state.ribbons);
        const viewType = this.props.viewDetails.viewType;

        // Determine the correct endpoint
        const endpoint = viewType === "form"
            ? "cyllo_studio/form/update/ribbons"
            : "cyllo_studio/kanban/update/ribbons";

        // Block UI during save
        this.env.services.ui.block();

        const response = await this.rpc(endpoint, {
            ...this.props.viewDetails,
            ribbons: ribbonsToSave,
        });
        if (response) {
            // Update undo/redo history
            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
            let cleanedStr = response.replace(/\s+/g, ' ').trim();
            storedArray.push(cleanedStr);
            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
            sessionStorage.setItem('ReDO', JSON.stringify([]));
        }

        // Store the selected ribbon's path for restoration after reload
        try {
            const sel = this.state.ribbons[this.state.selectedIndex];
            if (sel && sel.path) {
                sessionStorage.setItem('SelectedRibbonXPath', sel.path);
            }
        } catch (e) {
            console.warn('Failed to store selected ribbon:', e);
        }

        this.env.services.ui.unblock();

        // Close dialog before reload
        this.props.close();

        // Reload the studio view
        this.action.doAction('studio_reload');

    } catch (error) {
        console.error('Failed to save ribbons:', error);
        this.env.services.ui.unblock();
        this.action.doAction({
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Failed to save ribbons. Please try again.',
                'type': 'danger',
                'sticky': false,
            }
        });
    }
}

    /**
     * Validate ribbon edits.
     * Prevents saving empty labels by showing a warning notification.
     */
    handelDiscard(){
        this.props.close()
    }
}