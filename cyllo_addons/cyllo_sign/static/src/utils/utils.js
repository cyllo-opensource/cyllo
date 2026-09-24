/** @odoo-module **/
function cast(value) {
    return !value || isNaN(value) ? value : Number(value);
}
function parseString(str) {
    const parts = str.split("&");
    const result = {};
    for (const part of parts) {
        const [key, value] = part.split("=");
        const decoded = decodeURIComponent(value || "");
        result[key] = cast(decoded);
    }
    return result;
}
export function parseHash() {
    const location = window.location;
    const { pathname, search, hash } = location;
    return hash && hash !== "#" ? parseString(hash.slice(1)) : {};
}
export function parseSearchQuery(search) {
    return search ? parseString(search.slice(1)) : {};
}
