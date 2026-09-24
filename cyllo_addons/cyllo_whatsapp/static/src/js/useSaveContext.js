/** @odoo-module **/
const { useComponent } = owl
import { session } from "@web/session";

function saveToSessionStorage(key, value) {
    try {
        const serializedValue = JSON.stringify(value);
        sessionStorage.setItem(key, serializedValue);
    } catch (error) {
        console.error('Error saving to session storage:', error);
    }
}

function getFromSessionStorage(key) {
    try {
        const serializedValue = sessionStorage.getItem(key);
        return JSON.parse(serializedValue);
    } catch (error) {
        console.error('Error retrieving from session storage:', error);
        return null;
    }
}

function removeFromSessionStorage(key) {
    try {
        if (sessionStorage.getItem(key)) {
            sessionStorage.removeItem(key);
        }
    } catch (error) {
        console.error('Error removing item from sessionStorage:', error);
    }
}

export function useSaveContext() {
    const component = useComponent();
    const context = component.props.action.context
    var id = context?.rec_id
    id = (id === undefined) ? context.id : id;
    const key = `${session.db}_${component.props.action.tag}`
    id && saveToSessionStorage(key, {id})
    const saveManually = (newId) => saveToSessionStorage(key, {id: newId})
    const removeManually = () => removeFromSessionStorage(key)
    return {...getFromSessionStorage(key), saveManually, removeManually}
}