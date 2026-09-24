/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useRef, useEffect, onWillStart, useState, onMounted } from "@odoo/owl";
import { CyAnalyticMixin } from "@cyllo_analytics/js/mixin/cy_dashboard_mixin"
import { GraphTile } from "./components/graph_tile"
import { browser } from "@web/core/browser/browser";
import { KpiSheetChart } from "@cyllo_analytics/js/kpi_sheet_chart";
import { Table } from "@cyllo_analytics/js/table/table";
import { useResize } from "@cyllo_base/js/hooks"
import { FilterDropdown } from "@cyllo_analytics/js/filterDropdown"
import { _t } from "@web/core/l10n/translation";

/**
 * PresentationSelectionMode class for managing presentation preview mode in a dashboard view.
 * @class
 * @extends {CyAnalyticMixin}
 */
export class PresentationSelectionMode extends CyAnalyticMixin(Component) {
    /**
     * Initializes the PresentationSelectionMode class.
     * @function
     */
    setup() {
        this.presentation = true
        super.setup();
        this.edit = true;
        this.presentationRef = useRef("rootRef")
        useResize('collection', (width) => {
            this.state.width = width / 12
        })
        this.val = 0;
        this.selectedStacks = {};
        this.selectedStacksList = [];
        this.collectionRef = useRef('collection')
        this.state = useState({
            autoSlide: false,
            autoSlideTime: 3,
            titlePage: true,
            heading: '',
            subheading: '',
            width: 0,
            darkMode: false,
        })
        onMounted(async () => {
            this.state.heading = this.name
            requestAnimationFrame(() => {
                this.env.bus.trigger('onclickMenuBar', { isCollapse: true });
            });
        });
        useEffect(() => {
            this.state.autoSlideTime = this.state.autoSlideTime < 3 ? 3 : this.state.autoSlideTime
        }, () => [this.state.autoSlideTime])
    }
    addHeading() {
        this.state.heading = this.state.heading.length ? this.state.heading : this.name
    }
    /**
     * Generates a span element for managing counts.
     * @function`
     * @returns {HTMLElement} - The generated span element.
     */
    spanGenerator() {
        var element = document.createElement('span');
        element.className = "fa-stack fa-3x";
        element.setAttribute("data-count", this.val);
        return element;
    }
    /**
     * Manages stacks for counts.
     * @param {number} removedVal - The value to remove from counts.
     * @function
     * @returns {boolean} - True if the operation is successful.
     */
    manageFaStack(removedVal) {
        this.collectionRef.el.querySelectorAll('.fa-stack').forEach(item => {
            if (parseInt(item.dataset.count) > removedVal) {
                let count = parseInt(item.dataset.count);
                count--;
                item.dataset.count = JSON.stringify(count);
            }
        })
        return true;
    }
    /**
     * Handles the click event on a chart.
     * @param {Event} ev - The click event.
     * @async
     * @function
     */
    async onClickChart(ev, hasData, isGraph = true) {
        if (!hasData) return;
        let parentElement = $(ev.target).closest('.card');
        let parentId = parentElement[0].id;
        let dBId = parseInt(parentId.match(/\d+/)[0], 10)
        if (this.selectedStacks.hasOwnProperty(dBId)) {
            delete this.selectedStacks[dBId];
            this.selectedStacksList = this.selectedStacksList.filter(item => item.id !== dBId);
            let spanElement = parentElement.find('.fa-stack')
            let removedVal = spanElement[0].getAttribute('data-count')
            spanElement.remove();
            await this.manageFaStack(parseInt(removedVal))
            this.val--
        } else {
            this.selectedStacks[dBId] = this.ChartData.data.find(item => item.id === dBId);
            this.selectedStacksList.push(this.selectedStacks[dBId]);
            this.val++
            var element = this.spanGenerator()
            if (isGraph) {
                parentElement[0].firstElementChild.append(element)
            }
            else {
                parentElement.append(element)
            }
        }
    }
    /**
     * Creates a presentation with the selected data.
     * @param {string} type - The type of presentation.
     * @async
     * @function
     * @returns {number} - The ID of the created presentation.
     */
    async createPresentation(type) {
        const resId = await this.orm.create("dashboard.presentation", [this.presentationData(type)])
        return resId[0]
    }
    /**
     * Handles the presentation creation.
     * @param {string} type - The type of presentation.
     * @async
     * @function
     * @returns {Object} - The result of the action.
     */
    async handlePresentation(type) {
        if (this.isNoData) {
            return this.notification.add(_t("There is no data to be shown in the presentation"), { type: "warning" });
        }
        const rec_id = await this.createPresentation(type)
        document.documentElement.requestFullscreen();
        return this.actionService.doAction({
            target: "current",
            tag: "presentation_maker",
            type: "ir.actions.client",
            context: this.presentationData(type, rec_id)
        })
    }
    /**
     * Gets the presentation data for creating a presentation.
     * @param {string} type - The type of presentation.
     * @param {number} [rec_id] - The ID of the record for updating a presentation.
     * @returns {Object} - The presentation data.
     * @function
     */
    presentationData(type, rec_id) {
        return {
            rec_id,
            type,
            auto_slide: this.state.autoSlide,
            auto_slide_time: this.state.autoSlideTime,
            title_page: this.state.titlePage,
            title_page_heading: this.state.heading,
            title_page_subheading: this.state.subheading,
            chart_data: this.selectedStacksList.length > 0 ? this.selectedStacksList : this.ChartData.data.filter(item => item.type !== "kpi" && item.data.length),
            style_json: {
                height: '85vh',
                width: '100dvw',
                'margin-top': '0',
            },
            theme: this.themeState.currentTheme,
            theme_json: this.themeState.theme
        }
    }
    /**
     * Toggles the display of additional options.
     * @function
     */
    additionalOption() {
        this.presentationRef.el.querySelector('.additional-options').classList.toggle('open');
    }
    /**
     * Navigates back in the browser history.
     * @function
     */
    goBack() {
        browser.history.go(-1)
    }
    /**
     * Toggles the display of the auto slide duration input field.
     * @function
     */
    toggleAutoSlide() {
        var inputField = this.presentationRef.el.querySelector('#slideDuration')
        inputField.style.display = this.state.autoSlide ? 'block' : 'none';
    }
    /**
     * Toggles the display of the title page details input field.
     * @function
     */
    toggleTitlePage() {
        var titlePageDetails = this.presentationRef.el.querySelector('#titlePageDetails')
        titlePageDetails.style.display = this.state.titlePage ? 'block' : 'none';
    }
    get style() {
        var { width } = this.state
        return {
            height: `${width * 3.1}px;`,
            width: `${width * 3.9}px;`,
        }
    }
    get isNoData() {
        const isNoData = !this.ChartData.data.some(item => Boolean(item.data?.length))
        var isLoading = this.ChartData.loading
        return isLoading ? false : isNoData
    }
    get filterContent() {
        return owl.markup(
            "Choose the desired sequence to showcase your sheets in the presentation."
        );
    }
}
// Define the template for the PresentationSelectionMode component
PresentationSelectionMode.template = "PresentationSelectionMode";
PresentationSelectionMode.components = { GraphTile, KpiSheetChart, Table, FilterDropdown };
registry.category("actions").add("present_selection", PresentationSelectionMode);