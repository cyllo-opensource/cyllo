/** @odoo-module **/

/**
 * Generates a safe SQL alias from a column name or a label.
 * @param {string} base - The base string (e.g., column name or field label).
 * @param {boolean} isPreset - Whether the item is a calculation preset.
 * @returns {string} A safe SQL alias.
 */
export function generateSqlAlias(base, isPreset = false) {
    if (!base) return "expr_" + Math.random().toString(36).substring(2, 7);

    // For regular columns (table.field), replace dot with underscore
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
