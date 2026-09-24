/** @odoo-module */
const { useComponent } = owl

export function useVariable(def) {
    const component = useComponent();
    if (def === "def") return filterVariable.bind(component);
    else if(def === "noDef") return filterVariableNoDef.bind(component);
}

function filterVariableNoDef (variables, variable, operator) {
    return variables.filter(v => {
        if (variable.variable_type === "record") {
            if (["=", "!="].includes(operator) && variable.variable_type === v.variable_type && variable.modelId === v.modelId) {
                return true;
            } else if(["in", "not in"].includes(operator) && ["record", "recordset"].includes(v.variable_type) && variable.modelId === v.modelId) {
                return true;
            }
            return false;
        } else if (variable.variable_type === "recordset") {
            return ["=", "!=", "in", "not in"].includes(operator) && variable.modelId === v.modelId && ["record", "recordset"].includes(v.variable_type);
        } else {
            return variable.variable_type === v.variable_type;
        }
    }) || []
}

export async function filterVariable(variables, def, operator) {
    const isValidMany2One = (variable, model) =>
        ["record", "recordset", "string"].includes(variable.variable_type) &&
        ((!model && ["not ilike", "ilike"].includes(operator) && variable.variable_type === "string") ||
        (model === def.relation &&
            (["=", "!="].includes(operator) && variable.variable_type === "record") || model === def.relation &&
            (["in", "not in"].includes(operator) && ["recordset", "record"].includes(variable.variable_type))));
    const isValidPrimitive = (variable) =>
        (["html", "char", "selection", "text"].includes(def.type) && variable.variable_type === "string") ||
        (def.type === "boolean" && variable.variable_type === "boolean") ||
        (["integer", "float", "monetary"].includes(def.type) && variable.variable_type === "number") ||
        (def.type === "date" && variable.variable_type === "date") || (def.type === "datetime" && variable.variable_type === "datetime");
    const isValidMany2Many = (variable, model) =>
        ["recordset", "record"].includes(variable.variable_type) &&
        model === def.relation &&
        ["in", "not in", "=", "!="].includes(operator);
    const isValidOne2Many = (variable, model) =>
        ["recordset", "record"].includes(variable.variable_type) &&
        model === def.relation &&
        ["in", "not in", "=", "!="].includes(operator);
    const filteredVariables = await Promise.all(variables.map(async (variable) => {
        if (variable.modelId) {
            const [{ model }] = await this.orm.read("ir.model", [variable.modelId], ['model']);
            if (def.type === "many2one") {
                return isValidMany2One(variable, model) ? variable : null;
            } else if (def.type === "many2many") {
                return isValidMany2Many(variable, model) ? variable : null;
            } else if (def.type === "one2many") {
                return isValidOne2Many(variable, model) ? variable : null;
            }
        } else {
            if (def.type === "many2one") {
                return isValidMany2One(variable) ? variable : null;
            } else if (["many2many", "one2many"].includes(def.type)) {
                // TODO:####
                return null;
            }
        }
        return isValidPrimitive(variable) ? variable : null;
    }));
    return filteredVariables.filter(Boolean);
}

export const PYTHON_KEYWORDS = [
    'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
    'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
    'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
    'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
    'try', 'while', 'with', 'yield'
]

export const OPERATORS = {
    record: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        ["in", "in"],
        ["not in", "not in"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    recordset: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        ["in", "in"],
        ["not in", "not in"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    char: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        ["ilike", "contains (case insensitive)"],
        ["not ilike", "doesn't contain (case insensitive)"],
        ["like", "contains (case sensitive)"],
        ["not like", "doesn't contain (case sensitive)"],
        ["in", "in"],
        ["not in", "not in"],
        ["=like", "matches pattern"],
        ["=ilike", "matches pattern (case insensitive)"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    text: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        ["ilike", "contains (case insensitive)"],
        ["not ilike", "doesn't contain (case insensitive)"],
        ["like", "contains (case sensitive)"],
        ["not like", "doesn't contain (case sensitive)"],
        ["in", "in"],
        ["not in", "not in"],
        ["=like", "matches pattern"],
        ["=ilike", "matches pattern (case insensitive)"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    html: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        ["ilike", "contains (case insensitive)"],
        ["not ilike", "doesn't contain (case insensitive)"],
        ["like", "contains (case sensitive)"],
        ["not like", "doesn't contain (case sensitive)"],
        ["in", "in"],
        ["not in", "not in"],
        ["=like", "matches pattern"],
        ["=ilike", "matches pattern (case insensitive)"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    integer: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        [">", "greater than"],
        [">=", "greater than or equal to"],
        ["<", "less than"],
        ["<=", "less than or equal to"],
        ["in", "in"],
        ["not in", "not in"],
        ["between", "between"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    float: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        [">", "greater than"],
        [">=", "greater than or equal to"],
        ["<", "less than"],
        ["<=", "less than or equal to"],
        ["in", "in"],
        ["not in", "not in"],
        ["between", "between"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    monetary: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        [">", "greater than"],
        [">=", "greater than or equal to"],
        ["<", "less than"],
        ["<=", "less than or equal to"],
        ["in", "in"],
        ["not in", "not in"],
        ["between", "between"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    boolean: [
        ["=", "equal to"],
        ["!=", "not equal to"]
    ],
    date: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        [">", "after"],
        [">=", "after or on"],
        ["<", "before"],
        ["<=", "before or on"],
        ["between", "between"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    datetime: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        [">", "after"],
        [">=", "after or on"],
        ["<", "before"],
        ["<=", "before or on"],
        ["between", "between"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    many2one: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        ["in", "in"],
        ["not in", "not in"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    one2many: [
        ["in", "in"],
        ["not in", "not in"],
        ["=", "equal to"],
        ["!=", "not equal to"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    many2many: [
        ["in", "in"],
        ["not in", "not in"],
        ["=", "equal to"],
        ["!=", "not equal to"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    selection: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        ["in", "in"],
        ["not in", "not in"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
};

export const VARIABLE_OPERATORS = {
    record: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        ["in", "in"],
        ["not in", "not in"],
        ["set", "is set"],
        ["not_set", "is not set"],
    ],
    recordset: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        ["in", "in"],
        ["not in", "not in"],
        ["set", "is set"],
        ["not_set", "is not set"],
    ],
    number: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        [">", "greater than"],
        [">=", "greater than or equal to"],
        ["<", "less than"],
        ["<=", "less than or equal to"],
        ["between", "between"],
        ["set", "is set"],
        ["not_set", "is not set"],
    ],
    string: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        ["ilike", "contains (case insensitive)"],
        ["not ilike", "doesn't contain (case insensitive)"],
        ["like", "contains (case sensitive)"],
        ["not like", "doesn't contain (case sensitive)"],
        ["in", "in"],
        ["not in", "not in"],
        ["=like", "matches pattern"],
        ["=ilike", "matches pattern (case insensitive)"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    date: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        [">", "after"],
        [">=", "after or on"],
        ["<", "before"],
        ["<=", "before or on"],
        ["between", "between"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    datetime: [
        ["=", "equal to"],
        ["!=", "not equal to"],
        [">", "after"],
        [">=", "after or on"],
        ["<", "before"],
        ["<=", "before or on"],
        ["between", "between"],
        ["set", "is set"],
        ["not_set", "is not set"]
    ],
    boolean: [
        ["=", "equal to"],
        ["!=", "not equal to"]
    ],
}

export function getVariableDefaultValue (condition, variables) {
    if (!condition.field) return false;
    const { operator, field: {selectedVariable}} = condition;
    const variable = variables.find(item => item.id === selectedVariable);
    if (!variable) return false;
    const { variable_type } = variable;
    if (["=","!="].includes(operator) && variable_type === "record"){
        return false
    } else if (["in","not in"].includes(operator) && variable_type === "record" || variable_type === "recordset") {
        return [];
    } else {
        return  false
    }
}

export function validateCondition(condition) {
    // Check if condition is an object
    if (typeof condition !== 'object' || condition === null) {
        return false;
    }
    // Check for required 'field' and 'value' properties
    if (!condition.field || !condition.value) {
        return false;
    }
    // Check 'field' criteria
    if (typeof condition.field !== 'object' || (!'record' in condition.field && !'selectedVariable' in condition.field)) {
        return false;
    }
    // Check 'value' criteria
    if (condition.operator === 'set' || condition.operator === 'not_set') return true;
    if (typeof condition.value !== 'object') {
        return false;
    }
    if (condition.value.value === "") return false;
    if (condition.value.value === undefined || condition.value.value === null) {
            return false;
        }
    if (condition.value.fieldType === "variable") {
        if(!condition.value.value.selectedVariable) return false;
    } else if (condition.value.fieldType === "record") {
        if(!condition.value.value.record) return false;
    }
    return true;
}
