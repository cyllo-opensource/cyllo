/** @odoo-module **/
import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { LottieAnimation } from "./lottie/lottie"

export class ConfirmationPopup extends Component {
    setup() {
        this.state = useState({
            isOpen: false,
            isClosing: false
        });
        this.popupRef = useRef("popup");

        onMounted(() => {
            this.open();
            document.addEventListener('keydown', this.handleKeyDown);
        });

        onWillUnmount(() => {
            document.removeEventListener('keydown', this.handleKeyDown);
        });
    }

    handleKeyDown = (event) => {
        if (this.state.isOpen) {
            if (event.key === 'Escape') {
                this.onCancel();
            } else if (event.key === 'Enter') {
                this.onConfirm();
            }
        }
    }

    open() {
        this.state.isOpen = true;
        this.state.isClosing = false;
    }

    close() {
        this.state.isClosing = true;
        setTimeout(() => {
            this.state.isOpen = false;
            this.state.isClosing = false;
            this.props.close();
        }, 500);
    }

    onConfirm() {
        this.props.onConfirm();
        this.close();
    }

    onCancel() {
        this.props.onCancel();
        this.close();
    }
}

ConfirmationPopup.template = "ConfirmationPopup";
ConfirmationPopup.components = { LottieAnimation };

ConfirmationPopup.props = {
    title: {type: String},
    message: {type: String},
    confirmText: {type: String, optional: true},
    cancelText: {type: String, optional: true},
    onConfirm: {type: Function, optional: true},
    onCancel: {type: Function, optional: true},
    close: {type: Function},
    icon: {type: String, optional: true},
    image: {type: String, optional: true},
    showCancel: {type: Boolean, optional: true},
    showConfirm: {type: Boolean, optional: true},
    lottie: {type: Boolean, optional: true},
    lottiePath: {type: String, optional: true},
};

ConfirmationPopup.defaultProps = {
    showCancel:  true,
    showConfirm: true,
    lottie: false,
    onCancel: () => {},
    onConfirm: () => {},
}