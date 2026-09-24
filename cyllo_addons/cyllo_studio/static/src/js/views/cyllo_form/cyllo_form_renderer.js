/** @odoo-module **/

/**
 * CylloFormRenderer
 *
 * Extended FormRenderer for Odoo Studio (Cyllo Edition).
 * Handles custom fields, notebooks, status bars, avatars, and inner groups.
 * Provides enhanced click handling for form spans and triggers events with field details.
 */

/**
 * setup
 *
 * Initializes the renderer and triggers the "FORM_DETAILS" event after the component is mounted.
 * Sends information about the current model, view, active fields, and view type to the bus.
 */
import { FormRenderer } from "@web/views/form/form_renderer";
import { useService } from "@web/core/utils/hooks";
import { RibbonDialog } from "@cyllo_studio/js/view_editor/kanban/ribbon_dialog";

const { onMounted } = owl;
import { StatusBar } from "@cyllo_studio/js/views/cyllo_form/status_bar/statusbar";
import { ChatterComponent } from "@cyllo_studio/js/views/cyllo_form/chatter/chatter_component";
import { CylloStatusBarButtons } from "@cyllo_base/js/status_bar_buttons";
import { CylloInnerGroup } from "@cyllo_studio/js/views/cyllo_form/form_group/form_group";
import { CylloField } from "@cyllo_studio/js/view_editor/fields/field";
import { CylloNotebook } from "@cyllo_studio/js/views/cyllo_form/notebook/notebook";
import { ButtonBox } from "@web/views/form/button_box/button_box";
import { AvatarComponent } from "@cyllo_studio/js/views/cyllo_form/avatar/avatar";
import { CylloFormLabel } from "@cyllo_studio/js/views/cyllo_form/form_label/form_label";


export class CylloFormRenderer extends FormRenderer {
    setup() {
        super.setup();
        this.showInvisible = this.props.showInvisible === true;
        this.dialogService = useService("dialog");

        onMounted(() => {
            this.env.bus.trigger("FORM_DETAILS", {
                mode: this.props.archInfo.activeActions,
                model: this.env.model.config.resModel,
                viewId: this.env.config.viewId,
                allFields: this.env.model.config.fields,
                activeFields: this.env.model.config.activeFields,
                viewType: "form",
            });
        });
    }

    /**
     * onRibbonClick
     *
     * Opens the RibbonDialog wizard for the clicked ribbon. The handler is
     * compiled onto the ribbon container itself (see CylloFormCompiler), so it
     * stays available for the whole lifetime of the rendered form — regardless
     * of whether the Studio sidebar is closed, showing a properties panel, or
     * has just been re-created by a page refresh.
     *
     * @param {Event} ev - Click event originating inside the ribbon.
     */
    onRibbonClick(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const ribbon =
            ev.target.closest?.('div.ribbon[cy-xpath]') || ev.currentTarget;
        if (!ribbon?.getAttribute('cy-xpath')) {
            return;
        }
        const allFields = this.env.model.config.fields;
        const fields = Object.entries(allFields || {}).map(([fieldName, field]) => ({
            value: fieldName,
            label: field.string,
        }));
        this.dialogService.add(RibbonDialog, {
            fields,
            ribbonElement: Array.from(document.querySelectorAll('div.ribbon[cy-xpath]')),
            viewDetails: {
                viewId: this.env.config.viewId,
                viewType: "form",
                model: this.env.model.config.resModel,
                active_fields: allFields,
                ribbonPath: ribbon.getAttribute('cy-xpath'),
            },
        });
    }

    /**
     * onSpanClick
     *
     * Handles click events on <span> elements in the form.
     * Removes previous border highlights and adds a border to the clicked element.
     * Triggers the "SpanDetails" event with information about the clicked field.
     *
     * @param {Event} param0 - The click event object containing the target span.
     * @param {Boolean} invisible - Indicates if the field is invisible.
     */
    onSpanClick({ target }, invisible) {
        const elements = document.querySelectorAll(".border-class");
        elements.forEach((e) => {
            e.classList.remove("border-class");
        });
        const classNames = target.getAttribute('class') || ''
        const updatedClassNames = classNames
            .split(' ')
            .filter(cls => cls !== 'cy-studio-striped')
            .join(' ');

        target.classList.add("border-class")
        this.env.bus.trigger('SpanDetails', {
            model: this.env.model.config.resModel,
            viewId: this.env.config.viewId,
            allFields: this.env.model.config.fields,
            path: target.getAttribute('cy-xpath'),
            string: target.textContent || '',
            classNames: updatedClassNames,
            is_edit: true,
            element: target.target,
        })
    }

    handleSelectSpan(el) {
        el.stopPropagation();
        this.env.bus.trigger('SPAN_DETAILS', {
            string: el.target.textContent,
            bold: el.target.classList.contains("fw-bold"),
            italic: el.target.classList.contains("fst-italic"),
            underline: el.target.classList.contains("text-decoration-underline"),
            is_edit: true,
            element: el.target,
            view_id: this.env.config.viewId,
            model: this.env.model.config.resModel,
            view_type: this.env.config.viewType,
            type: "text",
            path: el.target.getAttribute('cy-xpath')
        });
    }
}

CylloFormRenderer.components = {
    ...FormRenderer.components,
    StatusBar: StatusBar,
    ChatterComponent,
    StatusBarButtons: CylloStatusBarButtons,
    AvatarComponent,
    ButtonBox,
    InnerGroup: CylloInnerGroup,
    Field: CylloField,
    Notebook: CylloNotebook,
    FormLabel: CylloFormLabel,


};