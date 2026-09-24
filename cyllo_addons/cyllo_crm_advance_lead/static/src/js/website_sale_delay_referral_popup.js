/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.ProductReferral = publicWidget.Widget.extend({
  selector: "#referral_modal",
  events: {
    "click #refer": "_onReferClick",
    "click #close": "_onCloseClick",
  },
  async start() {
    this._super(...arguments);
    if (this.el.querySelector("#is_referral").value) {
      setTimeout(() => {
        var location = this.el.querySelector("#location_temp");
        if (location) {
          location.style.display = "block";
        }
      }, 1000);
    }
  },
  _onReferClick() {
    var order_id = this.el.querySelector("#order").value;
    window.location.href = `/referral?order_id=${order_id}`;
  },
  _onCloseClick() {
    var location = this.el.querySelector("#location_temp");
    location.style.display = "none";
  },
});
