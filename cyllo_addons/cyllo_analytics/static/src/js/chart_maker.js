/** @odoo-module **/
import { worldMapChart } from "./charts/world_map";
import { loadingChart } from "./charts/loadingChart"
import { _t } from "@web/core/l10n/translation";


/**
 * Converts a string to title case.
 * @param {string} inputString - The input string to be converted to title case.
 * @param {string} [splitBy="_"] - The character to split the input string.
 * @returns {string} - The input string converted to title case.
 */
export const convertToTitleCase = (inputString, splitBy = "_") => {
    var titleCaseString = inputString
    if (inputString) {
        const words = inputString.split(splitBy);
        titleCaseString = words
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }
    return titleCaseString;
}
export const getChartZoom = (chart) => {
    switch (chart) {
        case "pictorialBar":
            return 10
        case "line":
            return 10
        default:
            return 0
    }
}

// Category axis labels: characters kept before the "..." and the number of
// categories below which every single label is still drawn.
const MAX_LABEL_LENGTH = 12;
const MAX_FULL_LABELS = 12;
// Categories the initial (un-scrolled) view opens with at most.
const MAX_VISIBLE_CATEGORIES = 20;

export class ChartMaker {
    /**
     * Constructor for the ChartMaker class.
     * @param {Array} data - The data for the chart.
     * @param {string} dimension - The dimension of the chart.
     * @param {Array} measures - The measures for the chart.
     * @param {string} name - The name of the chart.
     * @param {string} type - The type of chart (e.g., 'bar', 'line', 'pie', 'doughnut').
     * @param {string} dimension_axis - The dimension axis ('x' or 'y').
     * @param {object} params - Additional parameters for the chart (optional).
     */
    constructor(data, dimension, measures, name, type, dimension_axis, params = {}) {
        this.data = data
        this.dimension = dimension
        this.measures = measures
        this.name = name
        this.type = type
        this.dimension_axis = dimension_axis
        this.params = params
        this.color_mappings = params.color_mappings || []
        this.annotations = params.annotations || []
        this.themeColor = params.themeColor || {}
        this.hidePieSliceLabels = params.hidePieSliceLabels || false
        this.pieLegendBottom = ['pie', 'doughnut'].includes(type) ? true : params.pieLegendBottom;
        this.chartOptions = {};
    }

    /** Subtle grid (split) line color — faint so it doesn't glare in dark mode. */
    get _splitLineColor() {
        return this.params.isDarkMode ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.09)';
    }

    /** Axis baseline / tick color — slightly stronger than the grid lines. */
    get _axisLineColor() {
        return this.params.isDarkMode ? 'rgba(255, 255, 255, 0.28)' : 'rgba(0, 0, 0, 0.25)';
    }

    getPointMappings(measureAlias, value, dimensionLabel = null) {
        if ((!this.color_mappings || !this.color_mappings.length) && (!this.annotations || !this.annotations.length)) return [];
        const matches = [];

        // 1. Find Dedicated Business Annotation (Manual double-click context)
        if (dimensionLabel && this.annotations && this.annotations.length) {
            const annotation = this.annotations.find(a =>
                a.measure_alias === measureAlias &&
                (a.dimension_label === String(dimensionLabel) || a.dimension_label === dimensionLabel)
            );
            if (annotation) {
                matches.push({ ...annotation, is_annotation: true });
            }
        }

        // 2. Find Range mapping (Automated Indicator rule)
        if (this.color_mappings && this.color_mappings.length) {
            const rangeMatch = this.color_mappings.find(m => {
                if (m.measure_alias !== measureAlias) return false;

                const min = parseFloat(m.min_value);
                const val = parseFloat(value);
                const maxStr = String(m.max_value || '').toLowerCase().trim();

                if (maxStr === 'all above' || maxStr === '') {
                    return val >= min;
                }
                return val >= min && val <= parseFloat(m.max_value);
            });
            if (rangeMatch) matches.push(rangeMatch);
        }

        return matches;
    }

    getPointColor(measureAlias, value) {
        // Colors are ONLY derived from indicator rules (the color_mappings section)
        if (!this.color_mappings || !this.color_mappings.length) return null;

        const rangeMatch = this.color_mappings.find(m => {
            if (m.measure_alias !== measureAlias) return false;

            const min = parseFloat(m.min_value);
            const val = parseFloat(value);
            const maxStr = String(m.max_value || '').toLowerCase().trim();

            if (maxStr === 'all above' || maxStr === '') {
                return val >= min;
            }
            return val >= min && val <= parseFloat(m.max_value);
        });

        return rangeMatch ? rangeMatch.color : null;
    }

    getMeasureColor(measureAlias) {
        if (!this.color_mappings || !this.color_mappings.length) return null;
        const mapping = this.color_mappings.find(m => m.measure_alias === measureAlias);
        return mapping ? mapping.color : null;
    }

    getDefaultZoom() {
        const length = this.data.length * this.measures.length
        const START_VALUES = [
            { threshold: 4500, value: 90 },
            { threshold: 3500, value: 88 },
            { threshold: 2500, value: 86 },
            { threshold: 1500, value: 84 },
            { threshold: 1000, value: 82 },
            { threshold: 500, value: 80 },
            { threshold: 400, value: 75 },
            { threshold: 350, value: 70 },
            { threshold: 100, value: 50 },
            { threshold: 15, value: 30 },
            { threshold: 0, value: 0 },
        ];
        const getStartValue = () => {
            for (const { threshold, value } of START_VALUES) {
                if (length > threshold) {
                    return value + getChartZoom(this.type) + this.measures.length;
                }
            }
        };
        let startValue = getStartValue()
        if (this.type === 'line') {
            startValue += 5 * (this.measures.length)
        } else if (this.type === 'bar') {
            startValue += 8 * (this.measures.length)
        }
        let endValue = 100 - (startValue >= 100 ? 95 : startValue);
        const totalCategories = this.data.length;
        if (totalCategories > MAX_VISIBLE_CATEGORIES) {
            endValue = Math.min(endValue, (MAX_VISIBLE_CATEGORIES / totalCategories) * 100);
        }
        const dataZoom = [
            {
                type: 'inside',
                xAxisIndex: this.dimension_axis === "x" ? 0 : undefined,
                yAxisIndex: this.dimension_axis === "x" ? undefined : 0,
                start: 0,
                end: endValue,
                zoomOnMouseWheel: false,
                moveOnMouseMove: true,
                moveOnMouseWheel: false
            }
        ]
        return dataZoom
    }

    /**
     * Generate graph options for the chart.
     * @returns {object} - The graph options for the chart.
     */
    makeGraphOptions() {
        if (!this.data?.length) {
            return loadingChart({
                text: _t('No Data Found'),
                loop: false,
                title: this.name
            })
        }
        var legends = {
            data: [this.name]
        }
        const richLabels = {};
        const buildImagePath = (val) => {
            if (typeof val === 'string' && val.startsWith('CY_IMAGE:')) {
                const parts = val.split(':');
                return `/web/image?model=${parts[1]}&field=${parts[2]}&id=${parts[3]}`;
            }
            return null;
        };

        var formatter = (params) => {
            let value = params.name || params;
            const imgPath = buildImagePath(value);
            let content = "";
            if (imgPath) {
                const parts = value.split(':');
                content = `${params.seriesName} <br/><img src="${imgPath}" style="max-height: 50px; max-width: 50px; border-radius: 4px; margin-top: 5px;"/><br/>ID: ${parts[3] || '?'}<br/>Value: ${params.value}`;
            } else {
                content = `${params.seriesName} <br/>${value} : ${params.value}`;
            }

            // Get all matching mappings (both point-specific and range-based)
            const alias = this.measures[params.seriesIndex];
            const mappings = this.getPointMappings(alias, params.value, params.name);

            let hasAddedLine = false;
            mappings.forEach(mapping => {
                const label = mapping.is_annotation ? "Note" : "Indicator";
                const infoText = mapping.indicator || mapping.notes;

                if (infoText) {
                    const topMargin = hasAddedLine ? 4 : 8;
                    const topPadding = hasAddedLine ? 0 : 5;
                    const topBorder = hasAddedLine ? 'none' : '1px solid rgba(255,255,255,0.2)';
                    content += `<div style="margin-top: ${topMargin}px; padding-top: ${topPadding}px; border-top: ${topBorder}; font-size: 11px; font-style: italic; opacity: 0.9;"><strong>${label}:</strong> ${infoText}</div>`;
                    hasAddedLine = true;
                }
            });
            return content;
        }

        this.hasItemStyle = this.measures.includes("itemStyle")
        if (this.hasItemStyle) {
            this.measures = this.measures.filter(item => item !== 'itemStyle')
        }
        this.chartOptions.formatter = formatter
        if (this.measures.length > 2) {
            legends = {
                data: []
            }
            this.measures.forEach((key) => {
                const label = this.params.measureNames && this.params.measureNames[key] ? this.params.measureNames[key] : convertToTitleCase(key);
                legends.data.push(label)
            })
        }
        const _defaultPalette = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc'];
        // Pre-compute the base color for each measure (same palette used in legendData)
        const measureBaseColors = this.measures.map((key, index) => {
            if (this.params.themeColor && this.params.themeColor.length > 0) {
                return this.params.themeColor[index % this.params.themeColor.length];
            }
            return _defaultPalette[index % _defaultPalette.length];
        });

        var series = []
        this.measures.forEach((key, index) => {
            const label = this.params.measureNames && this.params.measureNames[key] ? this.params.measureNames[key] : convertToTitleCase(key);
            const baseColor = measureBaseColors[index];
            series.push({
                name: label,
                id: key,
                type: this.type,
                data: [],
                // Pin the base series color so legend and bars always use the same hue.
                color: baseColor,
                animationDelay: (idx) => idx * 50,
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 10
                    }
                },
                itemStyle: {
                    color: (params) => {
                        const customColor = this.getPointColor(key, params.value);
                        return customColor || params.color;
                    }
                }
            })
        })

        var dataZoom = this.getDefaultZoom();

        // Calculate dynamic image size to prevent congestion
        let hasImage = this.data && this.data.some(item => typeof item[this.dimension] === 'string' && item[this.dimension].startsWith('CY_IMAGE:'));
        let imgSize = 30;

        if (hasImage) {
            let totalItems = this.data ? this.data.length : 0;
            const maxVisible = 12; // Enforce stricter limit for smaller builder panels so images never overlap

            if (totalItems > maxVisible && dataZoom && dataZoom[0]) {
                const visiblePercentage = (maxVisible / totalItems) * 100;
                dataZoom[0].start = 0;
                dataZoom[0].end = Math.min(100, visiblePercentage);
            }

            let visibleItems = totalItems;
            if (dataZoom && dataZoom[0]) {
                const start = dataZoom[0].start;
                const end = dataZoom[0].end;
                visibleItems = Math.max(1, Math.ceil((totalItems * (end - start)) / 100));
            }
            // Use safe baseline container width of 400px for tight dashboards
            const estimatedSpace = 400 / visibleItems;
            const maxImgSize = 32; // Limit max size so line charts don't scale too large and overlap
            const minImgSize = 25; // Keep a readable minimum

            imgSize = Math.max(minImgSize, Math.min(maxImgSize, Math.floor(estimatedSpace * 0.8)));
        }

        // Pre-populate rich labels
        this.richLabels = richLabels;
        this.data && this.data.forEach(item => {
            const val = item[this.dimension];
            const imgPath = buildImagePath(val);
            if (imgPath) {
                const key = val.replace(/[^a-zA-Z0-9]/g, '_');
                this.richLabels[key] = {
                    backgroundColor: {
                        image: imgPath
                    },
                    height: imgSize,
                    width: imgSize,
                    borderRadius: 4
                };
            }
        });

        const hasRichLabels = Object.keys(this.richLabels).length > 0;
        var xAxis = {
            data: [],
            type: 'category',
            axisLabel: {
                interval: (hasRichLabels || this.data.length <= MAX_FULL_LABELS) ? 0 : 'auto',
                hideOverlap: !hasRichLabels,
                margin: 10,  // Gap between the axis line and the label
                ...(hasRichLabels ? {} : { padding: [0, 6, 0, 6] }),
                rotate: hasRichLabels ? 0 : (this.data.length > 6 ? 45 : 0),  // Disable rotate for images
                fontSize: 10,
                color: this.params.isDarkMode ? '#cccccc' : '#333333',
                formatter: function (value) {
                    if (typeof value === 'string' && value.startsWith('CY_IMAGE:')) {
                        const key = value.replace(/[^a-zA-Z0-9]/g, '_');
                        return `{${key}|}`;
                    }
                    const label = String(value ?? '');
                    return label.length > MAX_LABEL_LENGTH
                        ? label.substring(0, MAX_LABEL_LENGTH).trimEnd() + '...'
                        : label;
                },
                rich: this.richLabels
            },
            axisLine: { lineStyle: { color: this._axisLineColor } },
            axisTick: { lineStyle: { color: this._axisLineColor } },
            splitLine: { show: false },
        }

        this.data && this.data.forEach((item, mi) => {
            xAxis.data.push(item[this.dimension])
            this.measures.forEach((key, i) => {
                series[i].data.push(item[key])
            })
        })
        var yAxis = {
            type: "value",
            axisLabel: {
                color: this.params.isDarkMode ? '#cccccc' : '#333333'
            },
            axisLine: { lineStyle: { color: this._axisLineColor } },
            splitLine: { lineStyle: { color: this._splitLineColor } },
        }

        let titleBgColor = '#ffffff';
        let titleTextColor = '#333333';
        let legendIconColor = '#e0e0e0';
        if (this.params?.themeColor && this.params.themeColor.length > 0) {
            titleBgColor = this.params.themeColor[0];
            titleTextColor = '#ffffff';
            legendIconColor = '#ffffff';
        }

        const defaultPalette = _defaultPalette;
        var legendData = this.measures.map((key, index) => {
            const label = this.params.measureNames && this.params.measureNames[key] ? this.params.measureNames[key] : convertToTitleCase(key);
            const mappedColors = this.color_mappings ? this.color_mappings.filter(m => m.measure_alias === key).map(m => m.color) : [];

            if (mappedColors.length > 0) {
                // Use the SAME baseColor as the series so legend and bars match.
                const baseColor = measureBaseColors[index];
                const allColors = [...new Set([baseColor, ...mappedColors])];

                if (allColors.length > 1) {
                    const colorStops = [];
                    const step = 1 / allColors.length;
                    for (let i = 0; i < allColors.length; i++) {
                        colorStops.push({ offset: i * step, color: allColors[i] });
                        colorStops.push({ offset: (i + 1) * step, color: allColors[i] });
                    }
                    return {
                        name: label,
                        itemStyle: {
                            color: {
                                type: 'linear',
                                x: 0, y: 0, x2: 1, y2: 0,
                                colorStops: colorStops
                            }
                        }
                    };
                }
            }
            return { name: label };
        });

        var legends = {
            data: this.measures.map(key => this.params.measureNames && this.params.measureNames[key] ? this.params.measureNames[key] : convertToTitleCase(key))
        }

        let val = {
            legends,
            animation: true,
            animationDuration: 800,
            animationEasing: 'cubicOut',
            animationDurationUpdate: 500,
            animationEasingUpdate: 'cubicInOut',
            legend: {
                data: legendData,
                type: 'scroll',
                orient: 'horizontal',
                right: 20,
                top: 10,
                textStyle: {
                    color: this.params.isDarkMode ? '#cccccc' : '#333333',
                    fontSize: 12,
                    fontWeight: 500
                },
                itemGap: 15,
                icon: 'roundRect',
                z: 100
            },
            xAxis: this.dimension_axis === "x" ? xAxis : yAxis,
            yAxis: this.dimension_axis === "x" ? yAxis : xAxis,
            series,
            tooltip: {
                trigger: 'item',
                formatter: formatter
            },
            grid: {
                containLabel: true,
                left: '2%',
                right: '4%',
                top: 60,
                bottom: '10%'
            },
            dataZoom,
        }
        return this.additionalOption(val)
    }

    parseMeasures() {
        return this.measures.map(measure => convertToTitleCase(measure))
    }

    additionalOption(val) {
        /*
        Additional options for different chart can be added
        with functions named the type of the chart suffixed by 'Chart'
        */
        if (typeof this[`${this.type}Chart`] === 'function') {
            val.series.forEach(item => item.data = [])
            delete val.dataZoom
            return this[`${this.type}Chart`](val)
        }
        return val
    }

    pieAndDoughnutChart(val) {
        let axis = this.dimension_axis === "x" ? val.xAxis : val.yAxis
        const multiMeasure = this.measures.length > 1;

        const radiusScale = this.pieLegendBottom ? 0.8 : 1;
        const pct = (value) => `${Math.round(value * radiusScale)}%`;

        // For multi-measure pie, spread series across concentric rings so they don't overlap.
        // Single-measure keeps the original radius.
        const getRadius = (si) => {
            if (!multiMeasure) {
                return this.type === 'doughnut' ? [pct(40), pct(70)] : pct(50);
            }
            const total = this.measures.length;
            const outerMax = 70;
            const gap = 5;
            const ringWidth = Math.floor((outerMax - 10) / total) - gap;
            const outer = outerMax - si * (ringWidth + gap);
            const inner = outer - ringWidth;
            return [pct(inner), pct(outer)];
        };

        this.data && this.data.forEach((item, mi) => {
            axis.data.push(item[this.dimension])
            this.measures.forEach((key, i) => {
                const data = {
                    value: item[key],
                    name: axis.data[mi]
                }
                if (this.hasItemStyle) {
                    data.itemStyle = item["itemStyle"]
                }
                const customColor = this.getPointColor(key, item[key]);
                if (customColor) {
                    data.itemStyle = { ...(data.itemStyle || {}), color: customColor };
                }
                val.series[i].data.push(data)
                val.series[i].radius = getRadius(i)
                val.series[i].center = this.pieLegendBottom
                    ? ['50%', '42%']  // Sits above the legend band, not on top of it
                    : ['35%', '55%']
                val.series[i].type = "pie"
                if (this.hidePieSliceLabels) {
                    val.series[i].label = { show: false }
                    val.series[i].labelLine = { show: false }
                    val.series[i].emphasis = {
                        ...(val.series[i].emphasis || {}),
                        label: { show: false }
                    }
                } else {
                    val.series[i].label = {
                        formatter: (params) => {
                            if (typeof params.name === 'string' && params.name.startsWith('CY_IMAGE:')) {
                                const key = params.name.replace(/[^a-zA-Z0-9]/g, '_');
                                return `{${key}|}`;
                            }
                            return params.name;
                        },
                        rich: this.richLabels,
                        color: this.params?.isDarkMode ? '#ffffff' : '#333333',
                        textBorderWidth: 0
                    }
                }
            })
        })
        delete val.xAxis
        delete val.yAxis

        // In eCharts, a pie series-level itemStyle.color callback receives params.color = the
        // series base color (same for every slice), not the per-slice palette color.
        // For multi-measure: color by series index so each ring gets a distinct color.
        // For single-measure: color by dataIndex so each slice gets a distinct color.
        const palette = Array.isArray(this.themeColor) && this.themeColor.length > 0
            ? this.themeColor : null;
        val.series.forEach((s, si) => {
            const measureKey = this.measures[si];
            s.itemStyle = {
                color: (params) => {
                    const customColor = this.getPointColor(measureKey, params.value);
                    if (customColor) return customColor;
                    if (palette) {
                        const idx = multiMeasure ? si : params.dataIndex;
                        return palette[idx % palette.length];
                    }
                    return params.color;
                }
            };
        });

        // Pie legends are built from dimension values, not measure names, so they can be
        // long or raw image markers. Keep them short — the full value is in the tooltip.
        const legendLabel = (name) => {
            const raw = String(name ?? '');
            if (raw.startsWith('CY_IMAGE:')) {
                // All image markers share the same prefix, so truncating them would make
                // every entry read the same; the record id keeps them distinguishable.
                return `#${raw.split(':')[3] || '?'}`;
            }
            return raw.length > MAX_LABEL_LENGTH
                ? raw.substring(0, MAX_LABEL_LENGTH).trimEnd() + '...'
                : raw;
        };

        val.legend = this.pieLegendBottom ? {
            ...val.legend,
            orient: 'horizontal',
            left: 'center',
            bottom: 10,
            top: 'auto',
            right: 'auto',
            align: 'auto',
            formatter: legendLabel,
            tooltip: { show: true },
        } : {
            ...val.legend,
            orient: 'vertical',
            right: '5%',
            top: 'middle',
            left: 'auto',
            bottom: 16,
            align: 'left',
        };

        val.tooltip.formatter = (params) => {
            let content = `${params.name}<br/>${params.seriesName}: <b>${params.value}</b> (${params.percent}%)`;
            const alias = this.measures[params.seriesIndex];
            const mappings = this.getPointMappings(alias, params.value, params.name);

            let hasAddedLine = false;
            mappings.forEach(mapping => {
                const label = mapping.is_annotation ? "Note" : "Indicator";
                const infoText = mapping.indicator || mapping.notes;

                if (infoText) {
                    const topMargin = hasAddedLine ? 4 : 8;
                    const topPadding = hasAddedLine ? 0 : 5;
                    const topBorder = hasAddedLine ? 'none' : '1px solid rgba(255,255,255,0.2)';
                    content += `<div style="margin-top: ${topMargin}px; padding-top: ${topPadding}px; border-top: ${topBorder}; font-size: 11px; font-style: italic; opacity: 0.9;"><strong>${label}:</strong> ${infoText}</div>`;
                    hasAddedLine = true;
                }
            });
            return content;
        }
        return val
    }

    maxValue(flag) {
        var val = 0
        var result = this.data
        var key = this.measures[0]
        if (result.length) {
            for (let i = 0; i < result.length; i++) {
                val = val + result[i][key];
            }
            if (flag == false) {
                return val.toFixed(2)
            } else {
                const roundValue = Math.ceil(val / 20) * 20;
                const result = roundValue > 100 ? roundValue : 100;
                return result
            }
        }
    }

    pieChart(val) {
        return this.pieAndDoughnutChart(val)
    }

    doughnutChart(val) {
        return this.pieAndDoughnutChart(val)
    }

    scatterChart(val) {
        var dataZoom = this.getDefaultZoom()
        const axisData = this.data.map(item => item[this.dimension]);
        var series = this.measures.map(measure => {
            const data = this.data.map(item => {
                const val = item[measure];
                const customColor = this.getPointColor(measure, val);
                const res = {
                    value: [axisData.findIndex(axis => axis === item[this.dimension]), val]
                };
                if (customColor) {
                    res.itemStyle = { color: customColor };
                }
                return res;
            });
            return {
                data,
                type: "scatter",
                name: convertToTitleCase(measure),
                symbolSize: 20,
            }
        })
        if (this.dimension_axis === "x") {
            val.xAxis.data = axisData
        } else {
            val.yAxis.data = axisData
        }
        val.series = series
        val.dataZoom = dataZoom
        return val
    }

    radarChart(val) {
        val.legends.data = this.parseMeasures();
        // Every spoke shares ONE scale = the global max across all data points (with
        // 10% headroom). Deriving each axis's max from its own value (the old code)
        // normalised every point to the same fraction of its axis, so all points sat
        // at the same radius regardless of value — only 0 reached the centre.
        const allValues = this.data.flatMap(item =>
            this.measures.map(measure => Number(item[measure]) || 0)
        );
        const globalMax = allValues.length ? Math.max(...allValues) : 0;
        const max = globalMax > 0 ? globalMax * 1.1 : 1;
        const indicator = this.data.map(item => ({
            name: item[this.dimension],
            max,
        }))
        val.radar = {
            indicator,
            axisName: {
                formatter: (value) => {
                    if (typeof value === 'string' && value.startsWith('CY_IMAGE:')) {
                        const key = value.replace(/[^a-zA-Z0-9]/g, '_');
                        return `{${key}|}`;
                    }
                    return value;
                },
                rich: this.richLabels
            }
        }
        val.series = [{
            name: this.name,
            type: 'radar',
            data: this.measures.map(name => {
                return {
                    value: this.data.map(item => item[name]),
                    name: convertToTitleCase(name)
                }
            })
        }];
        delete val.xAxis
        delete val.yAxis
        return val
    }

    async mapChart(val) {
        if (!this.measures.length) {
            return val
        }
        return await worldMapChart(this, val)
    }

    gaugeChart(val) {
        val.tooltip.formatter = this.chartOptions.formatter
        val.series = [{
            name: this.name,
            type: 'gauge',
            min: 0,
            max: this.maxValue(true),
            splitNumber: 20,
            progress: {
                show: true
            },
            detail: {
                valueAnimation: true,
                formatter: '{value}'
            },
            data: this.measures.map(name => {
                return {
                    value: this.maxValue(false)
                }
            })
        }];
        delete val.xAxis
        delete val.yAxis
        return val
    }

    heatmapChart(val) {
        const length = this.data.length
        var AxisIndex = this.dimension_axis === "x" ? { xAxisIndex: 0 } : { yAxisIndex: 0 }
        var dataZoom = [{
            type: 'inside',
            id: this.dimension_axis === "x" ? "insideX" : "insideY",
            start: 0,
            end: length > 15 ? 30 : 100,
            zoomOnMouseWheel: false,
            moveOnMouseMove: true,
            moveOnMouseWheel: true,
            ...AxisIndex
        }]
        const sortKey = this.measures[this.measures.length - 1]
        const sortedData = [...this.data].sort((a, b) =>
            (b[sortKey] ?? 0) - (a[sortKey] ?? 0)
        )
        const baseColor = this.params.themeColor?.[0]
        const heatmapColors = baseColor ? (() => {
            const hex = baseColor.replace('#', '')
            const r = parseInt(hex.substring(0, 2), 16)
            const g = parseInt(hex.substring(2, 4), 16)
            const b = parseInt(hex.substring(4, 6), 16)
            const blend = (t, bg) => `rgb(${Math.round(bg + (r - bg) * t)},${Math.round(bg + (g - bg) * t)},${Math.round(bg + (b - bg) * t)})`
            const stops = [0.15, 0.35, 0.55, 0.75, 1]
            return this.params.isDarkMode
                ? stops.map(t => blend(t, 30))   // dark bg ~30 → full color
                : stops.map(t => blend(t, 255))  // white → full color
        })() : null
        const yAxis = [...new Set(sortedData.map(item => item[this.dimension]))].filter(v => v !== null && v !== undefined && v !== '')
        if (this.measures.length) {
            const validData = sortedData.filter(item => item[this.dimension] !== null && item[this.dimension] !== undefined && item[this.dimension] !== '')
            const xAxis = validData.map(item => item[this.measures[0]])
            const data = validData.map((item, index) => {
                return [yAxis.findIndex(res => res == item[this.dimension]), index, item[this.measures[this.measures.length - 1]]]
            })
                .filter(item => item[2] != null)
                .map(item => {
                    return this.dimension_axis === "x" ? [item[1], item[0], item[2]] : [item[0], item[1], item[2]]
                });
            var option = {
                dataZoom,
                tooltip: {
                    position: 'top',
                    formatter: this.chartOptions.formatter
                },
                title: val.title,
                darkMode: this.params.isDarkMode || false,
                xAxis: {
                    type: 'category',
                    axisLabel: {
                        color: this.params.isDarkMode ? '#cccccc' : '#333333'
                    },
                    // splitArea: {
                    //     show: true,
                    //     areaStyle: this.params.isDarkMode ? {
                    //         color: ['rgba(255,255,255,0.03)', 'rgba(255,255,255,0.07)']
                    //     } : {}
                    // }
                },

                yAxis: {
                    type: 'category',
                    axisLabel: {
                        color: this.params.isDarkMode ? '#cccccc' : '#333333'
                    },
                    splitArea: {
                        show: true,
                        areaStyle: {
                            color: this.params.isDarkMode
                                ? ['rgba(255,255,255,0.06)', 'rgba(255,255,255,0.14)']
                                : ['rgba(0,0,0,0.02)', 'rgba(0,0,0,0.06)']
                        }
                    }
                },
                visualMap: {
                    min: 0,
                    max: Math.max(...sortedData.map(item => item[sortKey])),
                    calculable: true,
                    orient: 'vertical',
                    right: 7,
                    bottom: 'center',
                    textStyle: {
                        color: this.params.isDarkMode ? '#cccccc' : '#333333'
                    },
                    ...(heatmapColors ? { inRange: { color: heatmapColors } } : {})
                },
                grid: { ...val.grid, top: '5%', right: '15%' },
                series: [
                    {
                        name: convertToTitleCase(this.measures[this.measures.length - 1]),
                        type: 'heatmap',
                        data: data,

                        label: {
                            show: true,
                            rotate: this.dimension_axis === 'x' ? 90 : 0,
                        },
                        emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowColor: 'rgba(0, 0, 0, 0.5)'
                            }
                        }
                    }
                ],
                graphic: val.graphic
            };
            if (this.dimension_axis === "x") {
                option.xAxis.data = xAxis
                option.yAxis.data = yAxis
                option.yAxis.axisLabel = { ...option.yAxis.axisLabel, ...val.xAxis?.axisLabel }
            } else {
                option.xAxis.data = yAxis
                option.yAxis.data = xAxis
                option.xAxis.axisLabel = { ...option.xAxis.axisLabel, ...val.yAxis?.axisLabel }
            }
        } else {
            option = val
        }
        return option
    }

    regressionLineScatterChart(val) {
        if (typeof ecStat === 'undefined') {
            return loadingChart({ text: 'ecStat library not loaded', loop: false, title: this.name });
        }
        echarts.registerTransform(ecStat.transform.regression);
        const axisData = [...new Set(this.data.map(item => item[this.dimension]))]
        var dataZoom = this.getDefaultZoom()
        var data = this.measures.map(measure => {
            const source = this.data.map(item => {
                return [axisData.findIndex(data => data == item[this.dimension]), item[measure]]
            })
            return { source }
        })
        if (!data.length) {
            data = [{ source: [[0, 0]] }]
        }
        var option = {
            dataset: [
                ...data,
                {
                    transform: {
                        type: 'ecStat:regression',
                        config: {
                            method: 'exponential'
                        }
                    }
                }
            ],
            title: val.title,
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross'
                },
                formatter: this.chartOptions.formatter
            },
            xAxis: {
                axisLabel: { color: this.params.isDarkMode ? '#cccccc' : '#333333' },
                axisLine: { lineStyle: { color: this._axisLineColor } },
                splitLine: {
                    lineStyle: {
                        type: 'dashed',
                        color: this._splitLineColor
                    }
                }
            },
            yAxis: {
                axisLabel: { color: this.params.isDarkMode ? '#cccccc' : '#333333' },
                axisLine: { lineStyle: { color: this._axisLineColor } },
                splitLine: {
                    lineStyle: {
                        type: 'dashed',
                        color: this._splitLineColor
                    }
                }
            },
            series: [{
                name: 'scatter',
                type: 'scatter',
                datasetIndex: 0
            },
            {
                name: 'line',
                type: 'line',
                smooth: true,
                datasetIndex: 1,
                symbolSize: 0.1,
                symbol: 'circle',
                label: {
                    show: true,
                    fontSize: 16
                },
                labelLayout: {
                    dx: -20
                },
                encode: {
                    label: 2,
                    tooltip: 1
                }
            }
            ],
            dataZoom,
            graphic: val.graphic,
        };
        if (this.dimension_axis === "x") {
            option.xAxis.data = axisData
            option.xAxis.axisLabel = val.xAxis?.axisLabel
        } else {
            option.yAxis.data = axisData
            option.yAxis.axisLabel = val.yAxis?.axisLabel
        }
        return option
    }

    funnelChart(val) {
        let data = this.dimension_axis === "x" ? val.xAxis.data : val.yAxis.data;
        data = data.filter(item => item).map(item => typeof item === 'number' ? JSON.stringify(item) : item)
        const baseFormatter = this.dimension_axis === "x" ? val.xAxis?.axisLabel?.formatter : val.yAxis?.axisLabel?.formatter;

        // Calculate funnel-specific image size to prevent vertical overlapping inside the funnel bounds
        const totalFunnelItems = this.data ? this.data.length : 1;
        // Strictly bound height to scale natively under the slice bounds, safely assuming a 220px inner vertical area
        // with appropriate buffering for the 2px gap per slice. No aggressive minimum bounds.
        const funnelImgSize = Math.max(2, Math.min(32, Math.floor(220 / totalFunnelItems) - 3));

        const funnelRichLabels = {};
        for (const [key, value] of Object.entries(this.richLabels || {})) {
            funnelRichLabels[key] = {
                ...value,
                height: funnelImgSize,
                width: funnelImgSize
            };
        }

        const seriesData = {
            name: convertToTitleCase(this.measures[0]),
            type: 'funnel',
            left: '10%',
            top: 60,
            bottom: 60,
            width: '80%',
            min: 0,
            max: 100,
            minSize: '0%',
            maxSize: '100%',
            sort: 'descending',
            gap: 2,
            label: {
                show: true,
                position: 'inside',
                formatter: (params) => {
                    return baseFormatter && typeof baseFormatter === 'function' ? baseFormatter(params.name) : params.name;
                },
                rich: funnelRichLabels
            },
            labelLine: {
                length: 10,
                lineStyle: {
                    width: 1,
                    type: 'solid'
                }
            },
            itemStyle: {
                borderColor: '#fff',
                borderWidth: 1
            },
            emphasis: {
                label: {
                    fontSize: 20
                }
            },
        }
        const series = this.measures.map(measure => {
            return {
                data: this.data.map(item => {
                    return {
                        name: item[this.dimension],
                        value: item[measure]
                    }
                }),
                ...seriesData
            }
        })
        let titleTextColor = '#333333';
        let legendIconColor = '#e0e0e0';
        if (this.params?.themeColor && this.params.themeColor.length > 0) {
            titleTextColor = '#ffffff';
            legendIconColor = '#ffffff';
        }

        val.legend = {
            top: 10,
            data,
            type: 'scroll',
            orient: 'horizontal',
            left: 'center',
            formatter: (name) => {
                const label = baseFormatter && typeof baseFormatter === 'function' ? baseFormatter(name) : name;
                return typeof label === 'string' ? label.replace(/\n/g, ' ') : label;
            },
            textStyle: {
                rich: this.richLabels,
                color: this.params?.isDarkMode ? '#ffffff' : '#333333',
                fontSize: 12,
                fontWeight: 500
            },
            icon: 'roundRect'
        }
        val.series = series
        delete val.xAxis
        delete val.yAxis
        return val
    }

    pictorialBarChart(val) {
        var option = val
        var dataZoom = this.getDefaultZoom()
        if (this.measures.length > 1) {
            var axisCategory = this.data.map(item => item[this.dimension])
            var barSeriesData = this.data.map(item => item[this.measures[0]])
            var lineSeriesData = this.data.map(item => item[this.measures[1]])
            option = {
                dataZoom,
                title: val.title,
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'shadow'
                    }
                },
                graphic: val.graphic,
                legend: {
                    ...val.legend,
                    data: [convertToTitleCase(this.measures[0]), convertToTitleCase(this.measures[1])]
                },
                series: [{
                    name: convertToTitleCase(this.measures[1]),
                    type: 'line',
                    smooth: true,
                    showAllSymbol: true,
                    symbol: 'emptyCircle',
                    symbolSize: 15,
                    data: lineSeriesData
                },
                {
                    name: convertToTitleCase(this.measures[0]),
                    type: 'bar',
                    barWidth: 10,
                    itemStyle: {
                        borderRadius: 5,
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
                            offset: 0,
                            color: this.params.themeColor?.length > 3 ? this.params.themeColor[1] : '#14c8d4'
                        },
                        {
                            offset: 1,
                            color: this.params.themeColor?.length > 3 ? this.params.themeColor[2] : '#43eec6'
                        }
                        ])
                    },
                    data: barSeriesData
                },
                {
                    name: convertToTitleCase(this.measures[1]),
                    type: 'bar',
                    barGap: '-100%',
                    barWidth: 10,
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
                            offset: 0,
                            color: 'rgba(20,200,212,0.5)'
                        },
                        {
                            offset: 0.2,
                            color: 'rgba(20,200,212,0.2)'
                        },
                        {
                            offset: 1,
                            color: 'rgba(20,200,212,0)'
                        }
                        ])
                    },
                    z: -12,
                    data: lineSeriesData
                },
                {
                    name: convertToTitleCase(this.measures[1]),
                    type: 'pictorialBar',
                    symbol: 'rect',
                    itemStyle: {
                        color: '#0f375f'
                    },
                    symbolRepeat: true,
                    symbolSize: [12, 4],
                    symbolMargin: 1,
                    z: -10,
                    data: lineSeriesData
                }
                ]
            };
            var xAxis = {
                data: axisCategory,
                axisLabel: { color: this.params.isDarkMode ? '#cccccc' : '#333333', ...val.xAxis?.axisLabel },
                axisLine: {
                    lineStyle: {
                        color: '#ccc'
                    }
                }
            }
            var yAxis = {
                axisLabel: { color: this.params.isDarkMode ? '#cccccc' : '#333333', ...val.yAxis?.axisLabel },
                splitLine: {
                    show: false
                },
                axisLine: {
                    lineStyle: {
                        color: '#ccc'
                    }
                }
            }
            if (this.dimension_axis === "x") {
                option.xAxis = xAxis;
                option.yAxis = yAxis;
            } else {
                option.yAxis = xAxis;
                option.xAxis = yAxis;
            }
        }
        return option;
    }

    regenGraphOptions(params) {
        this.params = { ...this.params, ...params };
        return this.makeGraphOptions()
    }
}