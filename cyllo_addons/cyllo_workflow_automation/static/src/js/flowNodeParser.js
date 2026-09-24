/** @odoo-module */

export class FlowNodeParser {
    constructor(values) {
        this.values = values
        this.drawFlow = values.flow_data.drawflow
    }
    parseData(key){
        const {data} = this.drawFlow.Home
        return Object.values(data).filter(item => item.data.type === key)
    }
    parsePrimaryModel() {
        const primaryModel = this.parseData('model')
        return {}
    }
    parseConnectedModels() {
        const connectedModels = this.parseData('sec_model')
        return {}
    }

    getData() {
        const primaryModel = this.parsePrimaryModel()
        const connectedModels = this.parseConnectedModels()
    }
}

