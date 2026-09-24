/** @odoo-module **/

/**
 * FormLabel Patch for Studio
 *
 * Extends the default Odoo FormLabel to provide Studio editing capabilities.
 * Allows users to click on labels to select form fields, highlight them,
 * show field icons, and trigger events for Studio property editing.
 *
 * Features:
 *  - Highlight the clicked field with a border.
 *  - Show/hide Studio field icons dynamically.
 *  - Determine the correct `cy-xpath` for single or multi-path fields.
 *  - Trigger `itemFieldName` event with all relevant field metadata for Studio.
 *
 * Props:
 *  - cyXpath (optional): The xpath of the field for Studio tracking.
 *
 * Methods:
 *  - onItemClick(e): Handles field label clicks, updates UI, computes paths,
 *    and triggers Studio bus events.
 */
import { FormLabel } from "@web/views/form/form_label";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

patch(FormLabel.prototype, {
  async setup() {
    super.setup();
  },

  /**
   * Handle click on a field label.
   * @param {MouseEvent} e - The click event.
   */
  onItemClick(e) {
    let parent = e.target.closest(".o_wrap_field");
    let item_path = parent?.firstElementChild.getAttribute("cy-xpath") || "";
    let has_multipath = false;
    if (!item_path) {
      let child = parent?.firstElementChild;
      if (child?.firstElementChild.nodeName == "BUTTON") {
        item_path = child?.firstElementChild.getAttribute("cy-xpath");
      } else {
        has_multipath = true;
        item_path = {
          first_path: child?.firstElementChild.getAttribute("cy-xpath"),
          second_path:
            child?.nextElementSibling?.firstElementChild.getAttribute("cy-xpath"),
        };
      }
    }

     const allIcons = document.querySelectorAll('.cy-studio-field-icons');
    allIcons.forEach(icon => {
        icon.style.opacity = '0';
        icon.style.marginRight = '';
            icon.style.background = '';

    });
    const panelIcons = e.target.parentElement.classList.contains('o_td_label') ? e.target.parentElement.offsetParent.nextElementSibling.querySelector('.cy-studio-field-icons') : e.target.parentElement.nextElementSibling?.querySelector('.cy-studio-field-icons')
    if(panelIcons){
       panelIcons.style.opacity = '1';
        panelIcons.style.marginRight = '0px';
          panelIcons.style.backgroundColor = '#f6fce5';

    }
    const elements = document.querySelectorAll(".border-class");
    elements.forEach((e) => {
      e.classList.remove("border-class");
    });

    let oWrapElement = e.target.closest(".o_wrap_label");
    oWrapElement?.classList.add("border-class");
    oWrapElement?.nextElementSibling.classList?.add("border-class");

    e.preventDefault();
    e.stopPropagation();
    var self = this;
    const targetElement = e.target.parentElement;
    const parentDiv = targetElement.closest(".o_wrap_field");
    if (parentDiv) {
      this.field_name = parentDiv.querySelector(".o_field_widget")?.getAttribute("name");
      const FieldItem = [this.__owl__.children];
      FieldItem.filter(function (item) {
        Object.values(item).filter(function (data) {
          if (data.props && data.props.name === self.field_name) {
            self.item_name = data;
          }
        });
      });
      this.env.bus.trigger("itemFieldName", {
        itemName: this,
        path: this.props.fieldInfo.MainPath,
        widgets:  this.content,
        FieldInfo: this.props.fieldInfo,
        activeFields: this.env.model.config.activeFields,
        item_path: item_path,
        has_multipath: has_multipath,
      });
    }
  },
});

FormLabel.props = {
  ...FormLabel.props,
  cyXpath: { type: String, optional: true },
};

FormLabel.template = "cyllo_studio.FormLabel";
