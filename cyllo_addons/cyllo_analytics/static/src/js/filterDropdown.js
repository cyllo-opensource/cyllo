/** @odoo-module **/
import {Component,useExternalListener,useRef} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class FilterDropdown extends Component {
    setup(){
        useExternalListener(window, "click", this.onWindowClick);
        this.filter_dropdown = useRef('filter_dropdown')
        this.filter_button = useRef('filter_button')
    }

    onWindowClick(){
        this.filter_button.el.classList.add('collapsed')
        this.filter_dropdown.el.classList.remove('show')
    }

    onCLickFilterWindow(ev){
        ev.stopPropagation()
    }

    get containerId(){
        const label = this.props.display_name || "filters"
        return "cy-dialogcontainer_" + label.replace(/[^A-Za-z0-9_-]/g, "_")
    }
}
FilterDropdown.defaultProps = {
    name: _t("Filters"),
    display_name: _t("Filters"),
    footer: true,
    class: "cy-active-btn cy-market-activity-btn",
    onClick: () => {},
    mainClass: ""
};
FilterDropdown.template = "cyllo_analytics.filterDropdown"
FilterDropdown.props = {
    name: { type: String, optional: true },
    display_name: { type: String, optional: true },
    footer: { type: Boolean, optional: true },
    class: { type: String, optional: true },
    onClick: { type: Function, optional: true },
    slots: { type: Object, optional: true },
    mainClass: { type: String, optional: true },
}