/* @odoo-module */
import { Chatter } from "@mail/core/web/chatter";
import { patch } from "@web/core/utils/patch";

patch(Chatter.prototype, {
     setup() {
        super.setup();
        this.busService = this.env.services.bus_service
        this.channel = "REFRESH"
        this.busService.addChannel(this.channel)
        this.busService.subscribe("notification", (data) => {
            if(data){
                   this.MessageUpdate(data)
            }
        });
    },
    async MessageUpdate(data){
        if (data.message){
        if (data.message[0]){
            var res_id=data.message[0].res_id
            var model=data.message[0].model
            var thread=this.threadService.getThread(model,res_id)
            this.threadService.fetchNewMessages(thread);
        }
        }
    }
});