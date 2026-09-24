/** @odoo-module **/

/**
 *
 * Cyllo Studio Multi-Record Autocomplete
 *
 * This module extends Odoo's RecordAutocomplete to provide a multi-record
 * selection widget with support for dynamic searching, "search more" functionality,
 * and integration with the core ORM and Name services.
 *
 * Features:
 * 1. Limits initial search results to a small number, with a "Search More..." option.
 * 2. Integrates domain and context filtering for precise queries.
 * 3. Supports multi-selection and updates parent component state on selection.
 * 4. Registers searched display names with the NameService for caching.
 *
 * Dependencies: orm, name services, registry for dialogs.
 */
import {AutoComplete} from "@web/core/autocomplete/autocomplete";
import {_t} from "@web/core/l10n/translation";
import {Domain} from "@web/core/domain";
import {registry} from "@web/core/registry";
import {useOwnedDialogs, useService} from "@web/core/utils/hooks";
import {RecordAutocomplete} from "@web/core/record_selectors/record_autocomplete";

const SEARCH_LIMIT = 7;
const SEARCH_MORE_LIMIT = 320;

export class CylloMultiRecordAutocomplete extends RecordAutocomplete {

    static props = {
        resModel: String,
        update: Function,
        multiSelect: Boolean,
        getIds: Function,
        value: String,
        domain: {type: Array, optional: true},
        context: {type: Object, optional: true},
        className: {type: String, optional: true},
        fieldString: {type: String, optional: true},
        placeholder: {type: String, optional: true},
    };
    static components = {AutoComplete};
    static template = "web.RecordAutocomplete";

    setup() {
        this.orm = useService("orm");
        this.nameService = useService("name");
        this.addDialog = useOwnedDialogs();
        this.sources = [
            {
                placeholder: _t("Loading..."),
                options: this.loadOptionsSource.bind(this),
            },
        ];
    }

    /**
     * Adds display names to NameService cache for fast rendering.
     * @param {Array} options - Array of [id, label] pairs.
     */
    addNames(options) {
        const displayNames = Object.fromEntries(options);
        this.nameService.addDisplayNames(this.props.resModel, displayNames);
    }

    /**
     * Retrieves currently selected record IDs.
     * @returns {Array} - Array of selected record IDs.
     */
    getIds() {
        return this.props.getIds();
    }

    /**
     * Loads autocomplete options based on the input text.
     * Limits initial results and adds "Search More..." if results exceed limit.
     * @param {String} name - Input string for filtering records.
     * @returns {Array} - Array of options for the autocomplete dropdown.
     */
    async loadOptionsSource(name) {
        if (this.lastProm) {
            this.lastProm.abort(false);
        }
        this.lastProm = this.search(name, SEARCH_LIMIT + 1);
        const nameGets = (await this.lastProm).map(([id, label]) => ([id, label ? label.split("\n")[0] : _t("Unnamed")]));
        this.addNames(nameGets);
        const options = nameGets.map(([value, label]) => ({value, label}));
        if (SEARCH_LIMIT < nameGets.length) {
            options.push({
                label: _t("Search More..."),
                action: this.onSearchMore.bind(this, name),
                classList: "o_m2o_dropdown_option",
            });
        }
        if (options.length === 0) {
            options.push({label: _t("(no result)"), unselectable: true});
        }
        return options;
    }

    /**
     * Handles the "Search More" action, opening a SelectCreateDialog with extended results.
     * @param {String} name - Input string for filtering records.
     */
    async onSearchMore(name) {
        const {fieldString, multiSelect, resModel} = this.props;
        let operator;
        const ids = [];
        if (name) {
            const nameGets = await this.search(name, SEARCH_MORE_LIMIT);
            this.addNames(nameGets);
            operator = "in";
            ids.push(...nameGets.map((nameGet) => nameGet[0]));
        } else {
            operator = "not in";
            ids.push(...this.getIds());
        }
        const arr = [...this.props.domain]
        const dynamicFilters = [
            {
                description: _t("View Type %s", "form"),
                domain: arr,
            },
        ];
        // fine for now but we don't like this kind of dependence of core to views
        const SelectCreateDialog = registry.category("dialogs").get("select_create");
        this.addDialog(SelectCreateDialog, {
            title: _t("Search: %s", fieldString),
            dynamicFilters,
            resModel,
            noCreate: true,
            multiSelect,
            context: this.props.context || {},
            onSelected: (resId) => {
                const resIds = Array.isArray(resId) ? resId : [resId];
                this.props.update([...resIds]);
            },
        });
    }

    /**
     * Returns the domain to exclude already selected records.
     * @returns {Array} - Odoo domain array.
     */
    getDomain() {
        const domainIds = Domain.not([["id", "in", this.getIds()]]);
        if (this.props.domain) {
            return Domain.and([this.props.domain, domainIds]).toList();
        }
        return domainIds.toList();
    }

    /**
     * Handles selection from the autocomplete dropdown.
     * Executes the provided action if present, else updates selected IDs.
     * @param {Object} param0 - Object containing value and action
     * @param {Object} params - Optional additional parameters
     */
    onSelect({value: resId, action}, params) {
        if (action) {
            return action(params);
        }
        this.props.update([resId]);
    }

    /**
     * Calls the ORM name_search method with the domain and context.
     * @param {String} name - Name to search for
     * @param {Number} limit - Maximum number of results
     * @returns {Promise<Array>} - Array of [id, name] tuples
     */
    search(name, limit) {
        const domain = this.getDomain();
        return this.orm.call(this.props.resModel, "name_search", [], {
            name,
            args: domain,
            limit,
            context: this.props.context || {},
        });
    }

    /**
     * Clears selected records if input value is empty.
     * @param {Object} param0 - Object containing inputValue
     */
    onChange({inputValue}) {
        if (!inputValue.length) {
            this.props.update([]);
        }
    }
}