/** @odoo-module **/

import {Component, useRef, onWillStart, onMounted, onWillUnmount, xml } from "@odoo/owl";

export class LottieAnimation extends Component {
    setup() {
        this.animationContainer = useRef("animationContainer");
        this.animation = null;

        onWillStart(async () => {
            const response = await fetch(this.props.src);
            this.animationData = await response.json();
        });

        onMounted(() => {
            this.loadAnimation();
        });

        onWillUnmount(() => {
            if (this.animation) {
                this.animation.destroy();
            }
        });
    }

    loadAnimation() {
        if (this.animation) {
            this.animation.destroy();
        }

        this.animation = lottie.loadAnimation({
            container: this.animationContainer.el,
            renderer: 'svg',
            loop: this.props.loop ?? false,
            autoplay: this.props.autoplay ?? true,
            animationData: this.animationData,
        });
    }
}

LottieAnimation.template = xml`
    <div class="lottie-container" t-ref="animationContainer" t-att-style="props.style"/>
`;

LottieAnimation.props = {
    src: String,
    loop: { type: Boolean, optional: true },
    autoplay: { type: Boolean, optional: true },
    style: { type: String, optional: true },
};