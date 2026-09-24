/** @odoo-module **/
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";

export class ExistingFieldProperties extends Component {
  static template = "cyllo_studio.ExistingFieldProperties";
  setup() {
  }
}
ExistingFieldProperties.components = {
  CylloStudioDropdown,
};
