/** @odoo-module **/

/**
 * Display a notification in the Odoo web client.
 *
 * @param {Object} env - The Owl environment object containing services like `action`.
 * @param {Object} options - Optional settings for the notification.
 * @param {string} options.message - The message to display (default: "Select a field").
 * @param {string} options.type - Type of notification: "warning", "success", "danger", etc. (default: "warning").
 * @param {boolean} options.sticky - Whether the notification should stay until manually dismissed (default: false).
 */
export function DisplayNotification(env, options = {}) {
    const defaultOptions = {
        message: 'Select a field',
        type: 'warning',
        sticky: false
    };

    // Merge default options with provided options
    const finalOptions = { ...defaultOptions, ...options };

    env.action.doAction({
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': finalOptions
    });
}