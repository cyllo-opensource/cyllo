/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SaveConfetti, SaveFireworks,BuildMessage } from "./effect/effects";
const effectRegistry = registry.category("effects");

function saveConfettiEffect(env, params = {}) {
    const message = params.message || "Record Saved Successfully!";
    const isLocked = params.locked || false;
    const icon = message === "Locked!" ? "ri-lock-2-fill" : "ri-lock-unlock-fill";
    if (env.services.user.showEffect) {
        return {
            Component: SaveConfetti,
            props: { message, isLocked, icon},
        };
    }
    env.services.notification.add(message);
}

function saveFireworksEffect(env, params = {}) {
    const message = params.message || "Record Saved Successfully!";
    if (env.services.user.showEffect) {
        return {
            Component: SaveFireworks,
            props: { message },
        };
    }
    env.services.notification.add(message);
}
function saveBuildingLoading(env, params = {}) {
    const message = params.message || "Building your Flow....!";
    const image = params.image || "";
    if (env.services.user.showEffect) {
        return {
            Component: BuildMessage,
            props: { message },
            image: image,
        };
    }
    env.services.notification.add(message);
}

effectRegistry.add("save_confetti", saveConfettiEffect);
effectRegistry.add("save_fireworks", saveFireworksEffect);
effectRegistry.add("save_Loading", saveBuildingLoading);
