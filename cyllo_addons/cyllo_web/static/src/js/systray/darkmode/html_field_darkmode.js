/** @odoo-module **/

import { HtmlField } from "@web_editor/js/backend/html_field";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched } from "@odoo/owl";

patch(HtmlField.prototype, {
    setup() {
        super.setup(...arguments);
        this.env.bus?.addEventListener("DARK_MODE_UPDATED", (event) => {
            this._updateIframeDarkMode(event.detail);
        });

        onMounted(() => {
            this._updateIframeDarkMode(this._isDarkModeActive());
        });

        onPatched(() => {
            this._updateIframeDarkMode(this._isDarkModeActive());
        });
    },

    async _setupReadonlyIframe() {
        const res = await super._setupReadonlyIframe(...arguments);
        this._updateIframeDarkMode(this._isDarkModeActive());
        if (this.iframeRef?.el) {
            this.iframeRef.el.addEventListener("load", () => {
                this._updateIframeDarkMode(this._isDarkModeActive());
            });
        }
        return res;
    },

    _isDarkModeActive() {
        return (
            document.documentElement.getAttribute("data-darkreader-scheme") === "dark" ||
            localStorage.getItem("darkMode") === "true"
        );
    },

    _updateIframeDarkMode(isDark) {
        if (!this.iframeRef?.el) {
            return;
        }
        let cdoc;
        try {
            cdoc = this.iframeRef.el.contentDocument;
        } catch (e) {
            return;
        }
        if (!cdoc) {
            return;
        }

        let styleEl = cdoc.getElementById("cyllo-mail-dark-mode");
        if (isDark) {
            if (!styleEl) {
                styleEl = cdoc.createElement("style");
                styleEl.id = "cyllo-mail-dark-mode";
                const target = cdoc.head || cdoc.documentElement || cdoc.body;
                if (target) {
                    target.appendChild(styleEl);
                }
            }
            styleEl.textContent = `
                :root, html, body {
                    color-scheme: dark !important;
                    background-color: transparent !important;
                    color: #fafafa !important;
                }
                body, p, span, div, td, th, li, h1, h2, h3, h4, h5, h6, b, strong, em, i, u, font, label, section, article, blockquote {
                    color: #fafafa !important;
                }
                a, a * {
                    color: #58a6ff !important;
                }
                [style*="background-color: #fff"],
                [style*="background-color: #FFF"],
                [style*="background-color: #ffffff"],
                [style*="background-color: #FFFFFF"],
                [style*="background-color: white"],
                [style*="background-color: rgb(255, 255, 255)"],
                [style*="background: #fff"],
                [style*="background: #FFF"],
                [style*="background: #ffffff"],
                [style*="background: #FFFFFF"],
                [style*="background: white"],
                [style*="background: rgb(255, 255, 255)"] {
                    background-color: #1a1d14 !important;
                }
                hr {
                    border-color: #333 !important;
                }
            `;
        } else if (styleEl) {
            styleEl.remove();
        }
    },
});
