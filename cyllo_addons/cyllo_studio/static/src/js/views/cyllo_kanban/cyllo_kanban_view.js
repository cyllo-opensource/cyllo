/** @odoo-module */

/**
 * CylloKanbanView
 *
 * This module defines a customized Kanban view for Cyllo Studio,
 * extending Odoo's default Kanban view functionality.
 *
 * Features:
 * 1. Custom Renderer:
 *    - Uses `CylloKanbanRenderer` to render Kanban cards with enhanced
 *      Cyllo Studio features such as ribbon integration, preview dialogs,
 *      and custom field handling.
 *
 * 2. Custom Controller:
 *    - Uses `CylloKanbanController` to manage RPC calls, bus events,
 *      and lifecycle handling for Kanban view interactions.
 *
 * 3. Registration:
 *    - Registers a new view type "n_kanban" for internal use.
 *    - Overrides the default "kanban" view to use CylloKanbanView,
 *      forcing the registry update to ensure the custom view is applied.
 *
 * Purpose:
 * Provides an interactive, fully customized Kanban editing experience
 * for Cyllo Studio users, maintaining full compatibility with Odoo's
 * Kanban infrastructure.
 */
import {registry} from "@web/core/registry";
import {CylloKanbanRenderer} from "./cyllo_kanban_renderer";
import {CylloKanbanController} from "./cyllo_kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";


export const CylloKanbanView = {
    ...kanbanView,
    Renderer: CylloKanbanRenderer,
    Controller: CylloKanbanController,
};

registry.category("views").add("n_kanban", kanbanView);
registry.category("views").add("kanban", CylloKanbanView, {force: true});

