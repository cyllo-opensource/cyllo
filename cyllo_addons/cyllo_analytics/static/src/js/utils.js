/** @odoo-module **/

/**
 * Generates a safe SQL alias from a column name or a label.
 * @param {string} base - The base string (e.g., column name or field label).
 * @param {boolean} isPreset - Whether the item is a calculation preset.
 * @returns {string} A safe SQL alias.
 */
export function generateSqlAlias(base, isPreset = false) {
    if (!base) return "expr_" + Math.random().toString(36).substring(2, 7);
    if (!isPreset && base.includes('.')) {
        return base.replace('.', '_');
    }

    // For presets or custom expressions, generate a safe name
    let alias = base
        .toLowerCase()
        .replace(/[^a-z0-9_]/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_+|_+$/g, '')
        .substring(0, 30);

    if (!alias) {
        return "expr_" + Math.random().toString(36).substring(2, 7);
    }
    if (/^[0-9]/.test(alias)) {
        alias = "col_" + alias;
    }
    return alias.substring(0, 30);
}

/**
 * Generates a SQL expression for currency conversion.
 * @param {string} column - The column name.
 * @param {string} modelName - The model table name.
 * @param {number} companyId - The current company ID.
 * @returns {string} The SQL expression.
 */
export function getMonetaryExpression(column, modelName, companyId) {
    const currency_rate = `(COALESCE((
        SELECT rate FROM res_currency_rate
        WHERE currency_id = ${modelName}.currency_id
        AND company_id = ${companyId}
        ORDER BY name DESC LIMIT 1
    ), 1) / COALESCE((
        SELECT rate FROM res_currency_rate
        WHERE currency_id = {selectedCurrency}
        AND company_id = ${companyId}
        ORDER BY name DESC LIMIT 1
    ), 1))`;

    return `ROUND(${column} / ${currency_rate}, 2)`;
}

/**
 * The dashboard.sheet fields a KPI needs, and the shape KpiSheetChart wants
 * them in.
 *
 * The deck editor and the player both mount that component and both read
 * their sheet config with their own orm.read, so the field list and the
 * mapping live here rather than being written out twice and drifting.
 */
export const KPI_SHEET_FIELDS = [
    "kpi_target", "kpi_view", "kpi_description", "kpi_redirect",
    "kpi_icon", "kpi_model",
];

/**
 * @param {Object} config - a dashboard.sheet read with KPI_SHEET_FIELDS.
 * @returns {Object} the `kpi` prop for KpiSheetChart, matching what the
 *                   dashboard builds in getKpi().
 */
export function kpiSettingsFromSheet(config) {
    return {
        description: config.kpi_description,
        redirect: config.kpi_redirect,
        target: config.kpi_target,
        measureView: config.kpi_view,
        icon: config.kpi_icon,
        model: config.kpi_model,
    };
}

export async function fetchSheetStyling(orm, sheetIds) {
    const bySheet = {};
    if (!sheetIds.length) return bySheet;
    const [mappings, annotations] = await Promise.all([
        orm.searchRead("dashboard.sheet.color.mapping", [["sheet_id", "in", sheetIds]],
            ["measure_alias", "min_value", "max_value", "color", "indicator", "notes", "sheet_id"]),
        orm.searchRead("dashboard.sheet.annotation", [["sheet_id", "in", sheetIds]],
            ["measure_alias", "dimension_label", "notes", "sheet_id"]),
    ]);
    const entry = (id) => (bySheet[id] ||= { color_mappings: [], annotations: [] });
    mappings.forEach((m) => entry(m.sheet_id[0]).color_mappings.push(m));
    annotations.forEach((a) => entry(a.sheet_id[0]).annotations.push(a));
    return bySheet;
}
