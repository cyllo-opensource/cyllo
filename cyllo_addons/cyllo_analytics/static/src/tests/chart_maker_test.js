/** @odoo-module **/
import { convertToTitleCase, ChartMaker } from "@cyllo_analytics/js/chart_maker"
import { CylloSheet } from "@cyllo_analytics/js/cyllo_sheet";

QUnit.test("should return the chart options based on the provided data, dimension, measures, name, type, and dimension_axis", (assert) => {
    const data = [{ dimension: 'A', measure1: 10, measure2: 20 }];
    const chartMaker = new ChartMaker(data, 'dimension', ['measure1', 'measure2'], 'chart', 'bar', 'x');
    const options = chartMaker.makeGraphOptions();
    assert.deepEqual({ type: options.xAxis.type, data: options.xAxis.data }, { type: 'category', data: ['A'] });
    assert.strictEqual(options.yAxis.type, 'value');
    assert.deepEqual(
        options.series.map((series) => ({ name: series.name, type: series.type, data: series.data })),
        [{ name: 'Measure1', type: 'bar', data: [10] }, { name: 'Measure2', type: 'bar', data: [20] }]);
    assert.deepEqual(options.legend.data.map((item) => item.name), ['Measure1', 'Measure2']);
    assert.strictEqual(options.tooltip.trigger, 'item');
});

QUnit.test('should convert a string with all lowercase letters to title case', (assert) => {
    assert.equal(convertToTitleCase("hello"), "Hello");
    assert.equal(convertToTitleCase("sale_order_total"), "Sale Order Total");
});

QUnit.test("query rebuild only groups when group by is explicit", (assert) => {
    const columns = [
        {
            type: "dimension",
            column: "sale_order.partner_id",
            query: "sale_order.partner_id AS sale_order_partner_id",
        },
        {
            type: "measure",
            column: "sale_order.amount_total",
            query: "sale_order.amount_total AS sale_order_amount_total",
        },
    ];

    const noGroupBy = CylloSheet.prototype._getGroupByTerms.call(
        {
            query_data: { groupBy: [] },
            state: { preserveExplicitGrouping: true },
        },
        columns
    );
    assert.deepEqual(noGroupBy.totalGroupBy, []);
    assert.strictEqual(noGroupBy.isGrouping, false);

    const explicitGroupBy = CylloSheet.prototype._getGroupByTerms.call(
        {
            query_data: {
                groupBy: [{ column: "sale_order.partner_id" }],
            },
            state: { preserveExplicitGrouping: true },
        },
        columns
    );
    assert.deepEqual(explicitGroupBy.totalGroupBy, ["sale_order.partner_id"]);
    assert.strictEqual(explicitGroupBy.isGrouping, true);
});

QUnit.test("drag-and-drop query keeps inferred grouping for aggregated measures", (assert) => {
    const columns = [
        {
            type: "dimension",
            column: "utm_medium.name",
            query: "utm_medium.name AS utm_medium_name",
        },
        {
            type: "measure",
            column: "sale_order.amount_total",
            query: "sale_order.amount_total AS sale_order_amount_total",
            aggregate_func: "SUM",
        },
    ];

    const result = CylloSheet.prototype._getGroupByTerms.call(
        {
            query_data: { groupBy: [] },
            state: { preserveExplicitGrouping: false },
        },
        columns
    );

    assert.deepEqual(result.totalGroupBy, ["utm_medium.name"]);
    assert.strictEqual(result.isGrouping, true);
});

QUnit.test("scatter points follow the axis that holds the dimension", (assert) => {
    const data = [
        { stage: "New", tickets: 27 },
        { stage: "In Progress", tickets: 46 },
    ];
    for (const [dimensionAxis, encode] of [["x", { x: 0, y: 1 }], ["y", { x: 1, y: 0 }]]) {
        const chartMaker = new ChartMaker(data, "stage", ["tickets"], "helpdesk", "scatter", dimensionAxis);
        const options = chartMaker.makeGraphOptions();
        const series = options.series[0];
        assert.deepEqual(series.encode, encode, `encode for dimension on ${dimensionAxis}`);
        assert.deepEqual(series.data.map((point) => [point.name, point.value]), [["New", [0, 27]], ["In Progress", [1, 46]]]);
        const categoryAxis = dimensionAxis === "x" ? options.xAxis : options.yAxis;
        assert.deepEqual(categoryAxis.data, ["New", "In Progress"]);
        const tooltip = options.tooltip.formatter({ seriesName: "Tickets", seriesIndex: 0, name: "In Progress", value: [1, 46] });
        assert.ok(tooltip.includes("In Progress : 46"), `tooltip shows the stage and count for dimension on ${dimensionAxis}`);
    }
});

QUnit.test("legend shows color mapping colors only for charts that draw them", (assert) => {
    const data = [{ stage: "New", tickets: 27 }, { stage: "In Progress", tickets: 46 }];
    const params = { color_mappings: [{ measure_alias: "tickets", min_value: 40, max_value: "all above", color: "#9b30d9" }] };
    const legendItem = (type) => new ChartMaker(data, "stage", ["tickets"], "helpdesk", type, "x", params)
        .makeGraphOptions().legend.data[0];
    assert.ok(legendItem("bar").itemStyle, "bar legend includes the mapped color");
    assert.notOk(legendItem("radar").itemStyle, "radar legend keeps the plain measure color");
});
