/** @odoo-module **/
export const BoxMixin = {

    _setupBoxResizeHandles(boxEl) {
        // Remove previous listeners by replacing handle container
        const oldHandles = boxEl.querySelectorAll('.box-resize-handle');
        oldHandles.forEach(h => {
            // Clone replaces to remove old listeners
            const clone = h.cloneNode(true);
            h.parentNode && h.parentNode.replaceChild(clone, h);
        });

        const self = this;
        boxEl.querySelectorAll('.box-resize-handle').forEach(handle => {
            const dir = handle.dataset.dir;
            let startX, startY, startW, startH;

            const onMove = (e) => {
                const dx = e.clientX - startX;
                const dy = e.clientY - startY;
                let newW = startW;
                let newH = startH;

                if (dir.includes('e')) newW = Math.max(80, startW + dx);
                if (dir.includes('w')) newW = Math.max(80, startW - dx);
                if (dir.includes('s')) newH = Math.max(80, startH + dy);
                if (dir.includes('n')) newH = Math.max(80, startH - dy);

                boxEl.style.width = newW + 'px';
                boxEl.style.height = newH + 'px';

                // Live-update config
                try {
                    const cfg = JSON.parse(boxEl.dataset.boxConfig || '{}');
                    cfg.style = cfg.style || {};
                    cfg.style.width = Math.round(newW);
                    cfg.style.height = Math.round(newH);
                    boxEl.dataset.boxConfig = JSON.stringify(cfg);
                    // Update props panel if this box is selected
                    if (self._selectedBoxEl === boxEl) {
                        self.state.boxConfig.width = cfg.style.width;
                        self.state.boxConfig.height = cfg.style.height;
                    }
                } catch (ex) { }
            };

            const onUp = () => {
                document.removeEventListener('pointermove', onMove);
                document.removeEventListener('pointerup', onUp);
            };

            handle.addEventListener('pointerdown', (e) => {
                if (self.state.previewMode) return;
                e.stopPropagation();
                e.preventDefault();
                startX = e.clientX;
                startY = e.clientY;
                startW = boxEl.offsetWidth;
                startH = boxEl.offsetHeight;
                document.addEventListener('pointermove', onMove);
                document.addEventListener('pointerup', onUp);
            });
        });
    },

    openBoxProps(boxEl) {
        this._selectedBoxEl = boxEl;
        let cfg = {};
        try { cfg = JSON.parse(boxEl.dataset.boxConfig || '{}'); } catch (e) { }
        const s = cfg.style || {};
        this.state.boxConfig = {
            label: cfg.label || 'Section',
            width: s.width || boxEl.offsetWidth || 300,
            height: s.height || boxEl.offsetHeight || 200,
            backgroundColor: s.backgroundColor || 'transparent',
            border: s.border || '1px solid #ccc',
            borderRadius: s.borderRadius !== undefined ? s.borderRadius : 4,
            padding: s.padding !== undefined ? s.padding : 8,
            marginTop: s.marginTop !== undefined ? s.marginTop : 16,
            layoutMode: cfg.layoutMode || 'free',
        };
        this.state.showBoxProps = true;
    },

    closeBoxProps() {
        this._selectedBoxEl = null;
        this.state.showBoxProps = false;
    },

    onBoxConfigChange(field, value) {
        const boxEl = this._selectedBoxEl;
        if (!boxEl) return;
        this.state.boxConfig[field] = value;

        let cfg = {};
        try { cfg = JSON.parse(boxEl.dataset.boxConfig || '{}'); } catch (e) { }
        cfg.style = cfg.style || {};

        if (field === 'label') {
            cfg.label = value;
            const labelEl = boxEl.querySelector('.box-label-text');
            if (labelEl) labelEl.textContent = value;
        } else if (field === 'width') {
            const v = Math.max(80, parseInt(value) || 80);
            cfg.style.width = v;
            boxEl.style.width = v + 'px';
        } else if (field === 'height') {
            const v = Math.max(80, parseInt(value) || 80);
            cfg.style.height = v;
            boxEl.style.height = v + 'px';
        } else if (field === 'backgroundColor') {
            cfg.style.backgroundColor = value;
            const dz = boxEl.querySelector('.box-dropzone');
            if (dz) dz.style.backgroundColor = value;
        } else if (field === 'border') {
            cfg.style.border = value;
            const dz = boxEl.querySelector('.box-dropzone');
            if (dz) dz.style.border = value;
        } else if (field === 'borderRadius') {
            const v = parseInt(value) || 0;
            cfg.style.borderRadius = v;
            const dz = boxEl.querySelector('.box-dropzone');
            if (dz) dz.style.borderRadius = v + 'px';
        } else if (field === 'padding') {
            const v = parseInt(value) || 0;
            cfg.style.padding = v;
            const dz = boxEl.querySelector('.box-dropzone');
            if (dz) dz.style.padding = v + 'px';
        } else if (field === 'marginTop') {
            const v = Math.max(0, parseInt(value) || 0);
            cfg.style.marginTop = v;
            boxEl.style.marginTop = v + 'px';
        }

        boxEl.dataset.boxConfig = JSON.stringify(cfg);
    },

    onBoxLayoutModeChange(mode) {
        const boxEl = this._selectedBoxEl;
        if (!boxEl) return;
        this.state.boxConfig.layoutMode = mode;

        let cfg = {};
        try { cfg = JSON.parse(boxEl.dataset.boxConfig || '{}'); } catch (e) { }
        cfg.layoutMode = mode;
        boxEl.dataset.boxConfig = JSON.stringify(cfg);

        const dz = boxEl.querySelector('.box-dropzone');
        if (dz) {
            dz.classList.remove('layout-free', 'layout-flow');
            dz.classList.add('layout-' + mode);
        }
        const badge = boxEl.querySelector('.box-layout-badge');
        if (badge) badge.textContent = mode;
    },

    deleteSelectedBox() {
        const boxEl = this._selectedBoxEl;
        if (!boxEl) return;
        this.closeBoxProps();
        boxEl.remove();
    }
};
