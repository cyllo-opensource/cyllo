/** @odoo-module */
import {Component, useState, useRef} from "@odoo/owl";

export class NameComponent extends Component {
    static template = 'NameComponent'

    setup() {
        this.root = useRef('root')
        this.state = useState({
            name: this.name,
            showInput: false,
        })
        this.externalClickHandler = (ev) => this.handleExternalClick(ev)
    }

    handleOnClickSpan() {
        setTimeout(() => this.root.el.querySelector(".form-control").focus(), 100)
        this.state.showInput = true
        this.addEventListeners()
    }

    addEventListeners() {
        document.addEventListener("click", this.externalClickHandler, true);
    }

    removeEventListeners() {
        document.removeEventListener("click", this.externalClickHandler, true);
    }

    handleExternalClick(ev) {
        if (!this.root.el.contains(ev.target)) {
            this.state.showInput = false;
            this.removeEventListeners();
            if (this.name !== this.state.name) {
                this.env.updateName?.(this.state.name)
            }
        }
    }

    get name() {
        return this.env.model.config.name.replace(/\.xlsx$/, '');
    }
}

