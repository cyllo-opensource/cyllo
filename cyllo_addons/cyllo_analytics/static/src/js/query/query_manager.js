/** @odoo-module **/

/**
 * SQLQueryParser class for parsing SQL queries and extracting relevant information.
 * @class
 */
export class SQLQueryParser {
    /**
     * Initializes the SQLQueryParser class with a given SQL query.
     * @constructor
     * @param {string} query - The SQL query to be parsed.
     */
    constructor(query) {
        this.query = query.replaceAll('public.', '');
    }

    /**
     * Parses the SQL query and extracts various components.
     * @function
     * @returns {Object} - An object containing information about joins, columns, where conditions,
     *                    group by columns, order by columns, and limit.
     */
    parse() {
        const tables = this.extractTables();
        if (tables.length > 0 && tables[0].model) {
            this.query = this.query.replace(/\bSELECT\s+\*\s/gi, `SELECT ${tables[0].model}.id `);
            this.query = this.query.replace(/\bCOUNT\(\s*\*\s*\)/gi, `COUNT(${tables[0].model}.id)`);
        }
        const columns = this.extractColumns();
        const where = this.extractWhereConditions();
        const groupBy = this.extractGroupByColumns();
        const orderBy = this.extractOrderBy();
        const limit = this.extractLimit();
        const joins = this.extractJoins();
        joins.forEach(item => tables.push(item))
        return {
            joins: tables,
            columns,
            where,
            groupBy,
            orderBy,
            limit,
        };
    }

    getMaskedQuery() {
        let result = "";
        let brackets = 0;
        let inString = false;
        let stringChar = '';
        for (let i = 0; i < this.query.length; i++) {
            const char = this.query[i];
            
            if (inString) {
                result += "#";
                if (char === stringChar && this.query[i - 1] !== '\\') inString = false;
            } else {
                if (char === "'" || char === '"') {
                    inString = true;
                    stringChar = char;
                    result += "#";
                } else if (char === '(') {
                    brackets++;
                    result += "#";
                } else if (char === ')') {
                    brackets--;
                    result += "#";
                } else if (brackets > 0) {
                    result += "#";
                } else {
                    result += char;
                }
            }
        }
        return result;
    }

    /**
     * Extracts the tables involved in the SQL query.
     * @function
     * @returns {Array} - An array of table information objects.
     */
    extractTables() {
        const maskedQuery = this.getMaskedQuery();
        const regex = /\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*))?/i;
        const match = maskedQuery.match(regex);
        if (match) {
            const model = match[1];
            let alias = match[2] || false;
            if (alias && /^(WHERE|GROUP|ORDER|LIMIT|JOIN|ON|HAVING)$/i.test(alias)) {
                alias = false;
            }
            const join = alias ? `${model} AS ${alias}` : model;
            return [{
                join,
                model,
                alias,
                name: false,
                linked: false,
                field: false
            }];
        }
        return [];
    }

    splitByCommaOutsideParentheses(str) {
        const result = [];
        let brackets = 0;
        let current = "";
        for (let i = 0; i < str.length; i++) {
            const char = str[i];
            if (char === '(') brackets++;
            else if (char === ')') brackets--;
            
            if (char === ',' && brackets === 0) {
                result.push(current.trim());
                current = "";
            } else {
                current += char;
            }
        }
        if (current.trim()) result.push(current.trim());
        return result;
    }

    /**
     * Extracts the columns selected in the SQL query.
     * @function
     * @returns {Array} - An array of column information objects.
     */
    extractColumns() {
        const maskedQuery = this.getMaskedQuery();
        const selectMatch = maskedQuery.match(/\bSELECT\b/i);
        const fromMatch = maskedQuery.match(/\bFROM\b/i);
        
        if (selectMatch && fromMatch && selectMatch.index < fromMatch.index) {
            const startIndex = selectMatch.index + 6;
            const columnStr = this.query.substring(startIndex, fromMatch.index).trim();
            const columns = this.splitByCommaOutsideParentheses(columnStr).map((column) => {
                let matchAlias = column.match(/^([\s\S]*?)(?:\s+AS\s+([\s\S]+))?$/i);
                let name = matchAlias ? matchAlias[1].trim() : column.trim();
                let alias = matchAlias && matchAlias[2] ? matchAlias[2].trim() : false;
                let query = column.trim()
                if (!alias) {
                    alias = name.replaceAll(/['"\.]/g, '_').replace(/[^a-zA-Z0-9_]/g, '');
                    query = `${query} AS ${alias}`
                }
                return {
                    column: name,
                    alias,
                    query,
                    value: name.replace(/\./g, ' > ')
                };
            });
            return columns;
        }
        return [];
    }

    /**
     * Extracts the WHERE conditions from the SQL query.
     * @function
     * @returns {Array} - An array of where condition objects.
     */
    extractWhereConditions() {
        const maskedQuery = this.getMaskedQuery();
        const whereMatch = maskedQuery.match(/\bWHERE\b/i);
        if (whereMatch) {
            const startStr = maskedQuery.substring(whereMatch.index + 5);
            const endMatch = startStr.match(/\b(GROUP BY|ORDER BY|LIMIT)\b/i);
            const rawLength = endMatch ? endMatch.index : startStr.length;
            
            const conditionStr = this.query.substring(whereMatch.index + 5, whereMatch.index + 5 + rawLength).trim();
            const conditions = conditionStr.split(/\sAND\s/i);
            const whereConditions = conditions.map((condition, index) => {
                return {
                    name: `Filter ${index + 1}`,
                    domain: ` ${condition}`,
                    active: true,
                    id: new Date().toISOString(), //temp Id
                    domain_py_expression: []
                };
            });
            return whereConditions;
        }
        return [];
    }

    /**
     * Extracts the GROUP BY columns from the SQL query.
     * @function
     * @returns {Array} - An array of group by column information objects.
     */
    extractGroupByColumns() {
        const maskedQuery = this.getMaskedQuery();
        const groupMatch = maskedQuery.match(/\bGROUP BY\b/i);
        if (groupMatch) {
            const startStr = maskedQuery.substring(groupMatch.index + 8);
            const endMatch = startStr.match(/\b(ORDER BY|LIMIT)\b/i);
            const rawLength = endMatch ? endMatch.index : startStr.length;
            
            const columnStr = this.query.substring(groupMatch.index + 8, groupMatch.index + 8 + rawLength).trim();
            const columns = this.splitByCommaOutsideParentheses(columnStr).map((column) => {
                let matchAlias = column.match(/^([\s\S]*?)(?:\s+AS\s+([\s\S]+))?$/i);
                let name = matchAlias ? matchAlias[1].trim() : column.trim();
                let alias = matchAlias && matchAlias[2] ? matchAlias[2].trim() : false;
                return {
                    column: name,
                    alias: alias || false,
                    query: column.trim(),
                    value: name.replace(/\./g, ' > ')
                };
            });
            return columns;
        }
        return [];
    }

    /**
     * Extracts the ORDER BY columns from the SQL query.
     * @function
     * @returns {Array} - An array of order by column information objects.
     */
    extractOrderBy() {
        const maskedQuery = this.getMaskedQuery();
        const orderMatch = maskedQuery.match(/\bORDER BY\b/i);
        if (orderMatch) {
            const startStr = maskedQuery.substring(orderMatch.index + 8);
            const endMatch = startStr.match(/\b(LIMIT)\b/i);
            const rawLength = endMatch ? endMatch.index : startStr.length;
            
            const columnStr = this.query.substring(orderMatch.index + 8, orderMatch.index + 8 + rawLength).trim();
            const columns = this.splitByCommaOutsideParentheses(columnStr).map((column) => {
                let matchAlias = column.match(/^([\s\S]*?)(?:\s+AS\s+([\s\S]+))?$/i);
                let name = matchAlias ? matchAlias[1].trim() : column.trim();
                let alias = matchAlias && matchAlias[2] ? matchAlias[2].trim() : false;
                const cleanName = name.replace(/\s+(DESC|ASC)$/i, '').trim(); // Remove DESC or ASC and trim
                return {
                    column: cleanName,
                    alias: alias || false,
                    query: column.trim(),
                    value: cleanName.replace(/\./g, ' > ')
                };
            });
            return columns;
        }
        return [];
    }

    /**
     * Extracts the LIMIT value from the SQL query.
     * @function
     * @returns {number|null} - The limit value or null if not present.
     */
    extractLimit() {
        // Use the masked query so that LIMIT inside subqueries (e.g. COALESCE subqueries)
        // are hidden and we only match the top-level LIMIT clause.
        const maskedQuery = this.getMaskedQuery();
        const regex = /\bLIMIT\s+(\d+)/i;
        const match = maskedQuery.match(regex);
        return match ? parseInt(match[1]) : null;
    }

    /**
     * Extracts the JOIN clauses from the SQL query.
     * @function
     * @returns {Array} - An array of join information objects.
     */
    extractJoins() {
        const maskedQuery = this.getMaskedQuery();
        const joins = [];
        const regex = /\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*))?\s+ON\s+/ig;
        let match;
        
        while ((match = regex.exec(maskedQuery)) !== null) {
            const model = match[1];
            const aliasMatches = match[2] || false;
            let alias = aliasMatches && !/^(WHERE|GROUP|ORDER|LIMIT|JOIN|ON|HAVING)$/i.test(aliasMatches) ? aliasMatches : false;
            
            const joinStartIndex = match.index;
            const contextStr = maskedQuery.substring(joinStartIndex + match[0].length);
            const nextClauseMatch = contextStr.match(/\b(JOIN|WHERE|GROUP BY|ORDER BY|LIMIT)\b/i);
            const conditionLength = nextClauseMatch ? nextClauseMatch.index : contextStr.length;
            
            const joinRawStr = this.query.substring(joinStartIndex, joinStartIndex + match[0].length + conditionLength).trim().replace(/\n/g, '');
            const conditionStr = this.query.substring(joinStartIndex + match[0].length, joinStartIndex + match[0].length + conditionLength).trim();
            
            const linkedTableRegex = /([^\.]+)\.(\w+)\s*=\s*([^\.]+)\.(\w+)/;
            const linkedTableMatch = conditionStr.match(linkedTableRegex);
            const linked = linkedTableMatch ? linkedTableMatch[3] : null;
            const field = linkedTableMatch ? linkedTableMatch[4] : null;

            joins.push({
                join: joinRawStr,
                model,
                alias,
                linked,
                field,
                name: model.replaceAll('_', ' ')
            });
        }
        return joins;
    }
}
  