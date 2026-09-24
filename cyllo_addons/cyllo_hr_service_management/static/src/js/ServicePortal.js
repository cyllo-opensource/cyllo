/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * ServicePortal Widget
 * ---------------------
 * Extends Odoo's publicWidget to handle user interactions when creating
 * service requests from the website portal.
 *
 * Features:
 *  - Auto-assign service handler based on user's related employee.
 *  - Dynamically update department options when service handler changes.
 *  - Show/hide maintenance type and service equipment fields based on category.
 *  - Toggle input visibility and required fields based on request type (custody/service).
 */
publicWidget.registry.ServicePortal = publicWidget.Widget.extend({
    selector: '.cy_service_create',
    events: {
        'change .cy_service_handler': '_onChangeHandler',
        'change .request_type': '_onChangeRequestType',
        'change .category_sel': '_onChangeCategory',
    },

    /**
     * Initializes the widget when the page loads.
     *
     * - Binds the ORM service for RPC calls.
     * - If only one handler option exists, auto-selects it
     *   and updates related department and employee data.
     *
     * @override
     * @returns {Promise} Resolves when widget is initialized.
     */
    start() {
        this.orm = this.bindService("orm");
        var handler = this.$el.find(".cy_service_handler")
        const handler_data = handler[0][1].getAttribute('value')
        var emp_hidden = this.$el.find("#cy_emp_hidden")
        if (handler[0].length == 2){
            var handler_name = handler[0][1].innerText
            var emp_inp = this.el.children[0][1];
            var department = this.$el.find(".handlers_dept")
            department.empty()
            department.append("<option value=" + handler[0][1].getAttribute('data')
            +  ">" + handler[0][1].getAttribute('title') + "</option>")
            handler.empty();
            handler.append("<option value=" + handler_data +
              " data=" + emp_hidden.value + " title=" + emp_inp.getAttribute('title') + ">"
              + handler_name + "</option>")
        }
    },

    /**
     * Handles change of the service handler selection.
     *
     * - Updates the department dropdown to show the handler's department.
     *
     * @param {Event} ev - The change event from the dropdown.
     */
    _onChangeHandler: function(ev) {
        var department = this.$el.find(".handlers_dept")
        department.empty()
        department.append("<option value=" + ev.target.options[ev.target.selectedIndex].getAttribute('data') +
          ">" + ev.target.options[ev.target.selectedIndex].getAttribute('title') + "</option>")
    },

    /**
     * Handles change of the service category.
     *
     * - Fetches the selected category details via ORM.
     * - If the category requires a maintenance order:
     *    - Shows the service equipment and maintenance type fields.
     *    - Marks them as required.
     * - Otherwise, hides and resets those fields.
     *
     * @param {Event} ev - The change event from the category dropdown.
     */
    _onChangeCategory: async function(ev) {
        const ser_category = this.$el.find(".category_sel")
        const ser_equip_div = this.$el.find(".cy-ser_equip")
        const cy_service_equip = this.$el.find(".cy_service_equip")
        const maintenance_type_sel = this.$el.find(".cy_maintenance_type")
        const maintenance_type = this.$el.find(".cy-maintenance_type")
        const category = ev.target.options[ev.target.selectedIndex].value
        if (category) {
          this.orm.searchRead("hr.service.category", [["id", "=", Number(category)]])
            .then(services => {
              const requiresMaintenance = services[0]?.require_maintenance_order;
              ser_equip_div.toggleClass('d-none', !requiresMaintenance);
              cy_service_equip[0].toggleAttribute('required', requiresMaintenance);
              maintenance_type.toggleClass('d-none', !requiresMaintenance);
              maintenance_type_sel[0].toggleAttribute('required', requiresMaintenance);
            });
        } else {
          // Reset elements when category is empty
          ser_equip_div.addClass('d-none');
          cy_service_equip[0].removeAttribute('required');
          maintenance_type.addClass('d-none');
        }
    },

    /**
     * Handles change of the request type (custody/service).
     *
     * - If custody:
     *    - Shows equipment and return date fields (required).
     *    - Hides category field.
     * - If service:
     *    - Shows category field (required).
     *    - Hides equipment and return date fields.
     *
     * @param {Event} ev - The change event from the request type dropdown.
     */
    _onChangeRequestType: function(ev) {
        var equipment = this.$el.find(".equipment")
        var equipment_sel = this.$el.find("#equipment_sel")
        var return_dt_div = this.$el.find(".return_dt_div")
        var return_date = this.$el.find(".return_date")
        var category = this.$el.find(".category")
        var category_sel = this.$el.find(".category_sel")
        if (ev.target.options[ev.target.selectedIndex].value == 'custody'){
          category_sel[0].removeAttribute('required');
          equipment.removeClass('d-none');
          equipment_sel[0].setAttribute('required', true);
          return_dt_div.removeClass('d-none');
          return_date[0].setAttribute('required', true);
          category[0].removeAttribute('required');
          category.addClass('d-none');
        }
        else{
          equipment.addClass('d-none');
          equipment[0].removeAttribute('required');
          return_dt_div.addClass('d-none');
          return_date[0].removeAttribute('required');
          category.removeClass('d-none');
          category_sel[0].setAttribute('required', true);
        }
    },
});