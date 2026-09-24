/** @odoo-module **/

import { Component, useRef, useState, onMounted } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

const PREVIEW_WIDTH = 600;
const MIN_PREVIEW_HEIGHT = 80;
const MAX_PREVIEW_HEIGHT = 400;
const OUTPUT_WIDTH = 1200;

export class BannerCropDialog extends Component {
    setup() {
        this.wrapperRef = useRef("wrapper");
        this.imgRef = useRef("img");
        this.previewWidth = PREVIEW_WIDTH;
        this.previewHeight = Math.round(
            Math.max(MIN_PREVIEW_HEIGHT, Math.min(MAX_PREVIEW_HEIGHT, PREVIEW_WIDTH / this.props.aspectRatio))
        );
        this.state = useState({ ready: false, scale: 1, x: 0, y: 0 });
        this.minScale = 1;
        this.naturalWidth = 0;
        this.naturalHeight = 0;
        this.dragging = false;
        this.dragStart = null;

        onMounted(() => {
            const img = new Image();
            img.onload = () => {
                this.naturalWidth = img.naturalWidth;
                this.naturalHeight = img.naturalHeight;
                const coverScale = Math.max(
                    this.previewWidth / this.naturalWidth,
                    this.previewHeight / this.naturalHeight
                );
                this.minScale = coverScale;
                this.state.scale = coverScale;
                this.state.x = (this.previewWidth - this.naturalWidth * coverScale) / 2;
                this.state.y = (this.previewHeight - this.naturalHeight * coverScale) / 2;
                this.state.ready = true;
            };
            img.onerror = () => this.props.close();
            img.src = this.props.imageUrl;
        });
    }

    get imgStyle() {
        return `width:${this.naturalWidth * this.state.scale}px;height:${this.naturalHeight * this.state.scale}px;transform:translate(${this.state.x}px, ${this.state.y}px);`;
    }

    clampPosition() {
        const w = this.naturalWidth * this.state.scale;
        const h = this.naturalHeight * this.state.scale;
        this.state.x = Math.min(0, Math.max(this.previewWidth - w, this.state.x));
        this.state.y = Math.min(0, Math.max(this.previewHeight - h, this.state.y));
    }

    onPointerDown(ev) {
        if (!this.state.ready) return;
        this.dragging = true;
        this.dragStart = { x: ev.clientX, y: ev.clientY, offX: this.state.x, offY: this.state.y };
        ev.currentTarget.setPointerCapture(ev.pointerId);
    }

    onPointerMove(ev) {
        if (!this.dragging) return;
        this.state.x = this.dragStart.offX + (ev.clientX - this.dragStart.x);
        this.state.y = this.dragStart.offY + (ev.clientY - this.dragStart.y);
        this.clampPosition();
    }

    onPointerUp() {
        this.dragging = false;
    }

    onWheel(ev) {
        if (!this.state.ready) return;
        ev.preventDefault();
        const prevScale = this.state.scale;
        let newScale = prevScale * (1 - ev.deltaY * 0.001);
        newScale = Math.min(this.minScale * 4, Math.max(this.minScale, newScale));
        const rect = this.wrapperRef.el.getBoundingClientRect();
        const px = ev.clientX - rect.left;
        const py = ev.clientY - rect.top;
        const ratio = newScale / prevScale;
        this.state.x = px - (px - this.state.x) * ratio;
        this.state.y = py - (py - this.state.y) * ratio;
        this.state.scale = newScale;
        this.clampPosition();
    }

    onZoomIn() {
        this.state.scale = Math.min(this.minScale * 4, this.state.scale * 1.2);
        this.clampPosition();
    }

    onZoomOut() {
        this.state.scale = Math.max(this.minScale, this.state.scale / 1.2);
        this.clampPosition();
    }

    _cancel() {
        this.props.close();
    }

    _confirm() {
        const outputWidth = OUTPUT_WIDTH;
        const outputHeight = Math.round(outputWidth / this.props.aspectRatio);
        const canvas = document.createElement("canvas");
        canvas.width = outputWidth;
        canvas.height = outputHeight;
        const ctx = canvas.getContext("2d");
        const scaleFactor = outputWidth / this.previewWidth;
        ctx.drawImage(
            this.imgRef.el,
            0, 0, this.naturalWidth, this.naturalHeight,
            this.state.x * scaleFactor, this.state.y * scaleFactor,
            this.naturalWidth * this.state.scale * scaleFactor,
            this.naturalHeight * this.state.scale * scaleFactor
        );
        this.props.onConfirm(canvas.toDataURL("image/png").split(",")[1]);
        this.props.close();
    }
}
BannerCropDialog.template = "cyllo_dashboard.BannerCropDialog";
BannerCropDialog.components = { Dialog };
BannerCropDialog.defaultProps = {
    onConfirm: () => {},
};
