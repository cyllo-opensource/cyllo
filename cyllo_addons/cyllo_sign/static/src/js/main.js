/** @odoo-module **/
import { parseHash } from "@web/core/browser/router_service";
import { App, EventBus } from "@odoo/owl";
import { templates } from "@web/core/assets";
import SignWrapper from "./sign_wrapper";
import { makeEnv, startServices } from "@web/env";

(function boot() {
    owl.whenReady(async () => {
    const bus = new EventBus();
    const env = makeEnv();
    await startServices(env);
    const translations = {};
    const hash = parseHash();
    const translateFn = (str) => {
        return translations[str] || str;
    }
    const app = new App(SignWrapper, {
        name: "SignWrapper",
        env,
        templates,
        translateFn,
        dev: true,
    });
    const root = await app.mount(document.body);
})
})();
