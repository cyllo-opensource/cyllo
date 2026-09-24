/** @odoo-module */

/**
 * CylloListView
 *
 * Custom List view integration for Cyllo Studio.
 * Extends the default Odoo list view to provide enhanced capabilities:
 *
 * Features:
 * 1. Renderer:
 *    - Uses `CylloListRenderer` for dynamic field editing, drag-and-drop reordering,
 *      session-based visibility, and column hover effects.
 *
 * 2. ArchParser:
 *    - Uses `CylloListArchParser` for parsing list view XML architecture.
 *    - Supports custom field attributes, optional visibility, button groups, and
 *      widget handling.
 *
 * 3. Registry Integration:
 *    - Registers "list" with `CylloListView` (force override of default list view).
 *    - Registers "n_list" with standard listView for non-customized lists.
 *
 * Purpose:
 * Provides a fully interactive and studio-editable list (tree) view in Odoo,
 * enabling developers and users to customize columns, fields, and buttons
 * dynamically within Cyllo Studio.
 */
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { CylloListRenderer } from "./cyllo_list_renderer";
import { CylloListArchParser } from "./cyllo_list_arch";

export const CylloListView = {
  ...listView,
  Renderer: CylloListRenderer,
  ArchParser: CylloListArchParser,
};

registry.category("views").add("list", CylloListView, { force: true });
registry.category("views").add("n_list", listView, { force: true });
