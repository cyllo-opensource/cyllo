/** @odoo-module **/
/**
 * Studio shared utilities.
 *
 * Lives in its own module (no component imports) so leaf modules like the
 * navbar can use these helpers without importing studio_wrapper, which would
 * create a dependency cycle (studio_wrapper -> navbar -> studio_wrapper).
 */

/**
 * Clears X2Many-related session and local storage entries.
 */
export function RemoveSessions() {
    localStorage.removeItem('X2ManysStudioPage');
    sessionStorage.removeItem('X2manyList');
    sessionStorage.removeItem('CyX2Many');
    sessionStorage.removeItem('CyX2ManyPath');
    sessionStorage.removeItem('x2ManyDetails');
    sessionStorage.removeItem('CyX2ManyTriggered');
    sessionStorage.removeItem('PrevForm');
    sessionStorage.removeItem("RelationalModel");
    sessionStorage.removeItem('CyStudioRelationModel');
}

/**
 * Validates whether a field is currently being edited.
 * Displays a notification if editing is in progress.
 *
 * @param {Object} state - The state object containing field flags.
 * @param {Object} notification - Notification service to display warnings.
 * @param {String} field - The field key to check in the state.
 * @param {String} type - Optional. Type of editing (default: "Editing").
 * @returns {Boolean} True if field is not being edited, false otherwise.
 */
export function validateEdit(state, notification, field, type = "Editing") {
    if (!state?.[field]) return true;

    notification.add({
        title: "Validation Error",
        message: `${type} is in progress.`,
        description: "Please save or cancel the current process.",
        type: "notification_panel",
        notificationType: "warning",
    });
    return false;
}
