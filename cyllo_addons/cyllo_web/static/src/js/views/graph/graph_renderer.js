/** @odoo-module **/
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { patch } from "@web/core/utils/patch";
import { getBorderWhite, DEFAULT_BG, getColor, hexToRGBA } from "@web/core/colors/colors";
import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
const NO_DATA = _t("No data");
import { SEP } from "@web/views/graph/graph_model";
import { sortBy, groupBy } from "@web/core/utils/arrays";

export const LINE_FILL_TRANSPARENCY = 0.4;

///**
// * @param {Object} chartArea
// * @returns {string}
// */
function getMaxWidth(chartArea) {
    const { left, right } = chartArea;
    return Math.floor((right - left) / 1.618) + "px";
}
/**
 * Used to avoid too long legend items.
 * @param {string} label
 * @returns {string} shortened version of the input label
 */
function shortenLabel(label) {
    // string returned could be wrong if a groupby value contain a " / "!
    const groups = label.toString().split(SEP);
    let shortLabel = groups.slice(0, 3).join(SEP);
    if (shortLabel.length > 30) {
        shortLabel = `${shortLabel.slice(0, 30)}...`;
    } else if (groups.length > 3) {
        shortLabel = `${shortLabel}${SEP}...`;
    }
    return shortLabel;
}

patch(GraphRenderer.prototype, {
        getChartConfig() {
        const { mode, modes } = this.model.metaData;
        let data;
        switch (mode) {
            case "bar":
                data = this.getBarChartData();
                break;
            case "line":
                data = this.getLineChartData();
                break;
            case "pie":
                data = this.getPieChartData();
                break
            case "doughnut":
                data = this.getDoughnutChartData();
                break
            case "scatter":
                data = this.getScatterChartData();
                break;
            case "bubble":
                data = this.getBubbleChartData();
                break;
            case "polarArea":
                data = this.getPolarAreaChartData();
                break;
            case "radar":
                data = this.getRadarChartData();
                break;
        }
        const options = this.prepareOptions();
        return { data, options, type: mode };
    },

    /**
     * Returns an object used to style chart elements independently from
     * the datasets.
     * @returns {Object}
     */
    getElementOptions() {
        const { mode, stacked } = this.model.metaData;
        const elementOptions = {};
        if (mode === "bar") {
            elementOptions.bar = { borderWidth: 1 };
        } else if (mode === "line") {
            elementOptions.line = { fill: stacked, tension: 0 };
         } else if (mode === "bubble") {
            elementOptions.bubble = { borderWidth: 1 };
        } else if (mode === "scatter") {
            elementOptions.point = { borderWidth: 1, radius: 5 };
        } else if (mode === "polarArea") {
            elementOptions.polarArea = { borderWidth: 1 };
        } else if (mode === "radar") {
            elementOptions.line = { borderWidth: 1, pointStyle: 'circle' };  // Correct element type is line
            elementOptions.point = { radius: 5 };  // Optional: for better visibility of points
        }
        return elementOptions;
    },

    getScaleOptions() {
        const labels = this.model.data.labels;
        const { allIntegers, fields, groupBy, measure, measures, mode, stacked } = this.model.metaData;

        // Pie and Doughnut charts don't use scales
        if (mode === "pie" || mode === "doughnut") {
            return {};
        }
        const xAxe = {
            type: "category",
            title: {
                display: Boolean(groupBy.length),
                text: groupBy.length ? fields[groupBy[0].fieldName].string : "",
            },
            ticks: {
                callback: (val, index) => {
                    const value = labels[index];
                    return shortenLabel(value);
                },
            },
        };

        const yAxe = {
            type: "linear",
            title: {
                text: measures[measure].string,
            },
            ticks: {
                callback: (value) => this.formatValue(value, allIntegers),
            },
            suggestedMax: 0,
            suggestedMin: 0,
            stacked: mode === "line" && stacked ? stacked : undefined,
        };

        // Radar and Polar Area charts use radial scales
        if (mode === "radar" || mode === "polarArea" ) {
            return {
                r: {
                    angleLines: {
                        display: true
                    },
                    suggestedMin: 0,
                    suggestedMax: 100, // Adjust as needed based on your data
                    ticks: {
                        callback: (value) => this.formatValue(value, allIntegers),
                    },
                    title: {
                        display: Boolean(measure),
                        text: measures[measure] ? measures[measure].string : "",
                    }
                }
            };
        }
        return { x: xAxe, y: yAxe };
    },


    /**
     * Returns the options used to configure the legend of the chart.
     * @returns {Object}
     */
    getLegendOptions() {
        const { mode } = this.model.metaData;
        const data = this.model.data;
        const refLength = ['pie', 'doughnut', 'polarArea'].includes(mode) ? data.labels.length : data.datasets.length;

        const legendOptions = {
            display: refLength <= 20, // Display legend only if there are 20 or fewer items
            position: "top",
            onHover: this.onlegendHover.bind(this),
            onLeave: this.onlegendHover.bind(this),
        };

        if (['line', 'scatter', 'bubble'].includes(mode)) {
            legendOptions.onClick = this.onLegendClick.bind(this);
        }

        if (['pie', 'doughnut', 'polarArea'].includes(mode)) {
            legendOptions.labels = {
                generateLabels: (chart) => {
                    const dataset = chart.data.datasets[0];
                    const { labels } = chart.data;
                    const meta = chart.getDatasetMeta(0);

                    return labels.map((label, index) => {
                        const arc = meta.data[index];
                        const custom = arc && arc.custom || {};
                        const arcOpts = chart.options.elements.arc;
                        const fillStyle =
                            label === NO_DATA
                                ? DEFAULT_BG
                                : getColor(index, cookie.get("color_scheme"));
                        const hidden = !chart.getDataVisibility(index);

                        return {
                            text: shortenLabel(label),
                            fullText: label,
                            fillStyle: fillStyle,
                            strokeStyle: custom.borderColor || arcOpts.borderColor,
                            lineWidth: arcOpts.borderWidth,
                            hidden: hidden,
                            index: index,
                            datasetIndex: 0,
                        };
                    });
                },
            };
        } else if (['bar'].includes(mode)) {
            const referenceColor = mode === "bar" ? "backgroundColor" : "borderColor";
            legendOptions.labels = {
                generateLabels: (chart) => {
                    return chart.data.datasets.map((dataset, index) => {
                        return {
                            text: shortenLabel(dataset.label),
                            fullText: dataset.label,
                            fillStyle: dataset[referenceColor],
                            hidden: !chart.isDatasetVisible(index),
                            lineCap: dataset.borderCapStyle,
                            lineDash: dataset.borderDash,
                            lineDashOffset: dataset.borderDashOffset,
                            lineJoin: dataset.borderJoinStyle,
                            lineWidth: dataset.borderWidth,
                            strokeStyle: dataset[referenceColor],
                            pointStyle: dataset.pointStyle,
                            datasetIndex: index,
                        };
                    });
                },
            };
        } else if (['radar'].includes(mode)) {
            legendOptions.labels = {
                generateLabels: (chart) => {
                    return chart.data.datasets.map((dataset, index) => {
                        return {
                            text: shortenLabel(dataset.label),
                            fullText: dataset.label,
                            fillStyle: getColor(index, cookie.get("color_scheme")),
                            hidden: !chart.isDatasetVisible(index),
                            lineCap: dataset.borderCapStyle,
                            lineDash: dataset.borderDash,
                            lineDashOffset: dataset.borderDashOffset,
                            lineJoin: dataset.borderJoinStyle,
                            lineWidth: dataset.borderWidth,
                            strokeStyle: dataset.borderColor || getColor(index, cookie.get("color_scheme")),
                            pointStyle: dataset.pointStyle,
                            datasetIndex: index,
                        };
                    });
                },
            };
        }
        else if (['bubble'].includes(mode)) {
        legendOptions.labels = {
            generateLabels: (chart) => {
                return chart.data.datasets.map((dataset, index) => {
                    const radius = dataset.data.length ? dataset.data[0].r : 5;
                    return {
                        text: shortenLabel(dataset.label),
                        fullText: dataset.label,
                        fillStyle: getColor(index, cookie.get("color_scheme")),
                        hidden: !chart.isDatasetVisible(index),
                        strokeStyle: dataset.borderColor || getColor(index, cookie.get("color_scheme")),
                        pointStyle: dataset.pointStyle,
                        radius: radius,
                        datasetIndex: index,
                    };
                });
            },
        };
    }

        return legendOptions;
    },


/**
 * Returns the data configuration for a Doughnut chart.
 * @returns {Object} The data object for the chart.
 */
    getDoughnutChartData() {
        const { domains } = this.model.metaData;
        const data = this.model.data;

        // Generate unique colors for each segment
        const colors = data.labels.map((_, index) => getColor(index, cookie.get("color_scheme")));
        const borderColor = getBorderWhite(cookie.get("color_scheme"));

        // Apply unique colors to each dataset
        for (const dataset of data.datasets) {
            dataset.backgroundColor = colors; // Each segment should have a unique color
            dataset.borderColor = borderColor;
        }

        // Ensure there is a zone associated with every origin
        const representedOriginIndexes = new Set(
            data.datasets.map((dataset) => dataset.originIndex)
        );

        let addNoDataToLegend = false;
        const fakeData = new Array(data.labels.length + 1).fill(1);
        const fakeTrueLabels = new Array(data.labels.length + 1).fill(NO_DATA);

        for (let index = 0; index < domains.length; ++index) {
            if (!representedOriginIndexes.has(index)) {
                data.datasets.push({
                    label: domains[index].description,
                    data: fakeData,
                    trueLabels: fakeTrueLabels,
                    backgroundColor: [...colors, DEFAULT_BG], // Add a unique color for "No Data" if needed
                    borderColor,
                });
                addNoDataToLegend = true;
            }
        }

        if (addNoDataToLegend) {
            data.labels.push(NO_DATA);
        }

        return data;
    },


    getScatterChartData() {
        const { domains } = this.model.metaData;
        const data = this.model.data;

        // Style/complete data
        // Assign colors to datasets
        const colors = data.datasets.map((_, index) => getColor(index, cookie.get("color_scheme")));
        const borderColor = getBorderWhite(cookie.get("color_scheme"));

        for (const [index, dataset] of data.datasets.entries()) {
            dataset.backgroundColor = colors[index];
            dataset.borderColor = borderColor;
            dataset.pointBackgroundColor = colors[index]; // Scatter charts often use background color for points
            dataset.pointBorderColor = borderColor; // and border color for points
        }

        // Make sure there is a zone associated with every origin
        const representedOriginIndexes = new Set(
            data.datasets.map((dataset) => dataset.originIndex)
        );
        let addNoDataToLegend = false;
        const fakeData = new Array(data.labels.length + 1).fill(null).map((_, index) => ({
            x: index,
            y: Math.random() // Adding random y-values for demonstration
        }));
        const fakeTrueLabels = new Array(data.labels.length + 1).fill(NO_DATA);

        for (let index = 0; index < domains.length; ++index) {
            if (!representedOriginIndexes.has(index)) {
                data.datasets.push({
                    label: domains[index].description,
                    data: fakeData,
                    trueLabels: fakeTrueLabels,
                    backgroundColor: colors[index],
                    borderColor,
                    pointBackgroundColor: colors[index],
                    pointBorderColor: borderColor,
                });
                addNoDataToLegend = true;
            }
        }
        if (addNoDataToLegend) {
            data.labels.push(NO_DATA);
        }

        return data;
    },

    getPolarAreaChartData() {
        const { domains } = this.model.metaData;
        const data = this.model.data;

        // Assign colors to datasets
        const colors = data.labels.map((_, index) => getColor(index, cookie.get("color_scheme")));
        const borderColor = getBorderWhite(cookie.get("color_scheme"));

        for (const dataset of data.datasets) {
            dataset.backgroundColor = colors;
            dataset.borderColor = borderColor;
        }

        // Ensure every domain has a dataset
        const representedOriginIndexes = new Set(
            data.datasets.map((dataset) => dataset.originIndex)
        );
        let addNoDataToLegend = false;
        const fakeData = new Array(data.labels.length).fill(1); // Polar area charts need actual data points

        for (let index = 0; index < domains.length; ++index) {
            if (!representedOriginIndexes.has(index)) {
                data.datasets.push({
                    label: domains[index].description,
                    data: fakeData,
                    backgroundColor: colors,
                    borderColor,
                });
                addNoDataToLegend = true;
            }
        }

        return data;
    },


    getRadarChartData() {
        const { domains } = this.model.metaData;
        const data = this.model.data;

        // Assign colors to datasets
        const colors = data.datasets.map((_, index) => getColor(index, cookie.get("color_scheme")));
        const borderColor = getBorderWhite(cookie.get("color_scheme"));

        for (const [index, dataset] of data.datasets.entries()) {
            dataset.backgroundColor = colors[index].replace('1)', '0.2)'); // Slightly transparent fill
            dataset.borderColor = borderColor;
            dataset.pointBackgroundColor = colors[index];
            dataset.pointBorderColor = borderColor;
        }

        // Ensure every domain has a dataset
        const representedOriginIndexes = new Set(
            data.datasets.map((dataset) => dataset.originIndex)
        );
        let addNoDataToLegend = false;
        const fakeData = new Array(data.labels.length).fill(0); // Radar charts need actual data points

        for (let index = 0; index < domains.length; ++index) {
            if (!representedOriginIndexes.has(index)) {
                data.datasets.push({
                    label: domains[index].description,
                    data: fakeData,
                    backgroundColor: colors[index].replace('1)', '0.2)'),
                    borderColor,
                    pointBackgroundColor: colors[index],
                    pointBorderColor: borderColor,
                });
                addNoDataToLegend = true;
            }
        }

        return data;
    },

    getBubbleChartData() {
        const { domains } = this.model.metaData;
        const data = this.model.data;

        // Assign colors to datasets
        const colors = data.datasets.map((_, index) => getColor(index, cookie.get("color_scheme")));
        const borderColor = getBorderWhite(cookie.get("color_scheme"));

        for (const [index, dataset] of data.datasets.entries()) {
            dataset.backgroundColor = colors[index];
            dataset.borderColor = borderColor;
            dataset.data.radius = dataset.data[index]/10;
        }


        // Ensure every domain has a dataset
        const representedOriginIndexes = new Set(
            data.datasets.map((dataset) => dataset.originIndex)
        );
        let addNoDataToLegend = false;

        // Generate fake data points for demonstration
        const fakeData = new Array(data.labels.length).fill(null).map((_, index) => ({
            x: index,
            y: Math.random(), // Random y-values for demonstration
            r: Math.random() * 20 + 5 // Random radius between 5 and 25
        }));

        for (let index = 0; index < domains.length; ++index) {
            if (!representedOriginIndexes.has(index)) {
                data.datasets.push({
                    label: domains[index].description,
                    data: fakeData,
                    backgroundColor: colors[index],
                    borderColor,
                });
                addNoDataToLegend = true;
            }
        }
        if (addNoDataToLegend) {
            data.labels.push(NO_DATA);
        }

        return data;
    },

    getTooltipItems(data, metaData, tooltipModel) {
        const { allIntegers, domains, mode, groupBy } = metaData;
        const sortedDataPoints = sortBy(tooltipModel.dataPoints, "raw", "desc");
        const items = [];
        for (const item of sortedDataPoints) {
            const index = item.dataIndex;
            const dataset = data.datasets[item.datasetIndex] || this.model.lineOverlayDataset;
            let label = dataset.trueLabels[index];
            let value = dataset.data[index];
            let formattedValue;
            let boxColor;
            let percentage;

             if (['pie', 'doughnut', 'polarArea'].includes(mode)) {
                if (label === NO_DATA) {
                    formattedValue = this.formatValue(0, allIntegers);
                } else {
                    formattedValue = this.formatValue(value, allIntegers);
                }
                if (groupBy.length > 1 || domains.length > 1) {
                    label = `${label} / ${dataset.label}`;
                }
                boxColor = dataset.backgroundColor[index];
                const totalData = dataset.data.reduce((a, b) => a + b, 0);
                percentage = totalData && ((value * 100) / totalData).toFixed(2);
            } else if (mode === "bubble") {
                if (label === NO_DATA) {
                    formattedValue = this.formatValue(0, allIntegers);
                } else {
                    formattedValue = this.formatValue(value, allIntegers);
                }
                boxColor = dataset.backgroundColor || dataset.borderColor;
                if (groupBy.length > 1 || domains.length > 1) {
                    label = `${label} / ${dataset.label}`;
                }
            } else {
                formattedValue = this.formatValue(value, allIntegers);
                if (groupBy.length > 1 || domains.length > 1) {
                    label = `${label} / ${dataset.label}`;
                }
                if (mode === "bar") {

                boxColor = dataset.backgroundColor;}
                else {
                boxColor = dataset.backgroundColor || dataset.borderColor;}
            }

            items.push({ label, value: formattedValue, boxColor, percentage });
        }
        return items;
    },
});
