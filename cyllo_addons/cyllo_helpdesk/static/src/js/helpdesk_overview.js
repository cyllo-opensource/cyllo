    /** @odoo-module */
import { registry } from "@web/core/registry"
import { onWillStart, onMounted, } from "@odoo/owl";
const actionRegistry = registry.category("actions");
import { useService } from "@web/core/utils/hooks";
const { Component, useState, useRef, useEffect } = owl;

export class ToggleTag extends Component {
    setup(){
        this.root = useRef('root')
        this.orm = useService("orm");
        this.toggle = useState({ tag : false , value : 0 })
        this.toggle.tag = this.props.tag
        this.float = this.props.float || false
        this.toggle.value = this.props.value || 0
        useEffect((el)=>{
            if (el) this.root.el.focus();
        }, () => [this.toggle.tag]);
    }
    async onBlurEvent(ev){
        const value = ev.target.value || 0
        const parsedValue = this.float ? parseFloat(value) : parseInt(value, 10)
        this.toggle.value = Number.isNaN(parsedValue) ? 0 : parsedValue
        if (this.props.fieldName) {
            const result = await this.orm.call(
                "helpdesk.overview",
                "set_daily_target",
                [this.props.fieldName, this.toggle.value]
            );
            this.toggle.value = result[this.props.fieldName];
        }
        this.changeElement()
    }
    get tag(){
        return this.toggle.tag
    }
    changeElement(){
        this.toggle.tag = !this.toggle.tag;
    }
}
ToggleTag.template = 'cyllo_helpdesk.ToggleTag'
ToggleTag.props = {
    tag : { type : Boolean, optional: true },
    value : { type : Number, optional: true },
    float : { type : Boolean, optional: true },
    fieldName : { type : String, optional: true },
}


export class HelpdeskOverview extends owl.Component {
    setup() {
      super.setup(...arguments);
        this.orm = useService("orm");
        this.action = useService("action");
        this.ticketData = useState({});
        onWillStart(async () => {
            Object.assign(
                this.ticketData,
                await this.orm.call("helpdesk.overview", "get_overview_data")
            );
        });
      }
      clickToggle(ev){
        console.log(this,'click')
      }
    async getSearchDetails(ev) {
        const action = ev.currentTarget;
        const actionRef = action.getAttribute('name')
        const title = action.dataset.actionTitle || action.getAttribute('title')
        const searchViewRef = action.getAttribute('search_view_ref')

        const buttonContext = action.getAttribute('context')
        return await this.action.doActionButton({
            resModel: 'helpdesk.ticket',
            name: 'get_acton',
            args: JSON.stringify([actionRef, title, searchViewRef]),
            context: '',
            buttonContext,
            type: 'object'
        })


//        this.env.services['action'].doAction({
//            name: 'My Tickets',
//            type: 'ir.actions.act_window',
//            res_model: 'helpdesk.ticket',
//            views: [[false, 'tree']],
//            target: 'current',
////            view_id: this.env.ref('cyllo_helpdesk.helpdesk_my_ticket_action').id
//             context:{
//                'tree_view_ref':'cyllo_helpdesk.helpdesk_my_ticket_action'
//            }
//        })
    }

//    getSearchDetails(ev) {
//          let filter_name = ev.currentTarget.getAttribute("filter_name");
//          let filters = filter_name.split(',');
//          let searchItems = this.env.searchModel.getSearchItems((item) => filters.includes(item.name));
//
//          this.env.searchModel.query = [];
//          for (const item of searchItems){
//                this.env.searchModel.toggleSearchItem(item.id);
//            }
//    }
}

HelpdeskOverview.template = 'cyllo_helpdesk.HelpdeskOverview'
HelpdeskOverview.components = {
ToggleTag
}

//actionRegistry.add('helpdesk_ticket_overview', HelpdeskOverview);
