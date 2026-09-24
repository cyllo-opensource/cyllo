/** @odoo-module **/
import { convertToTitleCase, ChartMaker } from "@cyllo_analytics/js/chart_maker"
import { CylloSheet } from "@cyllo_analytics/js/cyllo_sheet";

QUnit.test("should return the chart options based on the provided data, dimension, measures, name, type, and dimension_axis", async function (assert) {
const data = [{ dimension: 'A', measure1: 10, measure2: 20 }];
const dimension = 'dimension';
const measures = ['measure1', 'measure2'];
const name = 'chart';
const type = 'bar';
const dimension_axis = 'x';
const chartMaker = new ChartMaker(data, dimension, measures, name, type, dimension_axis);
const expectedOptions = {
   title: {
       text: 'Chart'
   },
   legends: {
      data: ['chart']
   },
    legend: {
        type: 'scroll',
        orient: 'vertical',
        right: 10,
        top: 20,
        bottom: 20
    },
    xAxis: {
        data: ['A'],
        type: 'category'
    },
    yAxis: {
        type: 'value'
    },
    series: [
    {
        name: 'Measure1',
        type: 'bar',
        data: [10],
        emphasis: {
        label: {
           show: true,
           fontSize: 10
           }
        }
    },
    {
        name: 'Measure2',
        type: 'bar',
        data: [20],
        emphasis: {
            label: {
            show: true,
            fontSize: 10
            }
        }
    }
    ],
    tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b} : {c}'
    },
    grid: {
        left: '12%',
        right: '15%',
        top: '15%',
        bottom: '20%'
    },
    dataZoom: [
    {
        YAxisIndex: 0,
        end: 100,
        id: "insideY",
        moveOnMouseMove: true,
        moveOnMouseWheel: true,
        start: 30,
        type: "inside",
        zoomOnMouseWheel: false
        }
    ],
    };
    const options = chartMaker.makeGraphOptions();
    assert.deepEqual(options, expectedOptions);
});

QUnit.test('should convert a string with all lowercase letters to title case', (assert) => {
    const inputString = "hello";
    const expectedOutput = "hello";
    const actualOutput = convertToTitleCase(inputString);
    assert.equal(actualOutput, expectedOutput);
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
