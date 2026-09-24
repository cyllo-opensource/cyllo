/** @odoo-module **/

export const SignMixin = {

    _setupSignResizeHandles(signEl) {
        const oldHandles = signEl.querySelectorAll('.sign-resize-handle');
        oldHandles.forEach(h => {
            const clone = h.cloneNode(true);
            h.parentNode && h.parentNode.replaceChild(clone, h);
        });

        const self = this;
        signEl.querySelectorAll('.sign-resize-handle').forEach(handle => {
            const dir = handle.dataset.dir;
            let startX, startY, startW, startH;

            const onMove = (e) => {
                const dx = e.clientX - startX;
                const dy = e.clientY - startY;
                let newW = startW;
                let newH = startH;

                if (dir.includes('e')) newW = Math.max(100, startW + dx);
                if (dir.includes('w')) newW = Math.max(100, startW - dx);
                if (dir.includes('s')) newH = Math.max(50, startH + dy);
                if (dir.includes('n')) newH = Math.max(50, startH - dy);

                signEl.style.width = newW + 'px';
                signEl.style.height = newH + 'px';

                try {
                    const cfg = JSON.parse(signEl.dataset.signConfig || '{}');
                    cfg.width = Math.round(newW);
                    cfg.height = Math.round(newH);
                    signEl.dataset.signConfig = JSON.stringify(cfg);
                    
                    if (self._selectedSignEl === signEl) {
                        self.state.signConfig.width = cfg.width;
                        self.state.signConfig.height = cfg.height;
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
                startW = signEl.offsetWidth;
                startH = signEl.offsetHeight;
                document.addEventListener('pointermove', onMove);
                document.addEventListener('pointerup', onUp);
            });
        });
    },

    openSignProps(signEl) {
        this._selectedSignEl = signEl;
        let cfg = {};
        try { cfg = JSON.parse(signEl.dataset.signConfig || '{}'); } catch (e) { }
        
        this.state.signConfig = {
            role: cfg.role || 'customer',
            label: cfg.label || 'Authorized Signature',
            required: cfg.required !== undefined ? cfg.required : true,
            show_date: cfg.show_date !== undefined ? cfg.show_date : false,
            show_name: cfg.show_name !== undefined ? cfg.show_name : false,
            width: cfg.width || signEl.offsetWidth || 200,
            height: cfg.height || signEl.offsetHeight || 100,
            alignment: cfg.alignment || 'left',
        };
        this.state.showSignProps = true;
    },

    closeSignProps() {
        this._selectedSignEl = null;
        this.state.showSignProps = false;
    },

    onSignConfigChange(field, value) {
        const signEl = this._selectedSignEl;
        if (!signEl) return;
        
        // Handle boolean values from toggles
        if (field === 'required' || field === 'show_date' || field === 'show_name') {
            this.state.signConfig[field] = value;
        } else {
            this.state.signConfig[field] = value;
        }

        let cfg = {};
        try { cfg = JSON.parse(signEl.dataset.signConfig || '{}'); } catch (e) { }
        cfg[field] = this.state.signConfig[field];
        signEl.dataset.signConfig = JSON.stringify(cfg);

        // Update DOM visual aspects immediately
        if (field === 'label') {
            const labelEl = signEl.querySelector('.sign-label');
            if (labelEl) labelEl.textContent = value;
        } else if (field === 'width') {
            const v = Math.max(100, parseInt(value) || 100);
            signEl.style.width = v + 'px';
            cfg.width = v;
        } else if (field === 'height') {
            const v = Math.max(50, parseInt(value) || 50);
            signEl.style.height = v + 'px';
            cfg.height = v;
        } else if (field === 'alignment') {
            signEl.style.textAlign = value;
            cfg.alignment = value;
        } else if (field === 'role') {
            signEl.dataset.role = value;
            const badgeEl = signEl.querySelector('.sign-role-badge');
            if (badgeEl) badgeEl.textContent = value;
        } else if (field === 'show_date') {
            let dateEl = signEl.querySelector('.sign-date');
            if (value && !dateEl) {
                const p = document.createElement('p');
                p.className = 'sign-date';
                p.style.margin = '2px 0';
                p.style.fontSize = '12px';
                p.style.color = '#666';
                p.innerHTML = 'Date: <span>____________</span>';
                signEl.querySelector('.sign-content-wrapper').appendChild(p);
            } else if (!value && dateEl) {
                dateEl.remove();
            }
        } else if (field === 'show_name') {
            let nameEl = signEl.querySelector('.sign-name');
            if (value && !nameEl) {
                const p = document.createElement('p');
                p.className = 'sign-name';
                p.style.margin = '2px 0';
                p.style.fontSize = '12px';
                p.style.color = '#666';
                p.innerHTML = 'Name: <span>____________</span>';
                // Insert before the date if date exists, otherwise at end
                const wrapper = signEl.querySelector('.sign-content-wrapper');
                const dateEl = wrapper.querySelector('.sign-date');
                if (dateEl) {
                    wrapper.insertBefore(p, dateEl);
                } else {
                    wrapper.appendChild(p);
                }
            } else if (!value && nameEl) {
                nameEl.remove();
            }
        }
        
        signEl.dataset.signConfig = JSON.stringify(cfg);
    },

    deleteSelectedSign() {
        const signEl = this._selectedSignEl;
        if (!signEl) return;
        if (confirm("Delete this Signature field?")) {
            this.closeSignProps();
            signEl.remove();
        }
    }
};
