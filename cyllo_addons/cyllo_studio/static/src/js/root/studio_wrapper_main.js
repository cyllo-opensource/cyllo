/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { CylloNavBar } from "@cyllo_studio/js/navbar/navbar";
import { ActionContainer } from "@web/webclient/actions/action_container";
import { MainComponentsContainer } from "@web/core/main_components_container";

/**
 * Main wrapper component for the Studio interface.
 * Manages top-level state such as edit mode, view changes, and active view details.
 */

export class StudioWrapperMain extends Component {
  static template = "cyllo_studio.StudioWrapperMain";
  setup() {
    this.state = useState({
      edit: false,
      viewChanged: false,
      editButton: true,
      view: true,
      viewDetails:{}
    });
    this.updateState = this.updateState.bind(this);
  }

  /**
   * Updates a specific attribute in the component state.
   * @param {string} attr - The attribute name to update.
   * @param {*} value - The new value for the attribute.
   */

  updateState(attr, value) {
    this.state[attr] = value;
  }

   /**
   * Returns props for child components.
   * Includes the current state and the updateState method for two-way state binding.
   * @returns {Object} The props object.
   */

  get viewProps() {
    return { ...this.state, updateState: this.updateState };
  }
}
StudioWrapperMain.components = {
  CylloNavBar,
  MainComponentsContainer,
  ActionContainer,
};
