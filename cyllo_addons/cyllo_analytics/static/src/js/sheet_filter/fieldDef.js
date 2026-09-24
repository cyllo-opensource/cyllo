/* @odoo-module */

/**
 * Returns a SQL fragment for a date-period operator.
 * The returned string is appended after "field_name " to form the WHERE clause.
 */
function _getPeriodSql(operator) {
    const periodMap = {
        "this_week": `>= DATE_TRUNC('week', CURRENT_DATE) AND {field} < DATE_TRUNC('week', CURRENT_DATE) + INTERVAL '1 week'`,
        "last_week": `>= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week' AND {field} < DATE_TRUNC('week', CURRENT_DATE)`,
        "this_month": `>= DATE_TRUNC('month', CURRENT_DATE) AND {field} < DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'`,
        "last_month": `>= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month' AND {field} < DATE_TRUNC('month', CURRENT_DATE)`,
        "this_quarter": `>= DATE_TRUNC('quarter', CURRENT_DATE) AND {field} < DATE_TRUNC('quarter', CURRENT_DATE) + INTERVAL '3 months'`,
        "last_quarter": `>= DATE_TRUNC('quarter', CURRENT_DATE) - INTERVAL '3 months' AND {field} < DATE_TRUNC('quarter', CURRENT_DATE)`,
        "this_year": `>= DATE_TRUNC('year', CURRENT_DATE) AND {field} < DATE_TRUNC('year', CURRENT_DATE) + INTERVAL '1 year'`,
        "last_year": `>= DATE_TRUNC('year', CURRENT_DATE) - INTERVAL '1 year' AND {field} < DATE_TRUNC('year', CURRENT_DATE)`,
    };
    return periodMap[operator] || '= CURRENT_DATE';
}

export function getPsqlOperatorsAndValues(fieldDef) {
    const operatorsMapping = {
        "many2many": {
            "in": { type: 'array_of_int', operator: 'IN' },
            "not in": { type: 'array_of_int', operator: 'NOT IN' },
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        },
        "many2one": {
            "=": { type: 'int', operator: '=' },
            "!=": { type: 'int', operator: '!=' },
            "in": { type: 'array_of_int', operator: 'IN' },
            "not in": { type: 'array_of_int', operator: 'NOT IN' },
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        },
        "one2many": {
            "in": { type: 'array_of_int', operator: 'IN' },
            "not in": { type: 'array_of_int', operator: 'NOT IN' }
        },
        "boolean": {
            "is": { type: 'boolean', operator: 'IS TRUE' },
            "is_not": { type: 'boolean', operator: 'IS FALSE' }
        },
        "selection": {
            "=": { type: 'string', operator: '=' },
            "!=": { type: 'string', operator: '!=' },
            "in": { type: 'array_of_string', operator: 'IN' },
            "not in": { type: 'array_of_string', operator: 'NOT IN' },
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        },
        "char": {
            "=": { type: 'string', operator: '=' },
            "!=": { type: 'string', operator: '!=' },
            "ilike": { type: 'string', operator: 'ILIKE' },
            "not ilike": { type: 'string', operator: 'NOT ILIKE' },
            "in": { type: 'array_of_string', operator: 'IN' },
            "not in": { type: 'array_of_string', operator: 'NOT IN' },
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        },
        "text": {
            "=": { type: 'string', operator: '=' },
            "!=": { type: 'string', operator: '!=' },
            "ilike": { type: 'string', operator: 'ILIKE' },
            "not ilike": { type: 'string', operator: 'NOT ILIKE' },
            "in": { type: 'array_of_string', operator: 'IN' },
            "not in": { type: 'array_of_string', operator: 'NOT IN' },
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        },
        "html": {
            "=": { type: 'string', operator: '=' },
            "!=": { type: 'string', operator: '!=' },
            "ilike": { type: 'string', operator: 'ILIKE' },
            "not ilike": { type: 'string', operator: 'NOT ILIKE' },
            "in": { type: 'array_of_string', operator: 'IN' },
            "not in": { type: 'array_of_string', operator: 'NOT IN' },
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        },
        "date": {
            "=": { type: 'date', operator: '=' },
            "!=": { type: 'date', operator: '!=' },
            ">": { type: 'date', operator: '>' },
            ">=": { type: 'date', operator: '>=' },
            "<": { type: 'date', operator: '<' },
            "<=": { type: 'date', operator: '<=' },
            "in_period": { type: 'period', operator: 'IN_PERIOD' },
            "between": { type: 'date_range', operator: 'BETWEEN' },
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        },
        "datetime": {
            "=": { type: 'datetime', operator: '=' },
            "!=": { type: 'datetime', operator: '!=' },
            ">": { type: 'datetime', operator: '>' },
            ">=": { type: 'datetime', operator: '>=' },
            "<": { type: 'datetime', operator: '<' },
            "<=": { type: 'datetime', operator: '<=' },
            "in_period": { type: 'period', operator: 'IN_PERIOD' },
            "between": { type: 'date_range', operator: 'BETWEEN' },
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        },
        "integer": {
            "=": { type: 'int', operator: '=' },
            "!=": { type: 'int', operator: '!=' },
            ">": { type: 'int', operator: '>' },
            ">=": { type: 'int', operator: '>=' },
            "<": { type: 'int', operator: '<' },
            "<=": { type: 'int', operator: '<=' },
            "in": { type: 'array_of_int', operator: 'in' },
            "contains": { type: 'string', operator: 'LIKE' },
            "ilike": { type: 'string', operator: 'ILIKE' },
            "between": { type: 'array_of_int', operator: 'BETWEEN' },
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        },
        "float": {
            "=": { type: 'float', operator: '=' },
            "!=": { type: 'float', operator: '!=' },
            ">": { type: 'float', operator: '>' },
            ">=": { type: 'float', operator: '>=' },
            "<": { type: 'float', operator: '<' },
            "<=": { type: 'float', operator: '<=' },
            "ilike": { type: 'string', operator: 'ILIKE' },
            "between": { type: 'array_of_float', operator: 'BETWEEN' },
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        },
        "monetary": {
            "=": { type: 'float', operator: '=' },
            "!=": { type: 'float', operator: '!=' },
            ">": { type: 'float', operator: '>' },
            ">=": { type: 'float', operator: '>=' },
            "<": { type: 'float', operator: '<' },
            "<=": { type: 'float', operator: '<=' },
            "between": { type: 'array_of_float', operator: 'BETWEEN' },
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        },
        "json": {
            "=": { type: 'object', operator: '=' },
            "!=": { type: 'object', operator: '!=' },
            "contains": { type: 'object', operator: '@>' },
            "not contains": { type: 'object', operator: '<@' },
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        },
        "properties": {
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        },
        "default": {
            "=": { type: 'unknown type', operator: '=' },
            "!=": { type: 'unknown type', operator: '!=' },
            ">": { type: 'unknown type', operator: '>' },
            ">=": { type: 'unknown type', operator: '>=' },
            "<": { type: 'unknown type', operator: '<' },
            "<=": { type: 'unknown type', operator: '<=' },
            "ilike": { type: 'string', operator: 'ILIKE' },
            "not ilike": { type: 'string', operator: 'NOT ILIKE' },
            "like": { type: 'string', operator: 'LIKE' },
            "not like": { type: 'string', operator: 'NOT LIKE' },
            "in": { type: 'array', operator: 'IN' },
            "not in": { type: 'array', operator: 'NOT IN' },
            "set": { type: 'boolean', operator: 'IS NOT NULL' },
            "not_set": { type: 'boolean', operator: 'IS NULL' }
        }
    };
    let isvalid = true
    if (!fieldDef) {
        return [{}, "", isvalid];
    }
    const { type, operator, value } = fieldDef;

    const field = operatorsMapping[type] || operatorsMapping["default"]
    const returnValue = field[operator]

    // Handle "in period" operator — value is the period name (e.g. "this_month")
    if (returnValue && returnValue.type === 'period') {
        const periodSql = _getPeriodSql(value);
        return [returnValue, periodSql, true];
    }

    // Handle date range (between) for date/datetime fields
    if (returnValue && returnValue.type === 'date_range') {
        if (Array.isArray(value) && value.length === 2) {
            const [start, end] = value;
            return [returnValue, `BETWEEN '${start}' AND '${end}'`, true];
        }
        return [returnValue, `BETWEEN '' AND ''`, false];
    }
    let groupRhs = ''
    if (typeof value === "boolean") {
        if (operator === "=" && value) {
            groupRhs = "= TRUE"
        }
        else if (operator === "=" && !value) {
            groupRhs = "= FALSE"
        }
        else if (operator === "!=" && !value) {
            groupRhs = "= TRUE"
        }
        else if (operator === "!=" && value) {
            groupRhs = "= FALSE"
        }
        else {
            groupRhs = value ? "IS NULL" : "IS NOT NULL";
        }

    } else if (Array.isArray(value)) {
        const rhsFormatted = value.map(v => {
            if (type === 'date' || type === 'datetime') {
                return `'${v}'`;  // Dates and datetimes should be quoted
            }
            const intValue = parseInt(v, 10);
            return isNaN(intValue) ? `'${v}'` : intValue;  // Use quotes for non-numeric values
        }).join(', ');
        isvalid = value.length > 0;
        groupRhs = `${returnValue.operator} (${rhsFormatted})`;
    } else {
        let formattedRhs;
        if (type === 'date' || type === 'datetime') {
            formattedRhs = `'${value}'`;  // Dates and datetimes should be quoted
            isvalid = formattedRhs.length > 0;
        } else {
            const rhsValue = parseInt(value, 10);
            formattedRhs = isNaN(rhsValue) ? `'${value}'` : rhsValue;  // Use quotes for non-numeric values
            isvalid = isNaN(rhsValue) ? Boolean(formattedRhs.length) : Boolean(formattedRhs)
        }
        groupRhs = `${returnValue.operator} ${formattedRhs}`;
    }
    return [returnValue, groupRhs, isvalid];
}