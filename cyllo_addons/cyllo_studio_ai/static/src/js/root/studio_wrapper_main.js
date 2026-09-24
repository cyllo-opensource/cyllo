/** @odoo-module **/
import { useState, onRendered, onWillUpdateProps,onMounted } from "@odoo/owl";
import { useBus, useService } from "@web/core/utils/hooks";
import { StudioWrapperMain } from "@cyllo_studio/js/root/studio_wrapper_main";
import { patch } from '@web/core/utils/patch';

patch(StudioWrapperMain.prototype,{
  setup() {
    super.setup()
    this.action = useService("action");
    this.state = useState({
      ...this.state,
      isAI: false
    });
  },
  get actionId() {
        const hashParams = new URLSearchParams(window.location.hash.slice(1));
        const actionId = hashParams.get('action');
        return actionId
  },

    initStudioAIState() {

        const controller = this.action?.currentController;
        if (!controller) {
            return;
        }

        const views = controller.action?.views || [];

        this.state.isAI = false;
    },

})
StudioWrapperMain.template = "cyllo_studio_ai.StudioWrapperMain"

