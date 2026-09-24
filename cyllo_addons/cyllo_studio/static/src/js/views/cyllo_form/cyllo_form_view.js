/** @odoo-module **/

/**
 * CylloFormView
 *
 * Custom Form View for Odoo Studio (Cyllo Edition).
 * Integrates the following custom components:
 *   - Renderer: CylloFormRenderer (enhanced form rendering with notebooks, status bars, avatars, and fields)
 *   - Compiler: CylloFormCompiler (compiles the form view architecture)
 *   - Controller: CylloFormController (handles form behavior, drag-and-drop, and X2Many fields)
 *
 * Registers this custom form view in the Odoo view registry,
 * overriding the default "form" view type with Cyllo enhancements.
 */
import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";
import { CylloFormRenderer } from "./cyllo_form_renderer";
import { CylloFormCompiler } from "./view_compiler";
import { CylloFormController } from "./cyllo_form_controller";


export const CylloFormView = {
    ...formView,
    Renderer: CylloFormRenderer,
    Compiler: CylloFormCompiler,
    Controller: CylloFormController,

};

registry.category("views").add("form", CylloFormView, { force: true });
