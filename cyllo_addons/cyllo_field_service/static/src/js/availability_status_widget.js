/** @odoo-module **/
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
const { Component, useRef, useState, onMounted} = owl;

export class AvailabilityStatusWidget extends Component {
    setup() {
        super.setup();
        this.root = useRef('root') // Reference to the root element
        this.orm = useService("orm");
        onMounted(()=>this.getAvailableWorkers())
    }
    async getAvailableWorkers(){
        let empId = await this.root.el.dataset.empId;
        let empName = await this.root.el.dataset.empName;
        let nonAvailable = this.root.el.querySelector('.worker_availability');
        let availabilityStatus =await this.orm.searchRead(
            "hr.employee",
            [
                ["id", "=", parseInt(empId)],

            ],
            ["availability_status"]
        );
        if(availabilityStatus[0].availability_status === 'not_available'){
            nonAvailable.classList.add('non_available_worker')
            this.root.el.title = `${empName} is currently busy in another service`;
        }
        else if(availabilityStatus[0].availability_status === 'available'){
            nonAvailable.classList.add('is_available_worker')
            this.root.el.title = `${empName} is available for service`
        }
        else{
            nonAvailable.classList.add('reserved_worker')
            this.root.el.title = `${empName} is reserved in other services`
        }
    }
}
AvailabilityStatusWidget.template = 'AvailabilityStatusWidget';
AvailabilityStatusWidget.props = {
    ...standardFieldProps,
};
export const availabilityStatus = {
    component: AvailabilityStatusWidget,
    supportedTypes: ["selection"],
};
registry.category("fields").add("availability_status_widget", availabilityStatus);
