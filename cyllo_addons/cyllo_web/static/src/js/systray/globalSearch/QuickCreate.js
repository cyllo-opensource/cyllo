/** @odoo-module **/
import {patch} from "@web/core/utils/patch";
import {NavBar} from "@web/webclient/navbar/navbar";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {useService} from "@web/core/utils/hooks";
import {useState, useRef, EventBus, useSubEnv} from "@odoo/owl";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";
import {Component, onWillStart, useExternalListener} from "@odoo/owl";
import {registry} from "@web/core/registry";

patch(EventBus.prototype, {
    setup() {
        super.setup(...arguments)
        this.eventBusdata = {}
    },
    setData(data) {
        this.eventBusdata = {...this.eventBusdata, ...data}
    },
    removeData(key) {
        delete this.eventBusdata[key]
    }
})

export class QuickCreateDropdown extends Dropdown {
    setup() {
        super.setup();
        this.action = useService("action");
        this.accounting = this.props.data.some(item => item.categories === "accounting");
        this.sale = this.props.data.some(item => item.categories === "sale");
        this.purchase = this.props.data.some(item => item.categories === "purchase");
        this.general = this.props.data.some(item => item.categories === "general");
    }

    onClickModel() {
        this.props.getModels()
        this.action.doAction(
            {
                res_model: 'ir.model',
                name: "Models",
                target: "current",
                type: "ir.actions.act_window",
                view_mode: 'tree,form',
                views: [[false, 'list'], [false, 'form']],
            },
        );
    }

    async openModelWizard(model_id) {
        /**
         * Sets the 'open' and 'groupIsOpen' properties to false and performs an action to open a new model window.
         *
         * @param {Event} ev - The event object.
         */
        this.env.bus.setData({dialogClass: 'o_custom_slide_wizard'})
        await this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: model_id,
            views: [
                [false, 'form']
            ],
            target: 'new',
            custom_wizard_class: "o_custom_slide_wizard"
        }, {
            onClose: () => {
                this.env.bus.removeData('dialogClass')
            }
        });
    }
}

QuickCreateDropdown.props = {
    ...Dropdown.props,
    data: {
        type: Array,
        optional: true
    },
    getModels: {type: Function, optional: true},
};

export class QuickCreateDropdownItem extends DropdownItem {


    getImageUrl(attachment) {
        if (attachment.uploading && attachment.tmpUrl) {
            return attachment.tmpUrl;
        }
        return url(attachment.urlRoute, {
            ...attachment.urlQueryParams,
            width: this.imagesWidth,
            height: this.props.imagesHeight,
        });
    }


}

QuickCreateDropdown.template = "QuickCreateDropdown";

export class QuickCreate extends Component {
    setup() {
        super.setup();
        this.rootRef = useRef("root");
        this.orm = useService('orm');
        this.state = useState({
            menu_list: [],
            result: [],
            open: false,
        });
        useExternalListener(window, "click", this.onOutsideClick);
        onWillStart(async () => {
            /* Get all active languages, code and flag images */
            this.state.result = await this.orm.call("ir.model", "get_model", []);
        })
    }

    async getModels(ev) {
        /**
         * Fetches the models asynchronously and updates the result in the component state.
         *
         * @param {Event} ev - The event object (optional).
         * @returns {Promise<void>} - A Promise that resolves when the models are fetched and the result is updated.
         */
        this.state.open = !this.state.open
    }

    openModelWizard(ev) {
        /**
         * Sets the 'open' and 'groupIsOpen' properties to false and performs an action to open a new model window.
         *
         * @param {Event} ev - The event object.openModelWizard
         */

        action.doAction({
            type: 'ir.actions.act_window',
            res_model: ev.target.attributes.model.value,
            views: [
                [false, 'form']
            ],
            target: 'new',
        });
    }

    getSwitchState() {
        /**
         * Sets the 'open' property to false in the component state.
         */
        this.state.open = false;
    }

    onOutsideClick(ev) {
        if (!this.rootRef.el || this.rootRef.el.contains(ev.target)) {
            return;
        }
        this.state.open = false;
    }

    getImageUrl(attachment) {
        if (attachment.uploading && attachment.tmpUrl) {
            return attachment.tmpUrl;
        }
        return url(attachment.urlRoute, {
            ...attachment.urlQueryParams,
            width: this.imagesWidth,
            height: this.props.imagesHeight,
        });
    }


}

QuickCreate.template = "QuickCreate";
QuickCreate.components = {
    QuickCreateDropdown,
    QuickCreateDropdownItem
};

NavBar.components = {
    /**
     * Object that defines the components of the NavBar.
     */
    ...NavBar.components,
    QuickCreate
};

export const QuickCreateItem = {
    Component: QuickCreate,
};

registry.category("navbaritems").add("QuickCreate", QuickCreateItem, {
    sequence: 2
});