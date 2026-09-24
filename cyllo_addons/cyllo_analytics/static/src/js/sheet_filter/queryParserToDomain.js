/* @odoo-module */
export const parseQueryToDomain = (query, tables) => {
    const parseCondition = (condition) => {
        const regex = /(\w+)\.(\w+)\s+(IN|NOT IN|>=|<=|=|!=|>|<|ILIKE|NOT ILIKE|IS NOT NULL|IS NULL|SET|NOT_SET)\s*(\(([^)]+)\)|('[^']+'|".+"|\S+))?/i;

        const match = condition.match(regex);
        if (!match) {
            return [{error: true, errorMsg: 'Invalid query format'}];
        }

        const [, table, field, operator, , values, singleValue] = match;
        const tableModel = tables.find(obj => obj.table === table);
        if (!tableModel) {
            return [{error: true, errorMsg: `Table ${table} not found in models`}];
        }

        let valueArray;
        if (values) {
            valueArray = values.split(',').map(v => {
                const trimmedValue = v.trim().replace(/^['"]|['"]$/g, '');
                const parsedValue = parseInt(trimmedValue, 10);
                return isNaN(parsedValue) ? trimmedValue : parsedValue;
            });
        }

        let pyOperator;
        switch (operator.toUpperCase()) {
            case 'IN':
                pyOperator = 'in';
                break;
            case 'NOT IN':
                pyOperator = 'not in';
                break;
            case '=':
                pyOperator = '=';
                break;
            case '!=':
                pyOperator = '!=';
                break;
            case '>':
                pyOperator = '>';
                break;
            case '>=':
                pyOperator = '>=';
                break;
            case '<':
                pyOperator = '<';
                break;
            case '<=':
                pyOperator = '<=';
                break;
            case 'ILIKE':
                pyOperator = 'ilike';
                break;
            case 'NOT ILIKE':
                pyOperator = 'not ilike';
                break;
            case 'IS NOT NULL':
                return [field, '!=', false];
            case 'IS NULL':
                return [field, '=', false];
            case 'SET':
                return [field, 'set', true];
            case 'NOT_SET':
                return [field, 'not_set', true];
            default:
                return [{error: true, errorMsg: `Unsupported operator ${operator}`}];
        }

        let value = valueArray || (singleValue ? singleValue.replace(/^['"]|['"]$/g, '') : true);
        if (tableModel.fields[field].type === 'many2one') {
            value = Array.isArray(value) ? value.map(v => parseInt(v)) : [parseInt(value)];

        }
        if (typeof value === "string") {
            if (value.toUpperCase() === "FALSE") {
                value = false
            }
            else if(value.toUpperCase() === "TRUE"){
                value = true
            }
        }
        return [field, pyOperator, value];
    };

    const conditions = query.split(/\s+OR\s+/i).map(cond => cond.trim());
    const domains = conditions.map(parseCondition);
    if (domains.some(dom => dom.find(item => item.error))) {
        return {error: true, errorMsg: "This query is not supported for editing"};
    }

    const domainObjects = [];
    let currentDomain = null;

    conditions.forEach((condition, index) => {
        const [, table] = condition.match(/(\w+)\./);
        const objData = tables.find(obj => obj.table === table);
        const domain = domains[index];

        if (!currentDomain || currentDomain.table !== objData.table) {
            currentDomain = {
                ...objData,
                domain: [domain],
            };
            domainObjects.push(currentDomain);
        } else {
            if (currentDomain.domain.length > 0) {
                currentDomain.domain.splice(0, 0, '|');
            }
            currentDomain.domain.push(domain);
        }
    });

    return {
        error: false,
        domains: domainObjects.map(obj => ({
            ...obj,
            domain: JSON.stringify(obj.domain),
        })),
    };
};