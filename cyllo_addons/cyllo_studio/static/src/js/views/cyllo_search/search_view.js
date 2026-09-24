/** @odoo-module **/

/**
 * SearchView
 *
 * Custom extension of Odoo's `SearchBarMenu` for Cyllo Studio.
 *
 * Features:
 * ----------
 * 1. Extends search view interactivity with drag-and-drop (via `SortableJS`) for reordering filters, groups, and fields.
 * 2. Integrates RPC calls for modifying search view structure (add, update, remove filters, groups, fields, and search panels).
 * 3. Supports undo/redo history management using `sessionStorage`.
 * 4. Provides UI dialogs for search-related entities:
 *    - Filters (`FilterDomainSelectorDialog`)
 *    - GroupBys (`GroupByDialog`)
 *    - Search Fields (`SearchFieldDialog`)
 *    - Search Panel Values (`SearchPanelValueDialog`)
 *    - Search Panel Configurations (`SearchPanelDialog`)
 * 5. Handles visibility toggling for invisible search elements (`onInvisibleClick`).
 * 6. Normalizes color formats for consistent rendering in search panels.
 *
 * Purpose:
 * --------
 * Enables Cyllo Studio users to visually configure and manage search views,
 * while persisting structural changes to the backend and keeping a smooth
 * UX through drag-and-drop and dialog-based interactions.
 */
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { onMounted, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { FilterDomainSelectorDialog } from "./dialog/filter_domain_selector_dialog";
import { GroupByDialog } from "./dialog/groupby_dialog";
import { SearchFieldDialog } from "./dialog/search_field_dialog";
import { SearchPanelValueDialog } from "./dialog/search_panel_value_dialog";
import { SearchPanelDialog } from "./dialog/search_panel_dialog";

export class SearchView extends SearchBarMenu {
  static template = "cyllo_studio.SearchView";
  static components = { ...SearchBarMenu.components };

  setup() {
    super.setup();
    this.rpc = useService("rpc");
    this.action = useService("action");
    this.notification = useService("effect");
    onMounted(() => this.onMounted());
    this.filterRef = useRef("filterRef");
    this.groupRef = useRef("groupRef");
    this.searchFieldRef = useRef("searchFieldRef");
    this.searchPanelRef = useRef("searchPanelRef")
    this.searchPanelItems = this.env.searchModel.sections
    this.searchPanelInfo = this.env.searchModel.searchPanelInfo
    this.state = useState({
        ...this.state,
        searchFields: this.env.searchModel.getSearchItems((searchItem) => ["field"].includes(searchItem.type)),
        filterItems: this.env.searchModel.getSearchItems((searchItem) => ["filter", "dateFilter", "filterSeparator"].includes(searchItem.type)),
        groupByItems: this.env.searchModel.getSearchItems((searchItem) => ["groupBy", "dateGroupBy", "groupSeparator"].includes(searchItem.type) && !searchItem.isProperty),
        searchPanelItems: this.searchPanelItems,
        visibleSearchElement: JSON.parse(sessionStorage.getItem("showInvisibleSearch")) || false,
    })
  }

  async reloadSearchView() {
    // Manually fetch the updated view from the server to bypass the frontend cache
    // This avoids using CLEAR-CACHES which triggers unintended backend menu reloading.
    const result = await this.env.services.orm.call(
        this.env.searchModel.resModel,
        "get_views",
        [],
        {
            context: this.env.searchModel.globalContext,
            views: [[this.env.searchModel.searchViewId, "search"]],
            options: { action_id: this.env.config.actionId || false }
        }
    );

    await this.env.searchModel.load({
        resModel: this.env.searchModel.resModel,
        context: this.env.searchModel.globalContext,
        searchViewId: this.env.searchModel.searchViewId,
        domain: this.env.searchModel.globalDomain,
        groupBy: this.env.searchModel.globalGroupBy,
        orderBy: this.env.searchModel.globalOrderBy,
        searchViewArch: result.views.search.arch,
        searchViewFields: result.models[this.env.searchModel.resModel],
    });

    this.action.doAction("studio_reload");
  }

    onMounted() {
    // Studio's own view-editor aside bar has no content for the search
    // view — close it so a stale panel isn't left open behind this one.
    this.env.bus.trigger("SEARCH_VIEW_OPENED");
    // visibleSearchElement is now initialized from sessionStorage directly
    // in useState() above, so no correction is needed here.
    const self = this;
    const filter = this.filterRef.el;
    const group = this.groupRef.el;
    const searchField = this.searchFieldRef.el;
    const searchPanel = this.searchPanelRef.el;
    let perv_path = null;
    let next_path = null;

    const containers = [filter, group, searchField, searchPanel];

    // Destroy existing sortables if any
    containers.forEach((container) => {
        if (!container) return;
        const existing = Sortable.get(container);
        if (existing) existing.destroy();
    });

    containers.forEach((container) => {
        if (!container) return;

        Sortable.create(container, {
            animation: 150,
            ghostClass: 'sortable-ghost',

            // Only allow dragging via the handle
            handle: '.handle-drag',

            // Only allow dropping within the same container (mirrors accepts: target === source)
            group: {
                name: 'search-items',
                pull: false,
                put: false,
            },

            onStart: function(evt) {
                perv_path = evt.item.previousElementSibling?.getAttribute("cy-xpath") || null;
                next_path = evt.item.nextElementSibling?.getAttribute("cy-xpath") || null;
            },

            onEnd: async function(evt) {
                // If dropped back to same position, do nothing
                if (evt.oldIndex === evt.newIndex) return;

                const el = evt.item;
                const previous_path = el.previousElementSibling?.getAttribute("cy-xpath") || null;
                const first_el_xpath = container.querySelector('div')?.getAttribute("cy-xpath") || null;
                let path = el.getAttribute("cy-xpath");

                // Get sibling now after the dropped element
                const sibling = el.nextElementSibling || null;
                const sibling_path = sibling?.getAttribute("cy-xpath") || null;
                const position = sibling_path ? "before" : "after";

                self.env.services.ui.block();
                try {
                    const response = await self.rpc("cyllo_studio/search/move/item", {
                        view_id: self.env.searchModel.searchViewId,
                        model: self.env.searchModel.resModel,
                        path,
                        position,
                        sibling_path,
                        previous_path,
                        perv_path,
                        next_path,
                        first_el_xpath,
                    });

                    if (response) {
                        let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                        let cleanedStr = response.replace(/\s+/g, ' ').trim();
                        storedArray.push(cleanedStr);
                        sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                        sessionStorage.setItem('ReDO', JSON.stringify([]));
                    } else {
                        self.notification.add({
                            title: _t("Warning"),
                            message: "Separators cannot be placed next to each other or at the top.",
                            type: "notification_panel",
                            notificationType: "warning",
                        });
                    }
                } finally {
                    setTimeout(() => {
                        self.env.services.ui.unblock();
                        self.reloadSearchView();
                    }, 3000);
                }
            },
        });
    });
}

  /** @returns {string[]} Sample values for testing. */
  get sampleValues(){
    return ['Customer', 'Sales Team', 'Create Date']
  }

    /** @returns {Array} Search field items from state. */
  get searchFields() {
    return this.state.searchFields
  }

  /** @returns {Array} GroupBy items from the search model. */
  get groupByItems() {
    return this.env.searchModel.getSearchItems(
      (searchItem) =>
        ["groupBy", "dateGroupBy", "groupSeparator"].includes(
          searchItem.type
        ) && !searchItem.isProperty
    );
  }

   /** @returns {Array} Filter items from state. */
  get filterItems() {
    return this.state.filterItems
  }

  /**
   * Toggle visibility of invisible search fields.
   */
  async onInvisibleClick(){
    // Toggle the state immediately so the checkbox doesn't flicker back while
    // the async RPC + reload are in flight. Without this the Owl template
    // re-reads the old state value after the click, causing the checkbox to
    // visually revert before onMounted() corrects it on the next render.
    const newValue = !this.state.visibleSearchElement;
    this.state.visibleSearchElement = newValue;
    sessionStorage.setItem('showInvisibleSearch', newValue);
    await this.rpc("cyllo_studio/set/session", {
        key: 'show_invisible_search',
        value: newValue,
    });
    await this.reloadSearchView();
  }

  /**
   * Add a separator to the search view structure.
   * @param {Object} sibling - Reference item to insert next to.
   */
  async addSeperator(sibling) {
    if (!sibling.cyXpath.includes("separator")) {
        this.env.services.ui.block();
        const rpcURl = "cyllo_studio/search/add/separator"
        try {
          const response = await this.rpc(rpcURl, {
            sibling_path: sibling.cyXpath,
            view_id: this.env.searchModel.searchViewId,
            model: this.env.searchModel.resModel,
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
    }
    await this.reloadSearchView()
  }

  /**
   * Add a new filter to the search view via dialog.
   * @param {Object} sibling - Reference item for positioning.
   */
  async addFilter(sibling) {
    const { domainEvalContext: context, resModel } = this.env.searchModel;
    const domain = await this.getDefaultLeafDomain(resModel);
    let path = sibling?.cyXpath || this.searchPanelInfo?.filter || "/search";

    this.dialogService.add(FilterDomainSelectorDialog, {
      resModel,
      defaultConnector: "|",
      domain,
      context,
      allFields: this.env.searchModel.searchViewFields,
      onConfirm: async (properties) =>
        await this.saveFilter(path, properties),
      title: _t("Add New Filter"),
      confirmButtonText: _t("Add"),
      discardButtonText: _t("Cancel"),
      isDebugMode: this.env.searchModel.isDebugMode,
    });
  }

  /**
   * Add a new groupBy to the search view via dialog.
   */
  async addGroupBy(sibling) {
    this.dialogService.add(GroupByDialog, {
      fields: this.fields,
      allFields: this.env.searchModel.searchViewFields,
      path: sibling?.cyXpath || this.searchPanelInfo?.groupBy || "/search",
      viewId: this.env.searchModel.searchViewId,
      model: this.env.searchModel.resModel,
    });
  }

  /**
   * Add a new search field to the search view.
   */
  addSearchField(sibling) {
    this.dialogService.add(SearchFieldDialog, {
      fields: this.fields,
      allFields: this.env.searchModel.searchViewFields,
      path: sibling?.cyXpath || "/search",
      viewId: this.env.searchModel.searchViewId,
      model: this.env.searchModel.resModel,
    });
  }

 /**
   * Edit an existing search field.
   * @param {Object} item - The search field item.
   */
  async editSearchField(item) {
    let properties = {
      string: item.description || "",
      field: item.fieldName,
      invisible: item.invisible || "false",
      groupIds: [],
    };
    if (item.groups) {
      properties.groupIds = await this.rpc("cyllo_studio/find/groups", {
        groups: item.groups,
      });
    }
    this.dialogService.add(SearchFieldDialog, {
      fields: this.fields,
      allFields: this.env.searchModel.searchViewFields,
      path: item.cyXpath,
      viewId: this.env.searchModel.searchViewId,
      model: this.env.searchModel.resModel,
      properties,
    });
  }

  /**
   * Edit an existing filter (standard or date filter).
   * @param {Object} item - The filter item.
   */
  async editFilter(item) {
    let properties = {
      label: item.description || "",
      invisible: item.invisible || "false",
      groupIds: [],
    };
    if(item.type === "dateFilter"){
      properties.fieldName = item.fieldName
      properties.defaultValues = item.defaultGeneratorIds
    }
    if (item.groups) {
      properties.groupIds = await this.rpc("cyllo_studio/find/groups", {
        groups: item.groups,
      });
    }
    const { domainEvalContext: context, resModel } = this.env.searchModel;
    this.dialogService.add(FilterDomainSelectorDialog, {
      resModel,
      defaultConnector: "|",
      domain: item.domain || "",
      context,
      properties,
      allFields: this.env.searchModel.searchViewFields,
      onConfirm: async (properties) =>
        await this.updateFilter(item.cyXpath, properties),
      title: _t("Update Filter"),
      confirmButtonText: _t("Update"),
      discardButtonText: _t("Cancel"),
      isDebugMode: this.env.searchModel.isDebugMode,
    });
  }

/**
   * Update an existing filter in backend.
   * @param {string} path - XPath of the filter.
   * @param {Object} properties - Filter properties.
   */
  async updateFilter(path, properties) {
    this.env.services.ui.block();
    try {
     const response =  await this.rpc("cyllo_studio/search/update/filter", {
        path,
        properties,
        view_id: this.env.searchModel.searchViewId,
        model: this.env.searchModel.resModel,
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
    await this.reloadSearchView()
  }


  /**
   * Save a new filter into backend.
   * @param {string} sibling_path - Position reference.
   * @param {Object} properties - Filter properties.
   */
  async saveFilter(sibling_path, properties) {
    this.env.services.ui.block();
    try {
      const response = await this.rpc("cyllo_studio/search/add/filter", {
        sibling_path,
        properties,
        view_id: this.env.searchModel.searchViewId,
        model: this.env.searchModel.resModel,
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
    await this.reloadSearchView()
  }

  /**
   * Edit an existing groupBy item.
   * @param {Object} item - GroupBy item.
   */
  async editGroupBy(item) {
    let properties = {
      string: item.description || "",
      field: item.fieldName,
      invisible: item.invisible || "false",
      groupIds: [],
    };
    if (item.groups) {
      properties.groupIds = await this.rpc("cyllo_studio/find/groups", {
        groups: item.groups,
      });
    }
    this.dialogService.add(GroupByDialog, {
      fields: this.fields,
      allFields: this.env.searchModel.searchViewFields,
      path: item.cyXpath,
      viewId: this.env.searchModel.searchViewId,
      model: this.env.searchModel.resModel,
      properties,
    });
  }

 standardize_color(str){
    var ctx = document.createElement('canvas').getContext('2d');
    ctx.fillStyle = str;
    return ctx.fillStyle;
}

  /**
   * Add or edit a Search Panel value.
   * @param {Object} [item=false] - Search panel item to edit.
   */

  async SearchPanelValue(item=false) {
     let properties = false
     if (item){
        let color = "#7e8600"
        if(item.color){
            color = item.color.startsWith("#") ? item.color : this.standardize_color(item.color)
         }
        properties = {
          string: item.description || "",
          field: item.fieldName,
          icon: item.icon || "",
          color: color,
          hierarchize: item.hierarchize,
          enable_counters: item.enableCounters,
          expand: item.expand,
          limit: item.limit,
          select: item.type === 'category' ? 'one' : 'multi',
          invisible: item.invisible || "False",
          groupIds: [],
        };
        if (item.accessGroups) {
          properties.groupIds = await this.rpc("cyllo_studio/find/groups", {
            groups: item.accessGroups,
          });
        }
     }

    this.dialogService.add(SearchPanelValueDialog, {
      fields: this.fields,
      allFields: this.env.searchModel.searchViewFields,
      path: item ? item.cyXpath : this.searchPanelInfo.cyXpath,
      viewId: this.env.searchModel.searchViewId,
      model: this.env.searchModel.resModel,
      properties,
    });
  }

  async removeItem(path) {
      this.state.searchFields = this.state.searchFields.filter((item) => item.cyXpath !== path)
      this.state.filterItems = this.state.filterItems.filter((item) => item.cyXpath !== path)
      this.state.groupByItems = this.state.groupByItems.filter((item) => item.cyXpath !== path)
      let searchPanelItems = []
      this.state.searchPanelItems.forEach((item) => {
          item.cyXpath !== path ? searchPanelItems.push(item) : null
      })
      this.state.searchPanelItems = searchPanelItems
     this.env.services.ui.block();
    try {
     const response  =  await this.rpc("cyllo_studio/search/remove/item", {
        path,
        view_id: this.env.searchModel.searchViewId,
        model: this.env.searchModel.resModel,
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
    await this.reloadSearchView()
  }

  get allViews(){
     const filteredViews = this.env.config.views
    .map(item => item[1])
    .filter(value => value !== "search" && value !== "form");

    return filteredViews.reduce((acc, item) => {
        acc[item] = item;
        return acc;
    }, {})
  }

  async addSearchPanel(){
    this.env.services.ui.block();
    try {
      const response = await this.rpc("cyllo_studio/search/add/search_panel", {
        view_id: this.env.searchModel.searchViewId,
        model: this.env.searchModel.resModel,
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
    await this.reloadSearchView()
  }

  async editSearchPanel(){
    let groupIds = []
     if (this.searchPanelInfo.groups) {
          groupIds = await this.rpc("cyllo_studio/find/groups", {
            groups: this.searchPanelInfo.groups,
          });
     }
     this.dialogService.add(SearchPanelDialog, {
      path: this.searchPanelInfo.cyXpath,
      viewId: this.env.searchModel.searchViewId,
      model: this.env.searchModel.resModel,
       views: this.allViews,
      properties: {
        view_types: this.searchPanelInfo.viewTypes || [],
        groupIds,
      }
    });
  }
}
