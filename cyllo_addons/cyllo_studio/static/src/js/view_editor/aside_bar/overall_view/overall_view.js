/** @odoo-module **/
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ListOverall } from "@cyllo_studio/js/views/cyllo_list/list_overall";
import { FormOverall } from "@cyllo_studio/js/views/cyllo_form/form_overall";
import { PivotOverall } from "@cyllo_studio/js/views/cyllo_pivot/pivot_overall";
import { _t } from "@web/core/l10n/translation";
import { KanbanOverall } from "@cyllo_studio/js/views/cyllo_kanban/kanban_overall";
import { CalendarOverall } from "@cyllo_studio/js/views/cyllo_calendar/calendar_overall";
import { GraphOverall } from "@cyllo_studio/js/views/cyllo_graph/graph_overall";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { resetViewCompilerCache } from "@web/views/view_compiler";

/**
 * Component to handle editing and displaying all types of views in Studio.
 * Supports list, form, pivot, kanban, calendar, and graph views.
 * Handles global operations like showing invisible fields and overall view updates.
 */
export class OverallView extends Component {
  static template = "cyllo_studio.OverallView";
  static props = {
    mode: { type: Object, optional: true },
    allFields: { type: Object, optional: true },
    activeFields: { type: Object, optional: true },
    viewType: { type: String, optional: true },
    model: { type: String, optional: true },
    calendar_info: { type: Object, optional: true },
    viewId: { type: [Number, String], optional: true },
    edit: { type: Boolean, optional: true },
    isMenu: { type: Boolean, optional: true },
    hasColorPicker: { type: Boolean, optional: true },
    progressAttributes: { type: Object, optional: true },
    ribbonElement: { type: NodeList, optional: true },
    measure: { type: Object, optional: true },
    envModel: { type: Object, optional: true },
    type: { type: String, optional: true },
    colorPickerPath: { type: String, optional: true },
    MetaData: { type: Object, optional: true },
    isFieldTag: { type: Boolean, optional: true },
    relational_model: { type: [String, Object], optional: true },
    fieldNodes: { type: Object, optional: true },
    widget: { type: String, optional: true },
    invisible: { type: String, optional: true },
    showInvisible: { type: Boolean, optional: true },
    showInvisibleFields: { type: Function, optional: true },
  };
  setup() {
    this.rpc = useService("rpc");
    this.notification = useService("effect");
    this.actionService = useService("action");
    this.dialogService = useService("dialog");
    this.state = useState({
      showInvisible: sessionStorage.getItem("invisible") === "1",
      showOptional: sessionStorage.getItem("show_optional") === "1"
    });
    //    onWillStart(() => {
    //      const checked = sessionStorage.getItem("invisible") === "1";
    //      this.state.showInvisible = checked;
    //      document.body.classList.toggle("cy-show-invisible", checked);
    //      // this.env.bus.trigger("CYLLO:SHOW_INVISIBLE_TOGGLED", checked);
    //    });

    onWillStart(() => {
      const checked = sessionStorage.getItem("invisible") === "1";
      this.state.showInvisible = checked;
      document.body.classList.toggle("cy-show-invisible", checked);
      // Optional fields are revealed by a separate toggle so "Show Invisible
      // Elements" no longer also exposes optional columns.
      const optionalChecked = sessionStorage.getItem("show_optional") === "1";
      this.state.showOptional = optionalChecked;
      document.body.classList.toggle("cy-show-optional", optionalChecked);
    });
    //        onMounted(() => {
    //        const checked = sessionStorage.getItem("invisible") === "1";
    //        if (checked) {
    //            this._applyInvisibleOverride(true);
    //        }
    //    });
  }
  _applyInvisibleOverride(show) {
    if (show) {
      document.body.classList.add("cy-show-invisible");
      document.querySelectorAll('[invisible="1"], [invisible="True"], [invisible="true"]').forEach(el => {
        el.style.setProperty('display', '', 'important');
        el.setAttribute('data-cy-was-invisible', '1');
      });
    } else {
      document.body.classList.remove("cy-show-invisible");
      // Restore Odoo's inline hide
      document.querySelectorAll('[data-cy-was-invisible="1"]').forEach(el => {
        el.style.display = 'none';
        el.removeAttribute('data-cy-was-invisible');
      });
    }
  }

  /**
  * Toggle display of invisible fields and reload the view.
  * @param {Event} ev - The checkbox change event.
  */

  showInvisibleFields(ev) {
    const checked = !!ev.target.checked;
    this.state.showInvisible = checked;
    if (checked) {
      sessionStorage.setItem("invisible", "1");
    } else {
      sessionStorage.removeItem("invisible");
    }
    this._applyInvisibleOverride(checked);
    document.body.classList.toggle("cy-hide-invisible", !checked);
    this.env?.bus?.trigger?.("CYLLO:SHOW_INVISIBLE_TOGGLED", checked);
    resetViewCompilerCache();
    this.actionService.doAction("studio_reload");
  }

  /**
   * Toggle display of optional (column-options) fields. Separate from
   * "Show Invisible Elements" so each reveals only its own kind of hidden
   * column. Pure CSS body-class toggle — no reload needed.
   * @param {Event} ev - The checkbox change event.
   */
  showOptionalFields(ev) {
    const checked = !!ev.target.checked;
    this.state.showOptional = checked;
    if (checked) {
      sessionStorage.setItem("show_optional", "1");
    } else {
      sessionStorage.removeItem("show_optional");
    }
    document.body.classList.toggle("cy-show-optional", checked);
  }

  /**
   * Reset the current view to its code-defined default, discarding ALL
   * Studio customizations on it. Works for every view type (form, list,
   * kanban, ...). The Studio view is deactivated (not deleted), so it can
   * later be restored from the deactivated-views list. Confirms first.
   */
  resetView() {
    const model = this.props.model;
    let view_id = this.props.viewId;
    let view_type = this.props.viewType;
    // Search views are tracked separately (see undo/redo in the navbar).
    const searchViewId = sessionStorage.getItem("searchViewId");
    if (searchViewId) {
      view_type = "search";
      view_id = searchViewId;
    }
    if (!model || !view_id || !view_type) {
      this.notification.add({
        title: _t("Cannot Reset"),
        message: "Open the view you want to reset first.",
        type: "notification_panel",
        notificationType: "warning",
        animation: false,
      });
      return;
    }
    this.dialogService.add(ConfirmationDialog, {
      title: _t("Reset View to Default"),
      body: _t(
        "This removes ALL Studio changes on this view and restores the "
        + "original layout defined in code. Custom fields you added stay on "
        + "the model but will no longer appear here."
      ),
      confirmLabel: _t("Reset View"),
      cancelLabel: _t("Cancel"),
      confirm: async () => {
        try {
          await this.rpc("/cyllo_studio/reset_view", {
            model: model,
            view_type: view_type,
            view_id: view_id,
          });
        } finally {
          sessionStorage.removeItem("UndoRedo");
          sessionStorage.removeItem("ReDO");
          this.env?.bus?.trigger?.("resetProperties");
          this.actionService.doAction("studio_reload");
          window.location.reload();
        }
      },
      cancel: () => { },
    });
  }

  /**
   * Common properties passed to all overall view components.
   */
  get commonProps() {
    return {
      envModel: this.props.envModel,
      mode: this.props.mode,
      viewType: this.props.viewType,
      model: this.props.model,
      viewId: this.props.viewId,
      handleView: this.handleView.bind(this),
      showInvisibleFields: this.showInvisibleFields.bind(this),
      showInvisible: this.state.showInvisible,
      showOptionalFields: this.showOptionalFields.bind(this),
      showOptional: this.state.showOptional,
    };
  }

  // Props for specific view components
  get overallListProps() {
    return {
      ...this.commonProps,
      allFields: this.props.allFields,
      activeFields: this.props.activeFields,
    };
  }
  get overallPivotProps() {
    return {
      ...this.commonProps,
      activeFields: this.props.activeFields,
    };
  }
  get overallCalendarProps() {
    return {
      ...this.commonProps,
      activeFields: this.props.activeFields,
      model: this.props.calendar_info,
    };
  }
  get overallFormProps() {
    return {
      ...this.commonProps,
      allFields: this.props.allFields,
      activeFields: this.props.activeFields,
    };
  }
  get overallGraphProps() {
    return {
      ...this.commonProps,
      allFields: this.props.allFields,
      MetaData: this.props.MetaData,

    };
  }
  get overallKanbanProps() {
    return {
      ...this.commonProps,
      allFields: this.props.allFields,
      isMenu: this.props.isMenu,
      hasColorPicker: this.props.hasColorPicker,
      colorPickerPath: this.props.colorPickerPath,
      progressAttributes: this.props.progressAttributes,
      ribbonElement: this.props.ribbonElement || document.querySelectorAll('nonexistent-selector'),
    };
  }
  /**
  * Handles updating overall view attributes via RPC.
  * @param {string} name - The attribute name to update.
  * @param {*} value - The new value.
  * @param {*} order - Optional order parameter for fields.
  */
  async handleView(name, value = null, order = null) {
    if (name) {
      try {
        await this.rpc("cyllo_studio/edit/overall_view", {
          method: "edit_overallView",
          args: [
            {
              model: this.props.model,
              view_type: this.props.viewType,
              view_id: this.props.viewId,
            },
          ],
          kwargs: {
            value: value,
            attr: name,
            path: '/' + this.props.viewType,
            order: order,
          },
        });
      } finally {
        this.notification.add({
          title: _t("Success"),
          message: "Changes Added.",
          description: "Exit Studio Mode To View Changes",
          type: "notification_panel",
          notificationType: "success",
          animation: false,
        });
        this.actionService.doAction("studio_reload");
      }
    }
  }
}
OverallView.components = {
  ListOverall,
  FormOverall,
  PivotOverall,
  KanbanOverall,
  CalendarOverall,
  GraphOverall,
};
