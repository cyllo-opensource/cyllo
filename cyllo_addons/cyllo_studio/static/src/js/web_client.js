/** @odoo-module **/
/**
 * Patch for WebClient
 *
 * This patch extends the Odoo WebClient to support a light mode specifically
 * for the Studio environment. On mounting, it checks the localStorage for
 * the "lightModeStudio" flag and adds a "light-studio-mode" CSS class to the
 * body if enabled. This allows Studio users to toggle between light and dark
 * UI themes.
 */
import { onMounted } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { StudioWrapperMain } from "@cyllo_studio/js/root/studio_wrapper_main";

patch(WebClient.prototype, {
  setup() {
    super.setup();
    onMounted(() => {
      const darkMode = localStorage.getItem("lightModeStudio");
      if (darkMode) {
        document.body.classList.add("light-studio-mode");
      }
    });
  },
});
WebClient.template = "cyllo_studio.WebClient";
WebClient.components = {
  ...WebClient.components,
  StudioWrapperMain,
};
