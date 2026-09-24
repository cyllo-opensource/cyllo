/** @odoo-module **/

/**
 * TextProperties Component
 *
 * Manages the properties of a Kanban text/span element in Studio.
 * Allows editing text content, styles (bold, italic, underline),
 * visibility, and domain conditions.
 * Supports auto-save with undo/redo integration.
 */
import {
    useService,
    useOwnedDialogs
} from "@web/core/utils/hooks";
import {
    _t
} from "@web/core/l10n/translation";
const {
    Component,
    useState,
    useRef,
    useEffect,
    onMounted,
    onWillUnmount,
    onWillDestroy,
    onWillUpdateProps,
    useExternalListener,
} = owl;
import {
    handleUndoRedo
} from "@cyllo_studio/js/utils/undo_redo_utils";
import {
    CylloExpressionEditorDialog
} from "@cyllo_studio/js/view_editor/components/expression_editor_dialog/expression_editor_dialog";

export class TextProperties extends Component {
    static template = 'cyllo_studio.TextProperties'

    /**
     * Initializes component state and services.
     * Tracks text content, formatting styles, visibility, and validation.
     */
    setup() {
        this.rpc = useService('rpc');
        this.action = useService('action');
        this.notification = useService('effect');
        this.addDialog = useOwnedDialogs();

        this.state = useState({
            string: '',
            isBold: false,
            isItalic: false,
            isUnderline: false,
            is_edit: false,
            invisible: 'false',
            validation: true,
            path: null,
        });

        this._autoSaving = false;
        this._autoSavePending = false;
        this.warningCount = 0;
        this.currentViewType = this.props?.viewDetails?.viewType || null;
        this.lastPath = null;

        const isDOMElement = (el) => el instanceof Element;

        const getCleanString = (el, fallback) => {
            let value = '';
            if (isDOMElement(el)) value = el.textContent?.trim() || '';
            else if (fallback) value = fallback.trim();

            if (value === 'Text' || value === 'Label') value = '';
            return value;
        };

        this.updateFormattingFromElement = (el, isEdit = false) => {
            if (!isDOMElement(el)) return;
            this.state.isBold = this.isElementBold(el);
            this.state.isItalic = this.isElementItalic(el);
            this.state.isUnderline = this.isElementUnderlined(el);
            this.state.path = el.getAttribute('cy-xpath') || null;

            // Only read string from element if we're editing
            if (isEdit) {
                this.state.string = getCleanString(el, '');
            } else {
                this.state.string = ''; // Keep empty for new elements
            }

            this.lastPath = this.state.path;
        };

        /**
         * === MOUNT: initialize state on load ===
         */
        onMounted(() => {
            const viewType = this.props?.viewDetails?.viewType || 'form';
            const spanProps = this.props?.span_properties || {};
            const el = spanProps?.element || this.props?.element || null;
            const isEdit = spanProps?.is_edit || this.props?.is_edit || !!(spanProps?.string);

            if (el instanceof Element) {
                this.updateFormattingFromElement(el, isEdit);
            } else {
                this.state.isBold = spanProps?.bold ?? !isEdit;
                this.state.isItalic = spanProps?.italic ?? false;
                this.state.isUnderline = spanProps?.underline ?? false;
                if (viewType === 'kanban') {
                    this.state.string = getCleanString(null, spanProps?.string || '');
                } else {
                    this.state.string = getCleanString(null, this.props?.string || '');
                }
            }

            this.state.is_edit = isEdit;
            this.state.invisible = spanProps?.invisible || this.props?.invisible || 'false';
        });
        onWillUpdateProps((nextPropsRaw) => {
            const nextProps = nextPropsRaw?.props || nextPropsRaw;
            const nextViewType = nextProps?.viewDetails?.viewType || this.currentViewType;
            const nextSpanProps = nextProps?.span_properties || {};
            const nextEl = nextSpanProps?.element || nextProps?.element || null;
            const nextIsEdit = nextSpanProps?.is_edit || nextProps?.is_edit || !!(nextSpanProps?.string);
            const nextPath =
                nextEl?.getAttribute('cy-xpath') ||
                nextSpanProps?.properties?.elementInfo?.path ||
                nextProps?.path ||
                nextProps?.properties?.elementInfo?.path ||
                null;

            const viewChanged = nextViewType && nextViewType !== this.currentViewType;
            const pathChanged = nextPath && this.lastPath && nextPath !== this.lastPath;
            const isNewSibling = nextProps?.sibling === true ||
                (!nextIsEdit && pathChanged) ||
                (nextPath && !this.lastPath);

            if (viewChanged || isNewSibling) {
                Object.assign(this.state, {
                    string: '', // always reset fully on view change or new addition
                    isBold: !nextIsEdit,
                    isItalic: false,
                    isUnderline: false,
                    is_edit: false,
                    invisible: nextSpanProps?.invisible || nextProps?.invisible || 'false',
                    path: nextPath,
                });

                if (nextEl instanceof Element) {
                    this.updateFormattingFromElement(nextEl, nextIsEdit);
                }

                this.lastPath = nextPath;
                this.currentViewType = nextViewType;
                return;
            }

            // Only update existing edit mode
            if (nextEl instanceof Element) {
                this.updateFormattingFromElement(nextEl, nextIsEdit);
            } else {
                if (nextSpanProps?.bold !== undefined) this.state.isBold = nextSpanProps.bold;
                if (nextSpanProps?.italic !== undefined) this.state.isItalic = nextSpanProps.italic;
                if (nextSpanProps?.underline !== undefined) this.state.isUnderline = nextSpanProps.underline;
                if (nextViewType === 'kanban') {
                    if (nextSpanProps?.string !== undefined) this.state.string = nextSpanProps.string;
                } else {
                    if (nextProps?.string !== undefined) this.state.string = nextProps.string;
                }
            }

            this.state.is_edit = nextIsEdit;
            this.state.invisible = nextSpanProps?.invisible || nextProps?.invisible || 'false';
            this.state.path = nextPath;
            this.lastPath = nextPath;
            this.currentViewType = nextViewType;
        });

    }
    /**
     * Toggles the text formatting style of the element.
     *
     * @param {string} style - One of 'bold', 'italic', 'underline'
     */
    handleStyle(style) {
        const element = this.props.span_properties?.element || this.props.element;
        if (!element) return;

        if (style === 'bold') this.state.isBold = !this.state.isBold;
        if (style === 'italic') this.state.isItalic = !this.state.isItalic;
        if (style === 'underline') this.state.isUnderline = !this.state.isUnderline;

        element.classList.toggle('fw-bold', this.state.isBold);
        element.classList.toggle('fw-normal', !this.state.isBold);

        element.classList.toggle('fst-italic', this.state.isItalic);
        element.classList.toggle('fst-normal', !this.state.isItalic);

        element.classList.toggle('text-decoration-underline', this.state.isUnderline);
        element.classList.toggle('text-decoration-none', !this.state.isUnderline);

        this.autoSave();
    }

    /**
     * Updates the text content of the element.
     *
     * @param {Event} event - Input change event
     */
    handleLabelChange({ target }) {
        this.state.string = target.value;
        const element = this.props.span_properties?.element || this.props.element;
        if (element) {
            element.textContent = target.value;
        }
    }

    isElementBold(element) {
        if (element?.classList?.contains('fw-normal')) {
            return false;
        }
        if (element?.classList?.contains('fw-bold')) {
            return true;
        }
        const fontWeight = element ? window.getComputedStyle(element)?.fontWeight : '';
        return fontWeight === 'bold' || parseInt(fontWeight) >= 500;
    }

    isElementItalic(element) {
        if (element?.classList?.contains('fst-normal')) {
            return false;
        }
        if (element?.classList?.contains('fst-italic')) {
            return true;
        }
        const fontStyle = element ? window.getComputedStyle(element)?.fontStyle : '';
        return fontStyle === 'italic' || fontStyle === 'oblique';
    }

    isElementUnderlined(element) {
        if (element?.classList?.contains('text-decoration-none')) {
            return false;
        }
        if (element?.classList?.contains('text-decoration-underline')) {
            return true;
        }
        const textDecoration = element ? window.getComputedStyle(element)?.textDecorationLine || window.getComputedStyle(element)?.textDecoration : '';
        return textDecoration.includes('underline');
    }

    autoSave() {
        if (this._autoSaving) { this._autoSavePending = true; return; }
        this._autoSaving = true;
        this.doSave().finally(() => {
            this._autoSaving = false;
            if (this._autoSavePending) { this._autoSavePending = false; this.autoSave(); }
        });
    }

    async doSave() {
        if (!this.state.string) {
            return this.notification.add({
                title: _t("Validation Error"),
                message: "Unable to save the text.",
                description: "Please provide a text to save",
                type: "notification_panel",
                notificationType: "warning",
            });
        }
        const element = this.props.span_properties?.element || this.props.element;
        let existingClasses = [];
        if (element && element.classList) {
            existingClasses = Array.from(element.classList).filter(
                (cls) =>
                    cls !== 'fw-bold' &&
                    cls !== 'fw-normal' &&
                    cls !== 'fst-italic' &&
                    cls !== 'fst-normal' &&
                    cls !== 'text-decoration-underline' &&
                    cls !== 'text-decoration-none' &&
                    cls !== 'border-class' &&
                    cls !== 'cy-studio-text'
            );
        }
        let updatedClassList = 'cy-studio-text';
        if (existingClasses.length > 0) {
            updatedClassList += ' ' + existingClasses.join(' ');
        }
        if (this.state.isBold) updatedClassList += ' fw-bold';
        else updatedClassList += ' fw-normal';

        if (this.state.isItalic) updatedClassList += ' fst-italic';
        else updatedClassList += ' fst-normal';

        if (this.state.isUnderline) updatedClassList += ' text-decoration-underline';
        else updatedClassList += ' text-decoration-none';

        this.env.services.ui.block();
        try {
            if (this.state.is_edit) {
                const response = await this.rpc("/cyllo_studio/kanban/update/text", {
                    path: this.props.span_properties?.element.getAttribute("cy-xpath") || this.props.path,
                    view_id: this.props.span_properties?.view_id || this.props.viewDetails.viewId,
                    model: this.props.span_properties?.model,
                    view_type: this.props.span_properties?.view_type || this.props.viewDetails.viewType,
                    ...this.props.viewDetails,
                    properties: {
                        string: this.state.string || '',
                        class_names: updatedClassList,
                    },
                });
                if (response) {
                    const storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                    storedArray.push(response.replace(/\s+/g, ' ').trim());
                    sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                    sessionStorage.setItem('ReDO', JSON.stringify([]));
                }
            } else {
                const addPath = this.props.viewDetails.viewType === "kanban"
                    ? (this.props.span_properties?.properties?.elementInfo?.path || this.props.path)
                    : (this.props.properties?.elementInfo?.path || this.props.path);
                const addPosition = this.props.viewDetails.viewType === "kanban"
                    ? (this.props.span_properties?.properties?.elementInfo?.position || 'inside')
                    : (this.props.properties?.elementInfo?.position || 'inside');
                const response = await this.rpc("/cyllo_studio/kanban/add/text", {
                    path: addPath,
                    position: addPosition,
                    ...this.props.viewDetails,
                    properties: {
                        string: this.state.string || '',
                        class_names: updatedClassList,
                        sibling: this.props.sibling || false,
                        item_type: this.props.item_type || "",
                        field_info: this.props.field_info || {},
                        invisible: this.state.invisible,
                    },
                });
                if (response) {
                    const storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                    storedArray.push(response.replace(/\s+/g, ' ').trim());
                    sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                    sessionStorage.setItem('ReDO', JSON.stringify([]));
                }
            }
            // this.env.bus.trigger("CLEAR-MENU");
            this.env.bus.trigger("CLEAR-CACHES");
            this.notification.add({
                title: _t("Success"),
                message: "Text saved.",
                type: "notification_panel",
                notificationType: "success",
            });
        } finally {
            this.env.services.ui.unblock();
        }
    }
    /**
    * Cancels the text edit and reloads the view.
    */
    cancelRibbon() {
        this.action.doAction('studio_reload');
    }
    /**
     * Toggles the 'invisible' property of the text element.
     *
     * @param {Event} target - Radio click event
     */
    onDomainRadioClick({ target }) {
        this.state.invisible = (this.state.invisible === 'true') ? 'false' : 'true';
        this.autoSave();
    }

    /**
    * Opens a dialog to edit the domain expression for the text element.
    *
    * @param {Event} target - Click event
    */
    onDomainClick({ target }) {
        this.state.validation = false
        let button = target.closest(".cy-basedOn");
        let attribute = button.getAttribute("data-attribute");
        this.addDialog(CylloExpressionEditorDialog, {
            resModel: this.props.viewDetails.model,
            fields: this.props.viewDetails.allFields,
            // Ensure that if this.state[attribute] is falsy, it defaults to a valid expression
            expression: this.state[attribute] || 'true',
            setValidation: () => {
                this.state.validation = true
            },
            onConfirm: (expression) => {
                this.state[attribute] = expression;
                this.autoSave();
            }
        });
    }
    async removeSpan() {
        this.env.services.ui.block();
        try {
            const response = await this.rpc("cyllo_studio/form/remove/text_element", {
                model: this.props.viewDetails.model,
                view_type: this.props.viewDetails.viewType,
                view_id: this.props.viewDetails.viewId,
                path: this.props.span_properties?.element.getAttribute("cy-xpath") || this.props.path
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
        this.env.bus.trigger("CLEAR-MENU");
        this.action.doAction("studio_reload");
        this.env.bus.trigger('resetProperties');
    }
}
