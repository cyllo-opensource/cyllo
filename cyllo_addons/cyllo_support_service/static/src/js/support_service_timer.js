/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { cyTimerWidget } from "@cyllo_web/js/widgets/timerWidget/cy_timer_widget";

patch(cyTimerWidget.prototype, {
    /**
     * Enhance the setup method to include additional services and event listeners.
     */
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.busService = this.env.services.bus_service
        this.busService.addChannel("TIMER-STOP")
        this.busService.addEventListener("notification", this.check_reset.bind(this))
    },
    /**
     * Override the start method to resume a ticket when the timer starts.
     */
    async start(){
        var resId = this.props.record.model.config.resId
        if(this.props.record.model.config.resModel == 'support.service.ticket'){
            if(this.props.record.data.stage_id[1] != 'In Progress'){
                await this.orm.call("support.service.ticket", "action_resume_ticket", [,resId]);
                this.action.doAction('soft_reload')
            }
        }
        let start = super.start()
    },
    /**
     * Override the stop method to pause a ticket when the timer stops.
     */
    async stop(){
        var resId = this.props.record.model.config.resId
        if(this.props.record.model.config.resModel == 'support.service.ticket'){
            if(this.props.record.data.stage_id[1] != 'On Hold'){
                await this.orm.call("support.service.ticket", "action_pause_ticket", [,resId]);
            }
        }
        let stop = super.stop()
    },
    /**
     * Check if the timer needs to be reset based on a received notification.
     * @param {Object} data - Notification data containing timer_toggle information.
     */
    check_reset(data){
        if(data.detail[0].type == 'resume_timer'){
            this.start()
        }else if(data.detail[0].payload.timer_toggle && data.detail[0].type == 'stop_timer'){
            if (owl.status(this) !== 'destroyed'){
                this.reset()
            }
        }
    }
});