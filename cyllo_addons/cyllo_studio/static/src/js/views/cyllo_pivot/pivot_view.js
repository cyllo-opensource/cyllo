/** @odoo-module */

/**
 * CylloPivotView
 *
 * Custom Pivot View definition extending Odoo's default `pivotView`.
 *
 * Key Features:
 * ----------------
 * 1. Uses a custom `CylloPivotRenderer` to extend rendering logic.
 * 2. Dynamically constructs pivot `modelParams` from either:
 *    - Preloaded state (when available), or
 *    - Parsing the XML arch definition using the view’s ArchParser.
 * 3. Ensures fallback behavior:
 *    - Adds `__count` as a default measure when no measures are active.
 *    - Normalizes boolean flags (`sticky`, `disableLinking`, `displayQuantity`).
 *    - Supports additional attributes like `colPath`, `rowPath`, and `measurePath`.
 * 4. Registers itself as the global `pivot` view in the Odoo view registry,
 *    replacing the default implementation (`force: true`).
 *
 * Purpose:
 * ---------
 * Allows Cyllo Studio to integrate a customized Pivot view pipeline,
 * making metadata extraction and rendering extensible for advanced
 * editor functionality.
 */
import {
    _t
} from "@web/core/l10n/translation";
import {
    registry
} from "@web/core/registry";
import {
    pivotView
} from "@web/views/pivot/pivot_view";
import {
    CylloPivotRenderer
} from './pivot_renderer'

export const CylloPivotView = {
    ...pivotView,
    Renderer: CylloPivotRenderer,

      /**
     * Override props to inject custom pivot metadata into the model.
     *
     * @param {Object} genericProps - Standard props passed by the view manager.
     * @param {Object} view - The pivot view definition, including ArchParser & Model.
     * @returns {Object} - Enhanced props containing pivot-specific `modelParams`.
     */
    props: (genericProps, view) => {
        const modelParams = {};
        if (genericProps.state && false) {
            modelParams.data = genericProps.state.data;
            modelParams.metaData = genericProps.state.metaData;
        } else {
            const {
                arch,
                fields,
                resModel
            } = genericProps;
            // parse arch
            const archInfo = new view.ArchParser().parse(arch);
            if (!archInfo.activeMeasures.length || archInfo.displayQuantity) {
                archInfo.activeMeasures.unshift("__count");
            }
            modelParams.metaData = {
                activeMeasures: archInfo.activeMeasures,
                colGroupBys: archInfo.colGroupBys,
                defaultOrder: archInfo.defaultOrder,
                disableLinking: Boolean(archInfo.disableLinking),
                displayQuantity: Boolean(archInfo.displayQuantity),
                sticky: Boolean(archInfo.sticky),
                fields: fields,
                fieldAttrs: archInfo.fieldAttrs,
                resModel: resModel,
                rowGroupBys: archInfo.rowGroupBys,
                title: archInfo.title || _t("Untitled"),
                widgets: archInfo.widgets,
                colPath: archInfo.colPath,
                rowPath: archInfo.rowPath,
                measurePath: archInfo.measurePath,
            };
        }

        return {
            ...genericProps,
            Model: view.Model,
            modelParams,
            Renderer: view.Renderer,
        };
    }
};

registry.category("views").add("pivot", CylloPivotView, {
    force: true
});