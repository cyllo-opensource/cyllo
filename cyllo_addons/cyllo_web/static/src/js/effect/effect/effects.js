/** @odoo-module **/

import {Component, useState, useEffect} from "@odoo/owl";
import {browser} from "@web/core/browser/browser";

export class NotificationPanel extends Component {
    setup() {
        this.state = useState({
            isAnimating: true,
            isShaking: true,
            progress: 100,
            isHovered: false,
        });

        this.closeTimeoutTime = this.props.time;

        useEffect(() => {
            const shakeTimeout = browser.setTimeout(() => {
                this.state.isShaking = false;
            }, 500);

            // Progress bar update
            const progressInterval = browser.setInterval(() => {
                if (!this.state.isHovered) {
                    this.state.progress -= 1;
                    this.closeTimeoutTime -= this.props.time / 100;
                    if (this.state.progress <= 0) {
                        browser.clearInterval(progressInterval);
                        this.state.isAnimating = false;
                    }
                }
            }, this.props.time / 100);

            // Close the panel after a delay
            this.closeTimeout = browser.setTimeout(() => {
                this.props.close();
            }, this.closeTimeoutTime);

            return () => {
                browser.clearTimeout(shakeTimeout);
                browser.clearInterval(progressInterval);
                browser.clearTimeout(this.closeTimeout);
            };
        }, () => []);

        this.onMouseEnter = this.onMouseEnter.bind(this);
        this.onMouseLeave = this.onMouseLeave.bind(this);
    }

    getIconClass() {
        switch (this.props.type) {
            case 'success':
                return 'ri-checkbox-circle-line';
            case 'warning':
                return 'ri-error-warning-line';
            case 'error':
            default:
                return 'ri-alarm-warning-line';
        }
    }

    // ... (keep onMouseEnter and onMouseLeave methods)

    onMouseEnter() {
        this.state.isHovered = true;
        browser.clearTimeout(this.closeTimeout);
    }

    onMouseLeave() {
        this.state.isHovered = false;
        this.closeTimeout = browser.setTimeout(() => {
            this.props.close();
        }, this.closeTimeoutTime);
    }
}

NotificationPanel.template = "cyllo_web.NotificationPanel";
NotificationPanel.props = {
    close: Function,
    title: String,
    message: String,
    description: {type: String, optional: true},
    type: {type: String, validate: (type) => ['success', 'warning', 'error'].includes(type)},
    time: Number,
    animation: {type: Boolean, optional: true},
};

