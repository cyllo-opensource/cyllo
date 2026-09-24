/** @odoo-module */
import {Component, useState, useRef} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

let isNavigatingGlobally = false;

export class BackButtonComponent extends Component {
    static template = 'BackButtonComponent';

    setup() {
        this.root = useRef('root');
        this.ui = useService("ui");
    }

    handleOnClickBack() {
        if (isNavigatingGlobally) {
            return;
        }
        isNavigatingGlobally = true;

        if (this.root.el) {
            this.root.el.style.pointerEvents = 'none';
        }

        this.ui.block();

        window.history?.back();

        setTimeout(() => {
            this.ui.unblock();
            isNavigatingGlobally = false;
            if (this.root.el) {
                this.root.el.style.pointerEvents = '';
            }
        }, 1500);
    }

}