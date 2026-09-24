/** @odoo-module */

function deepClone(value, cache) {
    if (value === null || typeof value !== 'object') {
        return value;
    }

    if (cache.has(value)) {
        return cache.get(value);
    }

    let cloned;

    if (Array.isArray(value)) {
        cloned = [];
        cache.set(value, cloned);
        for (let i = 0; i < value.length; i++) {
            cloned[i] = deepClone(value[i], cache);
        }
        return cloned;
    }

    if (value instanceof Date) {
        return new Date(value);
    }

    if (value instanceof RegExp) {
        return new RegExp(value);
    }

    if (value instanceof Map) {
        cloned = new Map();
        cache.set(value, cloned);
        for (const [key, entry] of value.entries()) {
            cloned.set(key, deepClone(entry, cache));
        }
        return cloned;
    }

    if (value instanceof Set) {
        cloned = new Set();
        cache.set(value, cloned);
        for (const item of value.values()) {
            cloned.add(deepClone(item, cache));
        }
        return cloned;
    }

    cloned = {};
    cache.set(value, cloned);
    for (const key of Object.keys(value)) {
        cloned[key] = deepClone(value[key], cache);
    }
    return cloned;
}

function cloneWithoutStructuredClone(value) {
    if (value === null || typeof value !== 'object') {
        return value;
    }
    return deepClone(value, new WeakMap());
}

export function cloneState(value) {
    if (typeof structuredClone === 'function') {
        try {
            return structuredClone(value);
        } catch (error) {
            if (error?.name !== 'DataCloneError' && !error?.message?.includes('could not be cloned')) {
                throw error;
            }
            // If DataCloneError occurs, fall back to the custom deep clone.
        }
    }
    return cloneWithoutStructuredClone(value);
}
