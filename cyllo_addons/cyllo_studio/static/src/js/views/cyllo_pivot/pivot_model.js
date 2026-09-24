/** @odoo-module */

/**
 * Patch: PivotModel.load
 *
 * Overrides the default PivotModel load method to enhance Studio behavior.
 *
 * Features:
 * 1. Supports custom pivot measures from `searchParams.context.pivot_measures`.
 * 2. Merges row and column groupings from both searchParams and existing metadata.
 * 3. Maintains a record of loaded active measures (`loadedActiveMeasures`) and row groupings (`loadedRowGroupBy`).
 * 4. Ensures measures are computed via `computeReportMeasures` for the pivot view.
 * 5. Resets expanded row/column groupings when groupings change.
 *
 * Purpose:
 * Allows Cyllo Studio to persist and manipulate pivot view configurations
 * while keeping Odoo’s pivot functionality intact.
 */
import {
    PivotModel
} from "@web/views/pivot/pivot_model";
import {
    patch
} from "@web/core/utils/patch";
import {
    computeReportMeasures,
    processMeasure
} from "@web/views/utils";

patch(PivotModel.prototype, {
    /**
     * @override
     *
     * Loads and prepares pivot metadata and measures based on both Studio
     * configuration and Odoo's default pivot model.
     *
     * @param {Object} searchParams - The parameters for the pivot query.
     * @param {Object} searchParams.context - Context dictionary containing
     *     Studio-specific keys:
     *       - pivot_measures: Array of custom measures to be used.
     *       - pivot_row_groupby: Array of row groupings to persist.
     *       - pivot_column_groupby: Array of column groupings to persist.
     * @param {Array} searchParams.groupBy - Default Odoo groupBy fields.
     *
     * @returns {Promise<Object>} - Returns a promise resolving to the
     *     loaded pivot data and updated metadata.
     *
     * Behavior:
     * - Processes custom measures if defined.
     * - Merges new groupings with previously loaded ones.
     * - Clears expanded groupings when definitions differ.
     * - Recomputes measures to ensure alignment with active metadata.
     */
    async load(searchParams) {
        this.searchParams = searchParams;
        const processedMeasures = processMeasure(searchParams.context.pivot_measures);
        const activeMeasures = processedMeasures || this.metaData.activeMeasures;
        const metaData = this._buildMetaData({
            activeMeasures
        });
        metaData.loadedActiveMeasures = [...processedMeasures || []]
        if (!this.reload) {
            metaData.rowGroupBys = [...searchParams.context.pivot_row_groupby || [], ...searchParams.groupBy, ...metaData.rowGroupBys]
            metaData.loadedRowGroupBy = [...searchParams.context.pivot_row_groupby || [], ...searchParams.groupBy]
            metaData.activeMeasures = [...new Set([
                ...(metaData.activeMeasures || []),
                ...(this.metaData.activeMeasures || [])
            ])];


            this.reload = true;
        } else {
            metaData.rowGroupBys = [...searchParams.groupBy, ...searchParams.context.pivot_row_groupby || [], ...metaData.rowGroupBys]
            metaData.loadedRowGroupBy = [...searchParams.groupBy, ...searchParams.context.pivot_row_groupby || []]
            metaData.activeMeasures = [...new Set([
                ...(metaData.activeMeasures || []),
                ...(this.metaData.activeMeasures || [])
            ])];

        }
        metaData.colGroupBys =
            searchParams.context.pivot_column_groupby || this.metaData.colGroupBys;

        if (JSON.stringify(metaData.rowGroupBys) !== JSON.stringify(this.metaData.rowGroupBys)) {
            metaData.expandedRowGroupBys = [];
        }
        if (JSON.stringify(metaData.colGroupBys) !== JSON.stringify(this.metaData.colGroupBys)) {
            metaData.expandedColGroupBys = [];
        }

        const allActivesMeasures = new Set(this.metaData.activeMeasures);
        if (processedMeasures) {
            processedMeasures.forEach((e) => allActivesMeasures.add(e));
        }

        metaData.measures = computeReportMeasures(metaData.fields, metaData.fieldAttrs, [
            ...allActivesMeasures,
        ]);
        const config = {
            metaData,
            data: this.data
        };
        return this._loadData(config);
    }
})