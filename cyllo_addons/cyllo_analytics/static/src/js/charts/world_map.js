/** @odoo-module **/

/**
 * Floor the number to the nearest value of to.
 *
 * @param {number} number - The number to floor.
 * @param {number} to - The value to which the number will be floored.
 * @returns {number} The floored number.
 */
function floorTo(number, to){
    return Math.floor(number / to) * to
}

/**
 * Ceil the number to the nearest value of to.
 *
 * @param {number} number - The number to ceil.
 * @param {number} to - The value to which the number will be ceiled.
 * @returns {number} The ceiled number.
 */
function ceilTo(number, to){
    return Math.ceil(number / to) * to
}

/**
 * This function creates a world map chart using the ECharts library.
 *
 * @param {Object} env - An object containing variables such as the dimension, measures, and data.
 * @param {Object} values - An object containing values for the chart such as the tooltip, visualMap, and series.
 * @returns {Object} The values object with the chart settings.
 */
export async function worldMapChart(env, values) {
    const valueTotalList = env.data.map(item => item[env.measures[0]]).sort()
    const res = await $.when(
        $.get('cyllo_analytics/static/src/assets/world.json'),
        await $.getScript('cyllo_analytics/static/src/lib/map/d3_array.min.js'),
        $.getScript('cyllo_analytics/static/src/lib/map/d3_geo.min.js')
    );
    const worldJson = res[0];
    const projection = d3.geoEquirectangular();
    values.tooltip = {
        trigger: "item",
        showDelay: 0,
        transitionDuration: 0.2
    }
    let max = valueTotalList.length ? ceilTo(valueTotalList[valueTotalList.length-1], 1000) : 15000
    let min = valueTotalList.length ? floorTo(valueTotalList[0], 1000) : 1000
    let color = ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffbf',
                '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026']
    if (env.params.themeColor) {
        color = env.params.themeColor
    }
    values.visualMap = {
        right: 10,
        min,
        max,
        inRange: {
            color
        },
        text: ['High', 'Low'],
        calculable: true
    }
    values.series = [{
        ...values.series[0],
        map: 'World',
        projection: {
            project: function(point) {
                return projection(point);
            },
            unproject: function(point) {
                return projection.invert(point);
            }
        },
        data: env.data.map(item => {
            return {
                name: item[env.dimension],
                value: item[env.measures[0]]
            }
        }).filter(item => item.name)
    }]
    delete values.xAxis
    delete values.yAxis
    delete values.legend
    echarts.registerMap('World', worldJson);
    return values
}