/** @odoo-module **/
import { Component, useRef, onMounted, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";


export class BoardFormDialog extends Component {
    static template = "cyllo_social_media_marketing.BoardFormDialog";
    static components = { Dialog };
    static props = {
        close: { type: Function, optional: true },
        onConfirm: { type: Function },
        title: { type: String, optional: true },
        confirmLabel: { type: String, optional: true },
        initialName: { type: String, optional: true },
    };
    static defaultProps = {
        title: "New Board",
        confirmLabel: "Create",
        initialName: "",
    };

    setup() {
        this.state = useState({ name: this.props.initialName });
        this.inputRef = useRef("input");
        onMounted(() => {
            this.inputRef.el?.focus();
            this.inputRef.el?.select();
        });
    }

    confirm() {
        const name = this.state.name.trim();
        if (!name) {
            return;
        }
        this.props.onConfirm(name);
        this.props.close();
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            this.confirm();
        }
    }
}
