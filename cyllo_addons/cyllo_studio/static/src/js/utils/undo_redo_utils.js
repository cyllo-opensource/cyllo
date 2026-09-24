/** @odoo-module **/
/**
 * Handles storing a new action in the Undo/Redo stack.
 *
 * @param {string} response - The string representing the action to be stored.
 *                           It will be cleaned of extra spaces before storing.
 *
 * This function updates the sessionStorage:
 * - Adds the cleaned action to the "UndoRedo" stack.
 * - Resets the "ReDO" stack to an empty array.
 */
export function handleUndoRedo(response){
    if(response){
        let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
        let cleanedStr = response.replace(/\s+/g, ' ').trim();
        storedArray.push(cleanedStr);
        sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
        sessionStorage.setItem('ReDO', JSON.stringify([]));
    }
}