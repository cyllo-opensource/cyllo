/** @odoo-module **/

/**
 * Patch the SearchModel to handle invisible search items in Studio views.
 * Adds support for a "showInvisibleSearch" toggle stored in sessionStorage.
 */
import { patch } from "@web/core/utils/patch";
import { evaluateExpr } from "@web/core/py_js/py";
import { SearchModel } from "@web/search/search_model";

patch(SearchModel.prototype,{
    setup(services){
        super.setup(services);
        this.showInvisibleSearch = JSON.parse(sessionStorage.getItem("showInvisibleSearch")) || false;//starlin

    },

    /**
     * Return search items, filtering out invisible items unless showInvisibleSearch is enabled.
     *
     * @param {Function} predicate - Optional filter function to apply to each search item
     * @returns {Array} Array of enriched search items
     */
    getSearchItems(predicate) {
        const searchItems = [];
        Object.values(this.searchItems).forEach((searchItem) => {

            let isInvisible =
                "invisible" in searchItem && evaluateExpr(searchItem.invisible, this.globalContext);
            if (!searchItem.striped){
                searchItem.striped = isInvisible && this.showInvisibleSearch ? true : false ;
            }
            isInvisible = this.showInvisibleSearch ? false : isInvisible ;
            if (!isInvisible && (!predicate || predicate(searchItem))) {
                const enrichedSearchitem = this._enrichItem(searchItem);
                if (enrichedSearchitem) {
                    searchItems.push(enrichedSearchitem);
                }
            }
        });
        if (searchItems.some((f) => f.type === "favorite")) {
            searchItems.sort((f1, f2) => f1.groupNumber - f2.groupNumber);
        }
        return searchItems;
    },
});
