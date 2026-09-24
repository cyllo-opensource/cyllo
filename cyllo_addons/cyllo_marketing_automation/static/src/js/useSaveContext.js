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
        const parsedValue = JSON.parse(serializedValue);
        return parsedValue;
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
    const context = component.props.action?.context
    var key = false;
    if (context) {
        var id = context?.rec_id
        id = (id === undefined) ? context.id : id;
        key = `${session.db}_${component.props.action.tag}`
        id && saveToSessionStorage(key, {id})
    }
    const saveManually = (value, keyWord="id", force=false) => {
        if (!value && !force) return
        saveToSessionStorage(key, {[keyWord]: value})
    }
    const saveToSession = (sKey, sValue, useDB= false) => {
        sKey = useDB ? `${session.db}_${sKey}` : sKey
        saveToSessionStorage(sKey, sValue)
    }
    const removeManually = (mKey) => {
        mKey = mKey ? `${session.db}_${mKey}` : key
        removeFromSessionStorage(mKey)
    }
    const getKeyValue = (key, useDB= true) => {
        key = useDB ? `${session.db}_${key}`: key
        return getFromSessionStorage(key)
    }
    var returnValue = key ? getFromSessionStorage(key) : { id: false }
    return { ...returnValue, saveManually, removeManually, getKeyValue, saveToSession }
}