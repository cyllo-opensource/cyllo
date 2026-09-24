/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { RecordSelector } from "@web/core/record_selectors/record_selector";
    import { CylloRecordAutocomplete } from "@cyllo_studio/js/view_editor/components/record_autocomplete/record_autocomplete";

/**
 * CylloRecordSelector
 *
 * Custom record selector component extending Odoo's `RecordSelector`.
 * Provides functionality to:
 * - Fetch and display the human-readable name of a single selected record
 * - Handle record changes via update callbacks
 * - Integrate with Cyllo's custom `CylloRecordAutocomplete` for record searching
 */
export class CylloRecordSelector extends RecordSelector {
    static props = {
        resId: [Number, { value: false }],
        resModel: String,
        update: Function,
        domain: { type: Array, optional: true },
        context: { type: Object, optional: true },
        fieldString: { type: String, optional: true },
        placeholder: { type: String, optional: true },
    };

    static components = { CylloRecordAutocomplete };
    static template = "cyllo_studio.RecordSelector";

    setup() {
        this.nameService = useService("name");
        onWillStart(() => this.computeDerivedParams());
        onWillUpdateProps((nextProps) => this.computeDerivedParams(nextProps));
    }

    /**
     * Compute display-related parameters.
     * Loads display names for the current record(s)
     * and resolves the label to show.
     *
     * @param {Object} [props=this.props] - Component props
     */
    async computeDerivedParams(props = this.props) {
        const displayNames = await this.getDisplayNames(props);
        this.displayName = this.getDisplayName(props, displayNames);
    }

    async getDisplayNames(props) {
        const ids = this.getIds(props);
        return this.nameService.loadDisplayNames(props.resModel, ids);
    }

    /**
     * Resolve display name for the selected record.
     *
     * @param {Object} [props=this.props] - Component props
     * @param {Object} displayNames - Mapping of IDs to display names
     * @returns {string} Human-readable record name or fallback text
     */
    getDisplayName(props = this.props, displayNames) {
        const { resId } = props;
        if (resId === false) {
            return "";
        }
        return typeof displayNames[resId] === "string"
            ? displayNames[resId]
            : _t("Inaccessible/missing record ID: %s", resId);
    }

    getIds(props = this.props) {
        if (props.resId) {
            return [props.resId];
        }
        return [];
    }

    /**
     * Update selected record.
     * Passes the chosen record ID back to the parent component
     * and re-renders the view.
     *
     * @param {Array<number>} resIds - Array of record IDs
     */
    update(resIds) {
        this.props.update(resIds[0] || false);
        this.render(true);
    }
}
