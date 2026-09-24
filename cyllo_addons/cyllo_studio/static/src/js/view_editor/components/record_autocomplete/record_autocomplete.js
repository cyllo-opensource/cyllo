/** @odoo-module **/
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";
import { useOwnedDialogs, useService } from "@web/core/utils/hooks";
import { RecordAutocomplete } from "@web/core/record_selectors/record_autocomplete";

const SEARCH_LIMIT = 7;
const SEARCH_MORE_LIMIT = 320;

/**
 * CylloRecordAutocomplete
 *
 * Extends Odoo's RecordAutocomplete to support:
 * - Multi-selection (optional)
 * - Dynamic domain filtering
 * - "Search More" modal for extended results
 *
 * Props:
 *  - resModel: The model to search records from
 *  - update: Callback to update selected records
 *  - multiSelect: Enable multiple selection
 *  - getIds: Function returning current record IDs
 *  - value: Current search input
 *  - domain: Optional domain for filtering
 *  - context: Optional context
 *  - className: Optional CSS class
 *  - fieldString: Field label for modal dialog
 *  - placeholder: Placeholder text
 */
export class CylloRecordAutocomplete extends RecordAutocomplete {

    static props = {
        resModel: String,
        update: Function,
        multiSelect: Boolean,
        getIds: Function,
        value: String,
        domain: { type: Array, optional: true },
        context: { type: Object, optional: true },
        className: { type: String, optional: true },
        fieldString: { type: String, optional: true },
        placeholder: { type: String, optional: true },
    };
    static components = { AutoComplete };
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

    addNames(options) {
        const displayNames = Object.fromEntries(options);
        this.nameService.addDisplayNames(this.props.resModel, displayNames);
    }

    getIds() {
        return this.props.getIds();
    }

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
            options.push({ label: _t("(no result)"), unselectable: true });
        }
        return options;
    }

    async onSearchMore(name) {
        const { fieldString, multiSelect, resModel } = this.props;
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

    getDomain() {
        const domainIds = Domain.not([["id", "in", this.getIds()]]);
        if (this.props.domain) {
            return Domain.and([this.props.domain, domainIds]).toList();
        }
        return domainIds.toList();
    }

    onSelect({ value: resId, action }, params) {
        if (action) {
            return action(params);
        }
        this.props.update([resId]);
    }

    search(name, limit) {
        const domain = this.getDomain();
        return this.orm.call(this.props.resModel, "name_search", [], {
            name,
            args: domain,
            limit,
            context: this.props.context || {},
        });
    }

    onChange({ inputValue }) {
        if (!inputValue.length) {
            this.props.update([]);
        }
    }
}