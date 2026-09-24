/** @odoo-module */
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
const { Component } = owl;
import { session } from "@web/session";

export class ToggleTag extends Component {
    /* Extending Component to create ToggleTag class */
    setup(){
        this.orm = useService("orm");
    }
}
export class SupportServiceOverview extends Component {
    /* Extending owl component to create a class for support service overview */
    setup() {
      super.setup(...arguments);
        this.orm = useService("orm");
        this.action = useService("action");
        onWillStart(async () => {
            this.ticketData = await this.orm.call(
                "support.service.ticket",
                "get_overview"
                );
        });
      }
    /* Function to get ticket details */
    getTicketDetails(value, failed) {
        let domain = [['user_id','=',session.uid],['stage_id.is_closed', '=', false],
        ['stage_id.is_canceled', '=', false]]
        failed ? domain.push(['stage_id.is_closed', '=', false,],[ 'deadline', '<', new Date()]): ''
        let priorityId = value ? value === 'urgent_tickets' ?  3 : 2 : null
        priorityId ? domain.push(['priority','=',priorityId]) : '';
        this.doAction(domain)
    }
    /* Function to get today closed tickets */
    getTodayClosedTicket() {
        let domain = [['user_id','=',session.uid], ['is_closed_today','=',true]]
        this.doAction(domain)
    }
    /* Function to get last week closed tickets */
    getLastWeekClosedTicket() {
        const lastSevenDays = new Date();
        lastSevenDays.setDate(lastSevenDays.getDate() - 6)
        let domain = [['user_id','=',session.uid], ['closed_date','>',lastSevenDays]]
        this.doAction(domain)
    }
    /* Function to get today's success rate */
    getTodaySuccessRate(){
        let domain = [['user_id','=',session.uid], ['is_closed_today','=',true], ['is_failed','=',false]]
        this.doAction(domain)
    }
    /* Function to get last week success rate */
    getLastWeekSuccessRate(){
        const lastSevenDays = new Date();
        lastSevenDays.setDate(lastSevenDays.getDate() - 6)
        let domain = [['user_id','=',session.uid], ['closed_date','>',lastSevenDays], ['is_failed','=',false]]
        this.doAction(domain)
    }
    /* doAction for all the domains defined above */
    async doAction(domain){
        await this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Tickets',
            res_model: 'support.service.ticket',
            domain:domain,
            views: [[false, 'tree'], [false, 'form']],
            view_mode: 'tree',
            target: 'self',
        })
    }
}
SupportServiceOverview.template = 'cyllo_support_service.SupportServiceOverview'
