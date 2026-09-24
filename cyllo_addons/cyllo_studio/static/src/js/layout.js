/** @odoo-module **/

/**
 *
 * Patch for the Layout component to integrate Cyllo Studio search view functionality.
 *
 * Features:
 * 1. Tracks and toggles a custom search view created via Cyllo Studio.
 * 2. Stores the search view state in sessionStorage for persistence across page reloads.
 * 3. Dynamically creates a search view if it does not exist for the current model.
 * 4. Uses Owl lifecycle hooks (onWillStart, onWillUnmount) to initialize state and clean up.
 * 5. Listens to the "SEARCH_CLICKED" event to toggle the search view asynchronously.
 *
 * Props:
 * - type (optional string)
 * - model (optional string)
 *
 * Components:
 * - SearchView
 */
import { Layout } from "@web/search/layout";
import { onWillStart, useState , onWillUnmount} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { SearchView } from "@cyllo_studio/js/views/cyllo_search/search_view";
import { patch } from "@web/core/utils/patch";

patch(Layout.prototype, {
  setup() {
    super.setup();
    this.rpc = useService("rpc");
    this.action = useService("action");
    this.state = useState({
      ...this.state,
      isSearchView: false,
      newClick: false,
    });
    onWillStart(() => {
      const cyStudioSearch =
        JSON.parse(sessionStorage.getItem("cyStudioSearch")) || false;
      if (cyStudioSearch) {
        if (cyStudioSearch?.viewId === this.env.searchModel.searchViewId) {
          this.state.isSearchView = cyStudioSearch?.show || false;
        } else {
          sessionStorage.removeItem("cyStudioSearch");
        }
      }
    });
    this.isDestroyed = false;
    onWillUnmount(() => {
      this.isDestroyed = true;
    });
    this.env.bus.addEventListener("SEARCH_CLICKED", async () => {
          if (!this.isDestroyed) {
      await this.toggleSearchView(); //await added
      }
    });
  },

   /**
   * Toggles the visibility of the Cyllo Studio search view.
   * If the search view does not exist, it calls createSearchView() to create it.
   */
  async toggleSearchView() {
      if (this.isDestroyed) return;
    sessionStorage.setItem("searchViewId", this.env.searchModel.searchViewId);
    if (!this.state.isSearchView) {
      let searchViewId = this.env.searchModel.searchViewId;
      if (!searchViewId) {
        await this.createSearchView();
      } else {
        this.setSearchSession(searchViewId);
        this.state.isSearchView = !this.state.isSearchView;
      }
    }
  },

  /**
   * Stores the search view state in sessionStorage.
   *
   * @param {number|string} searchViewId - ID of the search view to store
   */
  setSearchSession(searchViewId) {
    const cyStudioSearch = JSON.stringify({
      viewId: searchViewId,
      show: !this.state.isSearchView,
    });
    sessionStorage.setItem("cyStudioSearch", cyStudioSearch);
  },
  get searchView() {
    return SearchView;
  },

  /**
   * Creates a new Cyllo Studio search view using an RPC call.
   * Blocks the UI while the RPC is in progress and reloads the Studio UI after completion.
   */
  async createSearchView() {
    this.env.services.ui.block();
    try {
      let searchViewId = await this.rpc("cyllo_studio/search/add/search_view", {
        arch: this.env.searchModel.searchViewArch,
        model: this.env.searchModel.resModel,
      });
      this.setSearchSession(searchViewId);
    } finally {
      this.env.services.ui.unblock();
    }
    this.action.doAction("studio_reload");
  },
});
Layout.template = "studio.CylloLayout";
Layout.components = {
  ...Layout.components,
};
Layout.props = {
  ...Layout.props,
  type: {
    type: String,
    optional: true,
  },
  model: {
    type: String,
    optional: true,
  },
};
