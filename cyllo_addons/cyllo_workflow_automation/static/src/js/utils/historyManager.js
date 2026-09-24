/** @odoo-module */

import { cloneState } from "./stateClone";

export class HistoryManager {
    constructor(limit = 100) {
        this.undoStack = [];
        this.redoStack = [];
        this.limit = limit;
    }

    /**
     * Initial set of the state. Should be called when the editor is first loaded.
     * @param {Object|string} state
     */
    init(state) {
        this.undoStack = [cloneState(state)];
        this.redoStack = [];
    }

    /**
     * Save a new state snapshot.
     * @param {Object|string} state
     */
    save(state) {
        const newState = cloneState(state);

        this.undoStack.push(newState);
        this.redoStack = []; // Clear redo stack on new action

        if (this.undoStack.length > this.limit) {
            this.undoStack.shift(); // Remove oldest state
        }
    }

    /**
     * Revert to the previous state.
     * @returns {Object|string|null} The previous state.
     */
    undo() {
        if (!this.canUndo()) return null;

        const currentState = this.undoStack.pop();
        this.redoStack.push(currentState);

        return cloneState(this.undoStack[this.undoStack.length - 1]);
    }

    /**
     * Restore the next state.
     * @returns {Object|string|null} The next state.
     */
    redo() {
        if (!this.canRedo()) return null;

        const nextState = this.redoStack.pop();
        this.undoStack.push(nextState);

        return cloneState(nextState);
    }

    canUndo() {
        return this.undoStack.length > 1;
    }

    canRedo() {
        return this.redoStack.length > 0;
    }
}
