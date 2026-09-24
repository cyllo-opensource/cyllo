/** @odoo-module **/

/**
 * SearchFieldDialog
 * -----------------
 * Custom dialog component for managing "Search Fields" in Cyllo Studio.
 *
 * Features:
 * 1. Allows users to add or update search fields for a given view/model.
 * 2. Supports field selection, label customization, visibility toggling,
 *    and assignment to specific groups.
 * 3. Persists changes via RPC calls to backend routes.
 * 4. Maintains Undo/Redo history in sessionStorage.
 *
 * Props:
 * - `properties`: Existing search field configuration (optional).
 * - `allFields`: All fields of the current model.
 * - `path`: Path in the view where the search field should be added/updated.
 * - `viewId`: ID of the view being edited.
 * - `model`: Target model for the search field operation.
 */
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService, useOwnedDialogs } from "@web/core/utils/hooks";
import { ExpressionEditorDialog } from "@web/core/expression_editor_dialog/expression_editor_dialog";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { Dialog } from "@web/core/dialog/dialog";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import {_t} from "@web/core/l10n/translation";

export class SearchFieldDialog extends Component {
  static template = "cyllo_studio.SearchFieldDialog";
  static components = {
    Dialog,
    MultiRecordSelector,
    CylloStudioDropdown
  };
  setup() {
    this.rpc = useService("rpc");
    this.action = useService("action");
    this.addDialog = useOwnedDialogs();
    this.notification = useService('effect')
    this.state = useState({
      string: "",
      field: null,
      invisible: "false",
      groupIds: [],
    });
    onWillStart(() => {
      if (this.props.properties) {
        this.state.string = this.props.properties.string;
        this.state.field = this.props.properties.field;
        this.state.invisible = this.props.properties.invisible;
        this.state.groupIds = this.props.properties.groupIds;
      }
    });
  }

  onDomainRadioClick() {
    this.state.invisible = ['False','false', '0'].includes(this.state.invisible) ? "True" : "False";
  }

    get AllFields(){
        const arr = []
        for(let value in this.props.allFields){
            const obj = { value : this.props.allFields[value].name ,label:this.props.allFields[value].string }
            arr.push(obj)
        }
        return arr
    }

  /**
   * Returns currently selected default field.
   */
    get defaultAllFields() {
       return this.state.field
    }


  /**
   * Updates state when a field is selected from dropdown.
   */
   handleAllFieldSelect(value) {
       this.state.field = value;
   }

  /**
   * Confirmation handler:
   * - Validates required field.
   * - Builds properties payload.
   * - Calls proper RPC route (add or update).
   * - Updates Undo/Redo stacks in sessionStorage.
   * - Reloads page to reflect changes immediately.
   */
  async onConfirm() {
    let result = this.props.path.replace(/t[^/]*\//, '')
    if (!this.state.field) {
       this.notification.add({
            title: _t("Warning"),
            message: "Please select a field.",
            type: "notification_panel",
            notificationType: "warning",
        });
      return;
    }

    let rpcUrl = "cyllo_studio/add/search_field";

    let properties = {
      string: this.state.string,
      field: this.state.field,
      invisible: this.state.invisible,
      groupIds: this.state.groupIds,
    };

    if (this.props.properties) {
      rpcUrl = "cyllo_studio/update/search_field";
      properties = Object.keys(properties).reduce((acc, key) => {
        if (properties[key] !== this.props.properties[key]) {
          acc[key] = properties[key];
        }
        return acc;
      }, {});
      if ('field' in properties) {
          properties.name = properties.field;
          delete properties.field;
      }
    }
    this.env.services.ui.block();
    try {
     const response =  await this.rpc(rpcUrl, {
        path: result,
        view_id: this.props.viewId,
        model: this.props.model,
        properties,
      });
       if(response){
            let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
            let cleanedStr = response.replace(/\s+/g, ' ').trim();
            storedArray.push(cleanedStr);
            sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
            sessionStorage.setItem('ReDO', JSON.stringify([]));
        }
    } finally {
      this.env.services.ui.unblock();
    }
//---------------changed-------------------
        window.location.reload()
//-----------------------------------------
    this.props.close();
  }
  onDiscard() {
    this.props.close();
  }
}
