/** @odoo-module */
import {NavBar} from "@web/webclient/navbar/navbar";
import {patch} from "@web/core/utils/patch";
import {useBusDoAction} from "../hooks/useBusDoAction";
import {session} from "@web/session";
import {useEffect, useState} from "@odoo/owl";
import {Systray} from "../systray/cyllo_systray/systray"

NavBar.components = {...NavBar.components, Systray};

patch(NavBar.prototype, {
    setup() {
        super.setup();
        useBusDoAction({callBack: this.onMessage.bind(this)})
        this.styleState = useState({
            display: "flex",
        })
        this.env.bus.addEventListener("TOGGLE_NAVBAR:HIDE", ({detail: {show}}) => {
            this.styleState.display = show ? "flex" : "none";
        })
        this.cylloSystray = useState({
            show: true,
        })
        useEffect(() => {
            // FIXME: Fixed systray data mismatch issue caused by improper Website context detection.
            //
            // Issue:
            // When switching from Website to Backend via the Odoo UI (e.g., app switcher),
            // the old Website systray remained mounted in the DOM and did not properly switch
            // to the backend systray. As a result, the systray design and data were mismatched
            // in the backend until a manual page refresh or URL navigation was done.
            //
            // Root Cause:
            // The old logic incorrectly detected the environment using:
            //     const xmlId = this.action.currentController?.action?.xml_id || ""
            //     const isWebsite = xmlId === "website.website_preview"
            //
            // Problem in this code:
            // 1. `.includes()` was misused — it only accepts a single string, not multiple.
            // 2. This failed to correctly identify Website context, causing systray inconsistency.
            //
            // Fix Applied:
            // Replaced the detection with:
            //     const xmlId = this.currentApp?.xmlid || this.action.currentController?.action?.xml_id || ""
            //     const isWebsite = ["website.website_preview", "website.menu_website_configuration"].includes(xmlId)
            //
            // This ensures the systray re-renders correctly based on the active app,
            // even when switching via UI, preventing the old Website systray from persisting in backend.
            //
            // NOTE for future developers:
            // If systray design or data mismatch occurs again when switching between Website and Backend via the UI,
            // review this detection logic as a first step. This prevents legacy systray leftovers from Website context.
            this.cylloSystray.show =  this.websiteService?.currentWebsite === undefined
        }, () => [this.currentApp?.appID, this.action.currentController?.action, this.websiteService?.currentWebsite?.metadata?.path])
    },
    onMessage({detail: notifications}) {
        // Use f ilter to get all actions with channel "bus_do_action"
        const actions = notifications.filter(item => item.payload.channel === "bus_do_action");
        if (actions.length === 0) return; // If no matching actions, exit early
        let index = 0;
        // Use setInterval to loop through each action every 2 seconds
        const intervalId = setInterval(() => {
            const nextAction = actions[index];
            // Check if user matches the action payload auth user
            if (session.uid === nextAction.payload.auth?.user) {
                const {payload} = nextAction;
                // Determine actionId and execute the corresponding action
                if (payload.options) {
                    this.actionService.doAction(payload.action, payload.options);
                } else {
                    this.actionService.doAction(payload.action);
                }
            }
            index++; // Move to the next action
            // Stop the interval if all actions have been processed
            if (index >= actions.length) {
                clearInterval(intervalId);
            }
        }, 1000); // Execute every 1 seconds
    }
})

