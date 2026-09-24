/** @odoo-module **/

import { Component, useState, useEffect, } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { LottieAnimation } from "@cyllo_web/js/popups/lottie/lottie"

export class SaveLoading extends Component {
    setup() {
        this.state = useState({
            isAnimating : true
        })
        super.setup()
    }
    static props = {
        image: { type: String, optional: true},
        icon: { type: String, optional: true},
        message: { type: String, optional: true},
    }
    static template= "SaveLoading"
}
