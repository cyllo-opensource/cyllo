/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SearchBarSystray extends Component {
  // Component for the search bar in the systray.
  setup() {
    this.commandService = useService("command")
  }
  onSearchIconClick() {
    // Click (or the icon's data-hotkey="m") on the magnifier: open the
    // command palette straight into the master-search namespace — the
    // ">" prefix makes the palette render "Search for a record..." with
    // the model-grouped results (see the master_search provider in
    // core/commands/command_palette.js).
    this.commandService.openMainPalette({ searchValue: ">" });
  }
}
SearchBarSystray.template = "cyllo_web.SearchBarSystray";
export const systrayItem = {
  Component: SearchBarSystray,
};
registry.category("systray").add("SearchBar", systrayItem, {
  sequence: 1000,
});
