/** @odoo-module */

import { EventBus } from "@odoo/owl";

export default class Context extends EventBus {
    constructor(content) {
        super();
        this.content = content;
    }

    get context() {
        return this.content
    }

    setContext(data) {
        this.content = {...this.content, ...data}
        this.trigger("UPDATE-ME")
    }

    deleteNode(nodeId) {
        const indexToRemove = this.content.nodes.findIndex(item => item.nodeId === nodeId);
        if (indexToRemove !== -1) {
            this.content.nodes.splice(indexToRemove, 1);
            this.trigger("UPDATE-ME")
        }
    }
}