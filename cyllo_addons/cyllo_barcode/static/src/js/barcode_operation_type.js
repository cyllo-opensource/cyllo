/** @odoo-module */
// Import necessary modules and components
import { registry } from "@web/core/registry";
import { Component,useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
const actionRegistry = registry.category("actions");
export class CylloBarcodeStockPicking extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            stockPicking: []
        })
        this.companyService = useService("company");
        this.actionService = useService("action")
        this.getStockPicking()
    }
    /**
     * Function for opening the view for the corresponding transfer
     */
    _onClickOpenTransfer(id, name) {
        localStorage.setItem('cyllo-barcode-inventory', id)
        localStorage.setItem('cyllo-barcode-inventory-type', 'stock-picking')
        this.actionService.doAction({
            type: "ir.actions.client",
            name: name,
            tag: "cyllo_location_client_action",
            target: "current",
            context: {
                'menu': 'cyllo_stock_picking_client_action'
            }
        })
    }
    /**
     * Function for opening the wizard for the corresponding transfer
     */
    OpenStockPicking(ev, id, name) {
        ev.stopPropagation()
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: 'stock.picking',
            res_id: id,
            target: "current",
            views: [
                [false, "form"]
            ],
        })
    }
    /**
     * Function for all transfer in the corresponding operation types
     */
    async getStockPicking() {
        this.id = localStorage.getItem("cyllo-barcode-operation-type")
        this.name = localStorage.getItem("cyllo-barcode-operation-name")
        this.state.stockPicking = await this.orm.searchRead(
            "stock.picking", [
                ["picking_type_id", "=", Number(this.id)],
                ["state", "=", 'assigned']
            ], ['name', 'state', 'partner_id', 'scheduled_date'])
    }
}

CylloBarcodeStockPicking.template = "cyllo_barcode.BarcodeStockPicking";
actionRegistry.add('cyllo_stock_picking_client_action', CylloBarcodeStockPicking);