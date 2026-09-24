/** @odoo-module */
import {getIsActiveTab, useBusService} from "./useBusService";

export const useBusDoAction = ({callBack, event = "notification"}) => {
    /** demo usage
     * -------------
     *  channel = "bus_do_action"
     *  message = {
     *     "channel": channel,
     *     "auth": {
     *         "user": env.user.id,
     *     }
     *     "action": {
     *         'type': 'ir.actions.client',
     *         'tag': 'reload'
     *     }
     *  }
     *  env['bus.bus']._sendone(channel, "notification", message)
     *  */
    const channel = "bus_do_action";
    let isTabActive = true
    getIsActiveTab((state) => {
        isTabActive = state;
    })
    const beforeExecute = (ev) => {
        if (isTabActive) {
            callBack(ev)
        }
    }
    useBusService({channel, callBack: beforeExecute, event});
}