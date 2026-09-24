/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SelectCommissionPlan = publicWidget.Widget.extend({
  selector: ".commission-container",
  events: {
    "click .plan-card": "_selectPlan",
    "click #compareToggle": "_toggleCompareTable",
  },
  start: function () {
    this.planCards = this.el.querySelectorAll(".plan-card");
    this.radioInputs = this.el.querySelectorAll(".radio-input");
    this.selectedPlanInput = this.el.querySelector("#selectedPlanInput");
    this.submitBtn = this.el.querySelector("#submitBtn");
    this.validationMessage = this.el.querySelector("#validationMessage");
    this.compareToggle = this.el.querySelector("#compareToggle");
    this.comparisonTable = this.el.querySelector("#comparisonTable");
    return this._super(...arguments);
  },
  _selectPlan: function (ev) {
    this.planCards.forEach((card) => {
      card.classList.remove("selected");
      const btn = card.querySelector(".select-btn");
      if (btn) {
        btn.classList.remove("selected");
        btn.textContent = "Select Plan"; // Reset text back
      }
    });
    const selectedCard = ev.currentTarget;
    const planId = selectedCard.dataset.planId;
    const selectBtn = selectedCard.querySelector(".select-btn");
    const submitBtn = selectedCard.querySelector(".submit-btn");
    if (selectBtn) {
      selectBtn.classList.add("selected");
      selectBtn.textContent = "Selected";
    }
    selectedCard.classList.add("selected");
    if (this.selectedPlanInput) {
      this.selectedPlanInput.value = planId;
    }
    this.submitBtn.disabled = false;
    this.validationMessage.style.display = "none";
  },
  _toggleCompareTable: function (ev) {
    comparisonTable.classList.toggle("active");
    compareToggle.classList.toggle("active");
  },
});

export default publicWidget.registry.SelectCommissionPlan;
