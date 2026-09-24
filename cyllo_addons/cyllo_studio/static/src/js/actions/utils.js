/** @odoo-module **/
import { GROUPABLE_TYPES } from "@web/search/utils/misc";
/**
 * @param {string} fieldName
 * @param {Object} field
 * @returns {boolean}
 */
export const validateField = (fieldName, field) => {
    const { sortable, store, type } = field;
    return (
        GROUPABLE_TYPES.includes(type) &&
        fieldName !== "id" &&
        (type === "many2many" ? store : sortable)
    );
};
