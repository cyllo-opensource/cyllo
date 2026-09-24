/* @odoo-module */
/**
 * @class TableMaker
 * @classdesc The TableMaker class is used to create a table with data, dimensions, measures, and other properties.
 */
import { loadingChart } from "../charts/loadingChart"
import { _t } from "@web/core/l10n/translation";

export class TableMaker {
  /**
   * @constructor
   * @param {Array} data - The input data for the table.
   * @param {string} dimension - The name of the dimension field.
   * @param {Array} measures - An array of measure field names.
   * @param {string} name - The name of the table.
   * @param {number} min - The minimum count value for the table (default: 10).
   */
    constructor(data, dimension, measures, name, min) {
        this.data = data
        this.dimension = (typeof dimension === "object") ? dimension[0] : dimension
        this.measures = measures
        this.name = name
        this.min = min || 10
    }
  /**
   * Generates and returns an object representing the table data based on the stored properties.
   * @method getTableData
   * @returns {Object} - The table data object.
   */
    getTableData(){
        if (!this.data.length) {
            var loadingData = loadingChart({
                text: _t('No Data Found'),
                loop: false,
                title: this.name
            })
            loadingData.data = []
            return loadingData
        }
        var dimension_data = this.data?.map((item) => item[this.dimension])
        this.measures.forEach(item => {
            this.data.forEach(subData => {
                subData[item] = Number(subData[item]).toFixed(2)
            })
        })
        var tableData = {
            name: this.name,
            heading: [this.dimension, ...this.measures],
            count: dimension_data?.length || 0,
            min: 0,
            data: this.data
        }
        tableData.min = tableData.count > this.min ? this.min : tableData.count
        return tableData
    }
}
