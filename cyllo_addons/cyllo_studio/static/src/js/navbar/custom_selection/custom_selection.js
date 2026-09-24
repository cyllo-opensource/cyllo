/** @odoo-module **/
import { Component, useState, onWillUpdateProps, onMounted } from "@odoo/owl";
/**
 * CustomSelection Component
 *
 * Provides a dropdown UI for selecting a button style.
 * Supports both regular button classes and "link" styles with `text-*` colors.
 *
 * Props:
 * - defaultClass: The initial class string applied to the button.
 * - onChange: Callback function called when the selected class changes.
 *
 * State:
 * - showDropdown: Boolean to toggle the dropdown visibility.
 * - class: Array of current CSS classes applied to the button.
 * - selectedOption: Currently selected option object ({label, value, color}).
 * - isLinkStyle: Boolean indicating if the button uses a "link" style.
 *
 * Methods:
 * - processClass: Determines selected option and link style from the class string.
 * - handleOptionClick: Updates state and calls `onChange` when an option is clicked.
 * - setShowDropdown: Toggles dropdown visibility.
 */
export class CustomSelection extends Component {
  setup() {
    this.options = [
      { label: "Primary", value: "btn-primary", color: "#9ea700" },
      { label: "Secondary", value: "btn-secondary", color: "#EEEEEE" },
      { label: "Info", value: "btn-info", color: "#0180A5" },
      { label: "Warning", value: "btn-warning", color: "#9a6b01" },
      { label: "Danger", value: "btn-danger", color: "#dc3545" },
    ];
    this.state = useState({
      showDropdown: false,
      class: [],
      selectedOption: null,
      isLinkStyle: false,
    });

    // Set initial class based on defaultClass prop
    this.processClass(this.props.defaultClass);

    onWillUpdateProps((nextProps) => {
      this.processClass(nextProps.defaultClass);
    });

    // Add global click listener to close dropdown
    onMounted(async () => {
        window.addEventListener("click", (e) => {
            if (document.querySelector(".custom_selection_dropdown_active")) {
                this.setShowDropdown()
            }
        });
    });


  }
    /**
   * Processes a class string to determine selected option and link style.
   * @param {string} buttonClass - The CSS class string applied to the button
   */
  processClass(buttonClass) {
    if (buttonClass) {
      let classArray = buttonClass?.split(" ");
      let classIndex = -1;
      let optionArray = this.options.filter((option) => {
        const linkValue = "text-" + option.value.split("-")[1];
        const isLink =
          classArray.includes("btn-link") || classArray.includes(linkValue);
        let index = -1;
        if (
          classArray.includes(option.value) &&
          !classArray.includes("btn-link")
        ) {
          index = classArray.indexOf(option.value);
          classIndex = index !== -1 ? index : classIndex;
          return true;
        } else if (isLink) {
          index = classArray.indexOf(linkValue);
          classIndex = index !== -1 ? index : classIndex;
          return (
            index !== -1 ||
            (!buttonClass.includes("text-") && option.value === "btn-primary")
          );
        }
      });
       // Set selected option and determine link style
      if (optionArray.length === 1) {
        this.state.selectedOption = optionArray[0];
        if (classIndex !== -1) {
          let removedClass = classArray.splice(classIndex, 1)[0];
          this.state.isLinkStyle = removedClass.split("-")[0] !== "btn";
        } else {
          this.state.isLinkStyle = true;
        }
        this.state.class = classArray;
      } else {
        this.state.class = classArray;
        this.state.selectedOption = "";
      }
    }
  }
  /**
   * Handles click on a dropdown option.
   * Updates state and calls the onChange callback with new class string.
   * @param {Object} option - The selected option object
   */
  async handleOptionClick(option) {
    this.state.selectedOption = option;
    await this.setShowDropdown(false);
    if (this.state.isLinkStyle) {
      if (!this.state.class.includes("btn-link")) {
        this.state.class.push("btn-link");
      }
      this.state.class.push("text-" + option.value.split("-")[1]);
    } else {
      this.state.class.push(option.value);
    }
    this.props.onChange(this.state.class.join(" "));
  }
   /**
   * Toggles the dropdown visibility
   * @param {boolean} val - Optional value to force dropdown state
   */
  setShowDropdown(val = !this.state.showDropdown) {
    this.state.showDropdown = val;
    const el = document.querySelector(".custom_selection_dropdown");
  }
}

CustomSelection.template = "cyllo_studio.CustomSelection";
