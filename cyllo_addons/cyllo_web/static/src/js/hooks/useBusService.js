/** @odoo-module */
import {useComponent} from "@odoo/owl";

const defaultEvent = "notification";

export const getIsActiveTab = (setActive) => {
    const updateTabActiveState = () => {
        const isTabActive = !document.hidden && document.hasFocus();
        setActive(isTabActive);
    };
    document.addEventListener('visibilitychange', updateTabActiveState);
    window.addEventListener('focus', updateTabActiveState);
    window.addEventListener('blur', updateTabActiveState);
};


export const useBusService = ({channel, callBack, event = defaultEvent}) => {
    if (typeof channel !== "string" || !channel.trim()) {
        throw new Error("Invalid channel: Channel must be a non-empty string.");
    }
    if (typeof callBack !== "function") {
        throw new Error("Invalid callBack: callBack must be a function.");
    }
    if (typeof event !== "string" || !event.trim()) {
        throw new Error("Invalid event: Event must be a non-empty string.");
    }
    const component = useComponent();
    const busService = component.env.services.bus_service;
    if (!busService) {
        throw new Error("bus_service is not available in the environment.");
    }

    busService.addChannel(channel);
    busService.addEventListener(event, callBack);
};
