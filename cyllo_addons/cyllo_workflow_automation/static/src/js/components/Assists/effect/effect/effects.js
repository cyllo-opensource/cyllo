/** @odoo-module **/

import { Component, useState, useEffect, } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { LottieAnimation } from "@cyllo_web/js/popups/lottie/lottie"

export class SaveConfetti extends Component {
    /**
     * SaveConfetti component displays an animated confetti effect
     * for a celebratory message. It manages the animation state
     * and generates random confetti pieces with different colors.
     */
    setup() {
        this.state = useState({
            isAnimating: true,
            confettiCount: 150 // Number of confetti pieces
        });
        useEffect(() => {
            const animationTimeout = browser.setTimeout(() => {
                this.state.isAnimating = false;
            }, 1000);
            const closeTimeout = browser.setTimeout(() => {
                this.props.close();
            }, 2000);
            return () => {
                browser.clearTimeout(animationTimeout);
                browser.clearTimeout(closeTimeout);
            };
        }, () => []);
    }

    generateConfetti() {
        return Array.from({ length: this.state.confettiCount }, (_, i) => ({
            id: i,
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 3}s`,
            backgroundColor: this.getRandomColor()
        }));
    }

    getRandomColor() {
        const colors = ['#ff595e', '#ffca3a', '#8ac926', '#1982c4', '#6a4c93'];
        return colors[Math.floor(Math.random() * colors.length)];
    }
}

SaveConfetti.template = "SaveConfetti";
SaveConfetti.components = { LottieAnimation };
SaveConfetti.props = {
    close: Function,
    message: String,
    isLocked: { type: Boolean, optional: true },
    icon: {type: String, optional: true}
};


export class SaveFireworks extends Component {
    setup() {
        this.state = useState({
            isAnimating: true,
            fireworks: [],
            stars: [],
        });
        useEffect(() => {
            this.generateFireworks();
            this.generateStars();
            const animationTimeout = browser.setTimeout(() => {
                this.state.isAnimating = false;
            }, 4000);
            const closeTimeout = browser.setTimeout(() => {
                this.props.close();
            }, 5000);
            return () => {
                browser.clearTimeout(animationTimeout);
                browser.clearTimeout(closeTimeout);
            };
        }, () => []);
    }

    generateFireworks() {
        const fireworks = [];
        for (let i = 0; i < 5; i++) {
            fireworks.push({
                id: i,
                left: `${10 + Math.random() * 80}%`,
                top: `${40 + Math.random() * 40}%`,
                size: 10 + Math.random() * 20,
                delay: Math.random() * 2,
            });
        }
        this.state.fireworks = fireworks;
    }

    generateStars() {
        const stars = [];
        for (let i = 0; i < 50; i++) {
            stars.push({
                id: i,
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                size: 1 + Math.random() * 3,
                delay: Math.random() * 2,
            });
        }
        this.state.stars = stars;
    }

    getRandomColor() {
        return `hsl(${Math.random() * 360}, 100%, 50%)`;
    }
}

SaveFireworks.template = "SaveFireworks";
SaveFireworks.props = {
    close: Function,
    message: String,
};

export class BuildMessage extends Component {
    /**
     * SaveConfetti component displays an animated confetti effect
     * for a celebratory message. It manages the animation state
     * and generates random confetti pieces with different colors.
     */
    setup() {
        this.state = useState({
            isAnimating: true,
            confettiCount: 150 // Number of confetti pieces
        });
    }

    generateConfetti() {
        return Array.from({ length: this.state.confettiCount }, (_, i) => ({
            id: i,
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 3}s`,
            backgroundColor: this.getRandomColor()
        }));
    }
    closeBuildMessage(){
        this.state.isAnimating = false;
    }

    getRandomColor() {
        const colors = ['#ff595e', '#ffca3a', '#8ac926', '#1982c4', '#6a4c93'];
        return colors[Math.floor(Math.random() * colors.length)];
    }
}

BuildMessage.template = "BuildMessage";
BuildMessage.components = { LottieAnimation };
BuildMessage.props = {
    close: Function,
    message: String,
    icon: {type: String, optional: true}
};
