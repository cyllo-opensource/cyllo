/** @odoo-module **/
import {JournalDashboardGraphField} from '@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field';
import {patch} from "@web/core/utils/patch";
import { hexToRGBA } from "@web/core/colors/colors";

patch(JournalDashboardGraphField.prototype, {
    setup() {
        super.setup(...arguments);
    },

    getLineChartConfig() {
        const [firstDataset] = this.data;
        const chartLabels = firstDataset.values.map((point) => point.x);
        const primaryLineColor = "#9EA700";
        const isSample = firstDataset.is_sample_data;

        const borderColor = isSample ? hexToRGBA(primaryLineColor, 0.1) : primaryLineColor;
        const backgroundColor = isSample
            ? hexToRGBA(primaryLineColor, 0.05)
            : hexToRGBA(primaryLineColor, 0.2);

        return {
            type: "line",
            data: {
                labels: chartLabels,
                datasets: [
                    {
                        backgroundColor,
                        borderColor,
                        data: firstDataset.values,
                        fill: "start",
                        label: firstDataset.key,
                        borderWidth: 2,
                    },
                ],
            },
            options: {
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        intersect: false,
                        position: "nearest",
                        caretSize: 0,
                    },
                },
                scales: {
                    y: { display: false },
                    x: { display: false },
                },
                maintainAspectRatio: false,
                elements: {
                    line: {
                        tension: 0.000001,
                    },
                },
            },
        };
    },

    /**
     * Generate the configuration for the bar chart.
     * @returns {Object} Chart configuration
     */
    getBarChartConfig() {
        const [firstDataset] = this.data;
        const barData = [];
        const labelList = [];
        const backgroundColors = [];
        const pastBarColor = "#C1E1C1";
        const futureBarColor = "#ADD8E6";

        firstDataset.values.forEach((entry) => {
            barData.push(entry.value);
            labelList.push(entry.label);

            if (entry.type === "past") {
                backgroundColors.push(pastBarColor);
            } else if (entry.type === "future") {
                backgroundColors.push(futureBarColor);
            } else {
                backgroundColors.push("#ebebeb");
            }
        });

        return {
            type: "bar",
            data: {
                labels: labelList,
                datasets: [
                    {
                        backgroundColor: backgroundColors,
                        data: barData,
                        fill: "start",
                        label: firstDataset.key,
                    },
                ],
            },
            options: {
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        intersect: false,
                        position: "nearest",
                        caretSize: 0,
                    },
                },
                scales: {
                    y: { display: false },
                },
                maintainAspectRatio: false,
                elements: {
                    line:{
                        tension: 0.000001,
                    },
                },
            },
        };
    },
});