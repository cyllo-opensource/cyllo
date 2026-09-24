/** @odoo-module **/

import { registry } from '@web/core/registry';
import { Component, useRef, onMounted, onWillUnmount, useState, onWillStart, onPatched } from "@odoo/owl";
import { StudioFieldSelectorPopover } from "@cyllo_studio/js/studio_field_selector_popover";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { usePopover } from "@web/core/popover/popover_hook";
import { groupBy } from "@web/core/utils/arrays";
import { debounce } from "@web/core/utils/timing";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { QrMixin } from "@cyllo_studio/js/custom_report/studio_report_qr";
import { BoxMixin } from "@cyllo_studio/js/custom_report/studio_report_box";
import { SignMixin } from "@cyllo_studio/js/custom_report/studio_report_sign";
import { RemoveSessions } from "@cyllo_studio/js/root/studio_wrapper";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";

const Sortable = window.Sortable;

const escapeHtml = (unsafe) => {
    return (unsafe || '').toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
};

const SS_TEMPLATE = 'cyllo_report_template';
const SS_RES_MODEL = 'cyllo_report_res_model';

const PAPER_FORMAT_MAP = {
    'A0': [841, 1189], 'A1': [594, 841], 'A2': [420, 594], 'A3': [297, 420],
    'A4': [210, 297], 'A5': [148, 210], 'A6': [105, 148], 'A7': [74, 105],
    'A8': [52, 74], 'A9': [37, 52], 'B0': [1000, 1414], 'B1': [707, 1000],
    'B2': [500, 707], 'B3': [353, 500], 'B4': [250, 353], 'B5': [176, 250],
    'B6': [125, 176], 'B7': [88, 125], 'B8': [62, 88], 'B9': [44, 62],
    'B10': [31, 44], 'C5E': [163, 229], 'Comm10E': [105, 241], 'DLE': [110, 220],
    'Executive': [184, 267], 'Folio': [210, 330], 'Ledger': [432, 279],
    'Legal': [216, 356], 'Letter': [216, 279], 'Tabloid': [279, 432]
};

export class EditReport extends Component {
    setup() {
        this.reportFrameRef = useRef("report_frame");
        this.undoBtn = useRef("undoBtn");
        this.redoBtn = useRef("redoBtn");
        this.aceEditorRef = useRef("aceEditor");
        this.logoInputRef = useRef("logoInput");
        this.action = useService("action");
        this.popover = useService("popover");
        this.loadFieldInfo = useLoadFieldInfo();
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this._debouncedSaveCompanyFooter = debounce(() => this.saveCompanyFooter(true), 800);

        this.state = useState({
            previewMode: false,
            records: [],
            currentIndex: 0,
            reportInfo: {},
            paperFormats: [],
            previewHtml: false,
            previewUrl: false,
            showSourceEditor: false,
            sourceCode: "",
            showResetDialog: false,
            showActionsMenu: false,
            showTemplateDialog: false,
            templateForm: {
                name: "",
                description: "",
                category: "",
            },
            includeHeaderFooter: true,
            // ── Table Config Modal state ──
            showTableModal: false,
            isSaving: false,
            tcm: this._getDefaultTcmState(),
            // ── QR Wizard state ──
            showQrWizard: false,
            qr: this._getDefaultQrState(),
            hasThumbnail: this.props.action.params.has_thumbnail || false,
            // ── Box Properties Panel state ──
            showBoxProps: false,
            boxConfig: {
                label: 'Section',
                width: 300,
                height: 200,
                backgroundColor: 'transparent',
                border: '1px solid #ccc',
                borderRadius: 4,
                padding: 8,
                layoutMode: 'free',
            },
            // ── Signature Properties Panel state ──
            showSignProps: false,
            signConfig: {
                role: 'customer',
                label: 'Authorized Signature',
                required: true,
                show_date: false,
                show_name: false,
                width: 200,
                height: 100,
                alignment: 'left',
            },
            analytics: {
                total_scans: 0,
                recent_scans: [],
            },
            hasQr: false,
            hasSign: false,
            hasOverflow: false,
            // ── Company & Report Settings ──
            companyLogo: null,
            companyName: '',
            companyInfo: '',
            hideLogo: false,
            logoHovered: false,
            // ── Footer Preview Controls ──
            footerShowReportFooter: true,
            footerShowPageNum: true,
            footerShowDocName: false,
            showFooterEditor: false,
            companyReportFooterText: '',
            hasCustomFooter: false,
            editIframeUrl: '',
        });

        // Promise resolver for the table config modal
        this._tcmResolve = null;

        // Track SortableJS instances so we can destroy/recreate on DOM changes
        this._sortableInstances = [];
        this._isDragging = false;

        onWillStart(async () => {
            await loadJS("/web/static/lib/ace/ace.js");
            // Fetch company logo and info
            try {
                let companyId = null;
                if (this.env && this.env.company && this.env.company.id) {
                    companyId = this.env.company.id;
                }
                const domain = companyId ? [['id', '=', companyId]] : [];

                const companies = await this.orm.searchRead(
                    'res.company',
                    domain,
                    ['name', 'logo', 'street', 'city', 'phone', 'email', 'website', 'report_footer'],
                    { limit: 1, order: 'id asc' }
                );
                if (companies && companies.length > 0) {
                    const co = companies[0];
                    this._companyId = co.id; // store for logo upload
                    this.state.companyLogo = co.logo || null;
                    this.state.companyName = co.name || '';
                    this.state.companyReportFooterText = co.report_footer || '';
                    this.state.companyInfo = this._formatCompanyInfo(co);
                }
            } catch (e) {
                console.warn('[Cyllo Studio] Could not fetch company info:', e);
            }
            let companyId = null;
            if (!companyId) {
                const companies = await this.orm.searchRead(
                    'res.company', [], ['id'], { limit: 1, order: 'id asc' }
                );
                if (companies && companies.length > 0) {
                    companyId = companies[0].id;
                }
            }

            if (!companyId) {
                console.warn('[Cyllo Studio] Could not determine company ID by any method.');
                return;
            }

            this._companyId = companyId;
        });

        onMounted(async () => {
            const params = this.props.action.params || {};

            // Hide the Cyllo sidebar logic per user request
            this._cyElsToRestore = [];

            // 1. Hide the exact submenu box requested (and firmly use !important to block OWL patches)
            const submenuBox = document.querySelector('.cy-submenu-box');
            if (submenuBox) {
                this._cyElsToRestore.push({ el: submenuBox, display: submenuBox.style.display || '' });
                submenuBox.style.setProperty('display', 'none', 'important');

                // 2. Hide the sibling wrapper / parent container that holds the dark sidebar
                const parentNav = submenuBox.parentElement;
                if (parentNav) {
                    this._cyElsToRestore.push({ el: parentNav, display: parentNav.style.display || '' });
                    parentNav.style.setProperty('display', 'none', 'important');

                    // 3. Find the closest flex/grid ancestor
                    let layoutContainer = parentNav.parentElement;
                    while (layoutContainer && layoutContainer.tagName !== 'BODY') {
                        const style = window.getComputedStyle(layoutContainer);
                        if (style.display.includes('flex') || style.display.includes('grid')) {
                            break;
                        }
                        layoutContainer = layoutContainer.parentElement;
                    }

                    // 4. Force the content sibling to take full width
                    if (layoutContainer && layoutContainer.tagName !== 'BODY') {
                        Array.from(layoutContainer.children).forEach(child => {
                            if (!child.contains(parentNav) && child !== parentNav && !child.classList.contains('o_navbar')) {
                                this._cyElsToRestore.push({
                                    el: child,
                                    width: child.style.width || '',
                                    flex: child.style.flex || '',
                                    maxWidth: child.style.maxWidth || '',
                                    marginLeft: child.style.marginLeft || '',
                                    paddingLeft: child.style.paddingLeft || ''
                                });
                                child.style.setProperty('width', '100%', 'important');
                                child.style.setProperty('flex', '1 1 auto', 'important');
                                child.style.setProperty('max-width', '100%', 'important');
                                child.style.setProperty('margin-left', '0', 'important');
                                child.style.setProperty('padding-left', '0', 'important');
                            }
                        });
                    }
                }

                // Fallback direct kills for sticky buttons that might escape
                const sideItems = document.querySelectorAll('.cy_dashboard_back-btn, .cy-left-sidebar, .cy-submenu-logo, #accordionSidebar, .cy-NavHeader');
                sideItems.forEach(el => {
                    this._cyElsToRestore.push({ el: el, display: el.style.display || '' });
                    el.style.setProperty('display', 'none', 'important');
                });

                // 5. Shift Action Manager down to respect Cyllo's 50px top navbar
                const actionManager = document.querySelector('.o_action_manager');
                if (actionManager) {
                    const isAlreadyTracked = this._cyElsToRestore.some(item => item.el === actionManager);
                    if (!isAlreadyTracked) {
                        this._cyElsToRestore.push({
                            el: actionManager,
                            width: actionManager.style.width || '',
                            marginLeft: actionManager.style.marginLeft || '',
                            paddingLeft: actionManager.style.paddingLeft || ''
                        });
                    }
                    actionManager.style.setProperty('width', '100%', 'important');
                    actionManager.style.setProperty('height', '100%', 'important');
                    actionManager.style.setProperty('margin-left', '0', 'important');
                    actionManager.style.setProperty('padding-left', '0', 'important');
                    actionManager.style.setProperty('margin-top', '0', 'important');
                }

                // 6. Force the main content container to take full height
                const content = document.querySelector('.o_content');
                if (content) {
                    this._cyElsToRestore.push({
                        el: content,
                        height: content.style.height || '',
                        maxHeight: content.style.maxHeight || '',
                        overflow: content.style.overflow || ''
                    });
                    content.style.setProperty('height', '100vh', 'important');
                    content.style.setProperty('max-height', '100vh', 'important');
                    content.style.setProperty('overflow', 'hidden', 'important');
                }
            }

            let template = params.template;
            let resModel = params.res_model;

            if (template) {
                sessionStorage.setItem(SS_TEMPLATE, template);
                sessionStorage.setItem(SS_RES_MODEL, resModel || '');
            } else {
                template = sessionStorage.getItem(SS_TEMPLATE) || '';
                resModel = sessionStorage.getItem(SS_RES_MODEL) || '';
            }

            this._template = template;
            this._resModel = resModel;
            this._reportId = params.report_id || null;

            let arch = params.arch;
            if (!arch || arch === 'undefined') {
                if (!template) {
                    console.warn('[Cyllo Studio] No template available – cannot fetch arch.');
                } else {
                    const result = await this.rpc('/cyllo_studio/get_arch', { template });
                    arch = (result && result.success) ? result.arch : '';
                    if (!result || !result.success) {
                        console.warn('[Cyllo Studio] get_arch failed:', result?.error);
                    }
                }
            }

            // Check if the saved arch contains a logo-hide override and restore state
            if (arch && typeof arch === 'string' && arch.includes('cy-logo-override')) {
                this.state.hideLogo = true;
                // Strip it out of the editable canvas so it doesn't appear as a DOM node
                const parser = new DOMParser();
                const archDoc = parser.parseFromString(arch, 'text/html');
                archDoc.querySelectorAll('.cy-logo-override').forEach(el => el.remove());
                arch = archDoc.body.innerHTML;
            } else {
                this.state.hideLogo = false;
            }

            this.state.editIframeUrl = `/cyllo_studio/edit_canvas/${this._template}`;

            // The iframe load event will trigger onEditIframeLoad, which will set up Sortable.
            await this._fetchPreviewData();
            requestAnimationFrame(() => this._applyPaperFormatToCanvas());

            // Render initial footer preview
            this._renderFooterPreview();
        });

        onWillUnmount(() => {
            // Tear down drag/editor machinery so listeners/instances don't leak
            // when the editor component is destroyed.
            try { this._destroySortableInstances(); } catch (_) { }
            if (this.undoManager) {
                try { this.undoManager.destroy(); } catch (_) { }
                this.undoManager = null;
            }
            if (this.editor) {
                try { this.editor.destroy(); } catch (_) { }
                this.editor = null;
            }
            if (this._cyElsToRestore && this._cyElsToRestore.length > 0) {
                this._cyElsToRestore.forEach(item => {
                    if (item.display !== undefined) item.el.style.display = item.display;
                    if (item.width !== undefined) item.el.style.width = item.width;
                    if (item.flex !== undefined) item.el.style.flex = item.flex;
                    if (item.maxWidth !== undefined) item.el.style.maxWidth = item.maxWidth;
                    if (item.marginLeft !== undefined) item.el.style.marginLeft = item.marginLeft;
                    if (item.paddingLeft !== undefined) item.el.style.paddingLeft = item.paddingLeft;
                });
                this._cyElsToRestore = [];
            }
        });

        onPatched(() => {
            // Re-setup sortable if the component was patched (e.g. after modal close)
            // to ensure listeners are still attached to the live DOM elements.
            if (!this._isDragging) {
                this._setupSortable();
            } else {
                this._pendingSortableRebuild = true;
            }
            // Re-inject footer preview strip in case OWL replaced the DOM node
            this._renderFooterPreview();
            requestAnimationFrame(() => this._applyPaperFormatToCanvas());
        });
    }



    /**
     * Render the footer preview strip.
     * Always builds clean HTML from our own template — never uses raw backend HTML
     * Respects state.footerShowReportFooter and state.footerShowPageNum toggles.
     */
    _renderFooterPreview() {
        const el = document.getElementById('studio_footer_preview');
        if (!el) return;

        const showFooter = this.state.footerShowReportFooter;
        const showPageNum = this.state.footerShowPageNum;
        const showDocName = this.state.footerShowDocName;

        if (!showFooter && !showPageNum) {
            el.innerHTML = '<div class="cy-footer-empty-msg">All footer elements hidden</div>';
        } else {
            const leftHtml = [
                showFooter ? `<span class="cy-footer-placeholder">${this.state.companyReportFooterText || 'Company \u203A Report Footer'}</span>` : '',
                showDocName && showFooter ? '<span class="cy-footer-separator"> &nbsp;|&nbsp; </span>' : '',
                showDocName ? '<span class="cy-footer-placeholder">o.name</span>' : '',
            ].join('');

            const rightHtml = showPageNum
                ? 'Page <span class="cy-footer-expr">1</span> / <span class="cy-footer-expr">N</span>'
                : '';

            el.innerHTML = `
                <div class="cy-footer-row">
                    <div class="cy-footer-cell-left">${leftHtml}</div>
                    <div class="cy-footer-cell-right">${rightHtml}</div>
                </div>`;
        }

        el.style.pointerEvents = 'none';
        el.style.userSelect = 'none';
    }

    /**
     * Render header inside iframe
     */
    _renderHeaderInIframe(iframeDoc) {
        const headerEl = iframeDoc.querySelector('.cy-report-header');
        if (!headerEl) return;

        const logoBlock = headerEl.querySelector('.cy-logo-block');
        if (logoBlock) {
            let logoHtml = '';
            if (this.state.companyLogo && !this.state.hideLogo) {
                logoHtml = `
                    <div class="cy-logo-wrapper" style="position: relative; display: inline-block; border-radius: 4px; overflow: hidden;"
                         onmouseenter="this.querySelector('.cy-logo-overlay').style.opacity='1'"
                         onmouseleave="this.querySelector('.cy-logo-overlay').style.opacity='0'">
                        <img src="data:image/png;base64,${this.state.companyLogo}" class="cy-company-logo" alt="Company Logo" style="display: block;">
                        <div class="cy-logo-overlay" style="position: absolute; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; opacity: 0; transition: opacity 0.2s ease;">
                            <i class="ri-edit-line text-white me-3" style="font-size: 20px; cursor: pointer;" title="Change Logo" data-action="change"></i>
                            <i class="ri-eye-off-line text-warning me-3" style="font-size: 20px; cursor: pointer;" title="Hide Logo" data-action="hide"></i>
                            <i class="ri-delete-bin-line text-danger" style="font-size: 20px; cursor: pointer;" title="Delete Logo" data-action="remove"></i>
                        </div>
                    </div>
                `;
            } else {
                logoHtml = `
                    <div class="cy-logo-placeholder">
                        <i class="ri-camera-line"></i>
                        <span>${this.state.hideLogo && this.state.companyLogo ? 'Logo hidden — click to restore' : 'Your logo'}</span>
                    </div>
                `;
            }
            logoBlock.innerHTML = logoHtml + `
                <input type="file" class="cy-logo-input" accept="image/*" style="display:none">
            `;

            // Attach file input listener
            const fileInput = logoBlock.querySelector('.cy-logo-input');
            const self = this;
            fileInput.addEventListener('change', function (e) {
                self._handleLogoFileChange(e, iframeDoc);
            });
        }
    }

    /**
     * Render footer inside iframe
     */
    _renderFooterInIframe(iframeDoc) {
        const footerEl = iframeDoc.getElementById('studio_footer_preview');
        if (!footerEl) return;

        const showFooter = this.state.footerShowReportFooter;
        const showPageNum = this.state.footerShowPageNum;
        const showDocName = this.state.footerShowDocName;

        if (!showFooter && !showPageNum) {
            footerEl.innerHTML = '<div class="cy-footer-empty-msg">All footer elements hidden</div>';
        } else {
            const leftHtml = [
                showFooter ? `<span class="cy-footer-placeholder">${this.state.companyReportFooterText || 'Company \u203A Report Footer'}</span>` : '',
                showDocName && showFooter ? '<span class="cy-footer-separator"> &nbsp;|&nbsp; </span>' : '',
                showDocName ? '<span class="cy-footer-placeholder">o.name</span>' : '',
            ].join('');

            const rightHtml = showPageNum
                ? 'Page <span class="cy-footer-expr">1</span> / <span class="cy-footer-expr">N</span>'
                : '';

            footerEl.innerHTML = `
                <div class="cy-footer-row">
                    <div class="cy-footer-cell-left">${leftHtml}</div>
                    <div class="cy-footer-cell-right">${rightHtml}</div>
                </div>`;
        }

        footerEl.style.pointerEvents = 'none';
        footerEl.style.userSelect = 'none';
    }

    async _handleLogoClickInIframe(e, iframeDoc) {
        e.preventDefault();
        e.stopPropagation();

        if (this.state.hideLogo && this.state.companyLogo) {
            this.state.hideLogo = false;
            if (this.undoManager) this.undoManager.debouncedSave();
            this._renderHeaderInIframe(iframeDoc);
            return;
        }

        const action = e.target.dataset.action;
        if (!action) {
            if (!this.state.companyLogo) {
                const fileInput = iframeDoc.querySelector('.cy-logo-input');
                if (fileInput) fileInput.click();
            }
            return;
        }

        if (action === 'change') {
            const fileInput = iframeDoc.querySelector('.cy-logo-input');
            if (fileInput) fileInput.click();
        } else if (action === 'hide') {
            this.state.hideLogo = true;
            if (this.undoManager) this.undoManager.debouncedSave();
            this._renderHeaderInIframe(iframeDoc);
        } else if (action === 'remove') {
            const companyId = this._companyId;
            if (!companyId) {
                this.notification.add('Could not determine company. Please reload and try again.', { type: 'warning' });
                return;
            }
            try {
                await this.orm.write('res.company', [companyId], { logo: false });
                this.state.companyLogo = false;
                this.notification.add('Company logo removed', { type: 'success' });
                if (this.undoManager) this.undoManager.debouncedSave();
                this._renderHeaderInIframe(iframeDoc);
            } catch (err) {
                this.notification.add('Failed to delete logo: ' + err.message, { type: 'danger' });
            }
        }
    }

    /**
     * Handle logo file change inside iframe
     */
    async _handleLogoFileChange(e, iframeDoc) {
        const file = e.target.files[0];
        if (!file) return;
        // Use stored company ID (this.env.company may not be available in Community)
        const companyId = this._companyId;
        if (!companyId) {
            this.notification.add('Could not determine company. Please reload and try again.', { type: 'warning' });
            return;
        }
        const reader = new FileReader();
        const self = this;
        reader.onload = async (ev) => {
            const base64 = ev.target.result.split(',')[1];
            try {
                await self.orm.write('res.company', [companyId], { logo: base64 });
                self.state.companyLogo = base64;
                self.state.hideLogo = false;
                if (self.undoManager) self.undoManager.debouncedSave();
                self._renderHeaderInIframe(iframeDoc);
                self.notification.add('Company logo updated', { type: 'success' });
            } catch (err) {
                self.notification.add('Failed to save logo: ' + err.message, { type: 'danger' });
            }
        };
        reader.readAsDataURL(file);
    }

    /**
     * Update footer in iframe
     */
    _updateFooterInIframe() {
        this._renderFooterPreview();
        if (this.reportFrameRef.el && this.reportFrameRef.el.contentDocument) {
            this._renderFooterInIframe(this.reportFrameRef.el.contentDocument);
        }
    }

    onEditIframeLoad(ev) {
        if (!this.reportFrameRef.el || this.reportFrameRef.el.tagName !== 'IFRAME') return;
        const iframeDoc = this.reportFrameRef.el.contentDocument;
        if (!iframeDoc || !iframeDoc.body) return;

        const tempDoc = iframeDoc;
        this._updateHasQr(tempDoc.body.innerHTML);
        this._updateHasSign(tempDoc.body.innerHTML);

        // ── Strip all cy-custom-footer elements AND related style injections ──
        const customFooters = tempDoc.querySelectorAll('.cy-custom-footer');
        if (customFooters.length > 0) {
            const lastFooter = customFooters[customFooters.length - 1];
            this.state.footerShowReportFooter = lastFooter.dataset.showFooter === 'true';
            this.state.footerShowDocName = lastFooter.dataset.showDoc === 'true';
            this.state.footerShowPageNum = lastFooter.dataset.showPage === 'true';

            if (lastFooter.dataset.hasCustom === 'true') {
                this.state.hasCustomFooter = true;
                this.state.companyReportFooterText = decodeURIComponent(lastFooter.dataset.customText || '');
            } else {
                this.state.hasCustomFooter = false;
            }

            // ── Seed the saved-footer baseline from the persisted data attrs ──
            // save_changes() diffs current state vs _savedFooterState to detect changes.
            // We must seed it here (before the cy-custom-footer elements are removed)
            // because _loadedArch is captured AFTER removal and will have no footer marker.
            this._savedFooterState = {
                showF: this.state.footerShowReportFooter,
                showD: this.state.footerShowDocName,
                showP: this.state.footerShowPageNum,
                hasCustom: this.state.hasCustomFooter,
                customText: this.state.companyReportFooterText || '',
            };

            customFooters.forEach(el => el.remove());
        } else {
            this.state.footerShowReportFooter = true;
            this.state.footerShowPageNum = true;
            this.state.footerShowDocName = false;
            this.state.hasCustomFooter = false;
            // No custom footer saved yet — reset the baseline so any toggle is seen as a change
            this._savedFooterState = {
                showF: true, showD: false, showP: true, hasCustom: false, customText: ''
            };
        }

        tempDoc.querySelectorAll('style').forEach(styleEl => {
            const txt = styleEl.textContent || '';
            const cls = styleEl.getAttribute('class') || '';
            if (txt.includes('cy-custom-footer') || txt.includes('o_standard_footer') ||
                cls.includes('cy-footer-hide-std')) {
                styleEl.remove();
            }
        });

        tempDoc.querySelectorAll('.page ~ .footer, .page + .footer').forEach(el => {
            el.remove();
        });

        // ── Inject Header and Footer into iframe ──
        // Always create header and footer, even for empty templates

        // Create Header
        const headerEl = tempDoc.createElement('div');
        headerEl.className = 'cy-report-header';
        headerEl.innerHTML = `
            <div class="cy-company-block">
                <div class="cy-logo-block">
                    <div class="cy-logo-placeholder">
                        <i class="ri-camera-line"></i>
                        <span>Your logo</span>
                    </div>
                    <input type="file" class="cy-logo-input" accept="image/*" style="display:none">
                </div>
            </div>
        `;

        // Prepend header to body so it sits absolutely at the top (above address blocks)
        tempDoc.body.prepend(headerEl);

        // Create Footer
        const footerEl = tempDoc.createElement('div');
        footerEl.className = 'cy-footer-preview-wrapper mt-3';
        footerEl.innerHTML = `
            <div class="cy-footer-preview-area" id="studio_footer_preview"></div>
        `;

        // Append footer to body so it sits absolutely at the bottom
        tempDoc.body.append(footerEl);

        // Update header and footer with state
        this._renderHeaderInIframe(iframeDoc);
        this._renderFooterInIframe(iframeDoc);

        // Note: For Phase 3/4, _enrichReportDOM will need to operate on iframeDoc
        const editableArea = tempDoc.body;
        this._enrichReportDOM(editableArea);
        this._updateHasSign();
        $(editableArea).find('[t-elif], [t-else]').hide();

        // ── Store _loadedArch AFTER enrichment so it contains cy-xpath / cy-template ──
        // getChangedElements() diffs the edited iframe DOM against _loadedArch parsed as
        // originalDoc.  It queries originalDoc for [cy-template][cy-xpath] nodes to find
        // the baseline for each zone.  If _loadedArch is captured before _enrichReportDOM
        // runs, those attributes are absent and EVERY querySelector returns null — meaning
        // no zone is ever diffed, deletions and attribute changes are invisible, and Save
        // silently exits with changes.length === 0 every time.
        this._loadedArch = tempDoc.documentElement.outerHTML;

        this._setupIframeAutoResize(this.reportFrameRef.el);
        this._setupSortable();

        // Give the .page full paper height now that the iframe content exists.
        // onWillStart/onPatched call this too, but they fire before the iframe
        // finishes loading (no .page yet), so a blank/short report would otherwise
        // collapse to content height and render as "half a page".
        requestAnimationFrame(() => this._applyPaperFormatToCanvas());

        this.editor = null;

        // Destroy the previous manager before creating a new one. onEditIframeLoad
        // runs again after every save/reset (the iframe is reloaded), and the
        // manager attaches a keydown handler to the host document that is only
        // removed in destroy() — without this, handlers accumulate on each reload.
        if (this.undoManager) {
            try { this.undoManager.destroy(); } catch (_) { }
        }
        this.undoManager = new UndoRedoManager(editableArea, {
            maxStackSize: 50,
            debounceTime: 300,
            autoTrack: true,
            trackAttributes: true,
            keyboardShortcuts: true
        });
        this.undoManager.startTracking();

        new MutationObserver(() => {
            this.undoBtn.el.disabled = !this.undoManager?.canUndo();
            this.redoBtn.el.disabled = !this.undoManager?.canRedo();
        }).observe(editableArea, {
            childList: true,
            subtree: true,
            characterData: true,
            attributes: true
        });

        // ── QR Block Internal Click Handler ──
        editableArea.addEventListener("click", (e) => {
            const qrBlock = e.target.closest('.s_qr_block');
            if (qrBlock && e.target.classList.contains('qr-edit-btn')) {
                e.preventDefault();
                e.stopPropagation();
                this.openQrWizard(qrBlock, 'edit').then(config => {
                    if (config) this.insertQrBlock(qrBlock, config, 'update');
                });
            }
        });

        const self = this;
        const iframeWin = this.reportFrameRef.el.contentWindow;
        const $iframe = $(iframeDoc);  // jQuery scoped to iframe document
        editableArea.addEventListener("click", function (e) {
            if (self.state.previewMode) return;
            if (self._isDragging) return;

            let el = e.target.nodeType === 3 ? e.target.parentElement : e.target;
            if (el.classList.contains('page')) {
                $iframe.find('.selected').removeClass('selected');
                if (self.editor) self.editor.destroy();
                // Close box props when clicking canvas background
                self.closeBoxProps();
                return;
            }

            // ── Handle Logo Click ──
            if (el.closest('.cy-logo-placeholder') || el.closest('.cy-logo-wrapper')) {
                self._handleLogoClickInIframe(e, iframeDoc);
                return;
            }

            // ── Settings Button Click Handler ──
            if (el.closest('.box-settings-btn, .table-settings, .field-settings, .sign-settings-btn')) {
                e.preventDefault();
                e.stopPropagation();
                let targetEl = el.closest('.box-section-wrapper, .table-wrapper, .field-block, .sign-wrapper');
                const btnEl = el.closest('.box-settings-btn, .table-settings, .field-settings, .sign-settings-btn');
                // Use the iframe window's SettingsButton (injected via studio-editor-undo-redo-ext.js)
                const IframeSettingsButton = iframeWin.SettingsButton || window.SettingsButton;
                if (targetEl && IframeSettingsButton) {
                    const sb = new IframeSettingsButton();
                    sb.base = { options: { owner: self } };
                    sb.showPopup(targetEl, btnEl);
                }
                return;
            }

            // ── Box toolbar / resize handle – ignore for selection ──
            if (el.closest('.box-toolbar') || el.closest('.box-resize-handles') || el.closest('.table-handle-container') || el.closest('.field-handle-container') || el.closest('.sign-toolbar')) {
                return;
            }

            // ── Box drop zone click logic ──
            const boxWrapper = el.closest('.box-section-wrapper');
            const boxDropzone = el.closest('.box-dropzone');
            if (boxWrapper) {
                if (el === boxWrapper || el === boxDropzone) {
                    e.stopPropagation();
                    el = boxWrapper;
                } else {
                    e.stopPropagation();
                }
            }

            // ── Sign click logic ──
            const signWrapper = el.closest('.sign-wrapper');
            if (signWrapper) {
                e.stopPropagation();
                el = signWrapper;
            }

            // If we clicked something inside a table, we might want to select the cell OR the whole table.
            // Requirement says: clicking border/edge selects entire table.
            const tableWrapper = el.closest('.table-wrapper');
            const isHandle = el.classList.contains('table-handle') || el.closest('.table-handle') || el.classList.contains('table-toolbar') || el.closest('.table-toolbar');
            const isInCell = el.closest('td, th');

            if (isHandle && tableWrapper) {
                el = tableWrapper;
            } else if (isInCell) {
                // If we click inside a cell, select the cell and STOP PROPAGATION
                // so we don't accidentally select the table wrapper.
                el = isInCell;
                if (!self.state.previewMode) {
                    e.stopPropagation();
                }
            } else if (tableWrapper) {
                const isTableTag = el.tagName === 'TABLE';
                // If we click the wrapper directly or the table tag (border), select whole table
                if (isTableTag || el === tableWrapper) {
                    el = tableWrapper;
                }
            }

            // Handle text node selection
            const textNode = el.closest('.text-node');
            if (textNode) {
                el = textNode;
            }

            // Handle field block selection (atomic unit)
            const fieldBlock = el.closest('.field-block');
            if (fieldBlock) {
                el = fieldBlock;
            }

            // For .text-node: skip wasSelected gate — always open editor on any click
            const isTextNode = el.classList.contains('text-node');

            // ── Issue 5: Check if this element was just dropped (data-needs-edit flag) ──
            const isNewDrop = el.dataset && el.dataset.needsEdit === '1';
            if (isNewDrop) {
                delete el.dataset.needsEdit;
            }

            const wasSelected = el.classList.contains('selected');

            $iframe.find('.selected').removeClass('selected');
            if ($iframe.find('#branchSelector').css('display') !== 'none') self.closeBranchSelector();

            let element = el;
            for (let i = 0; i <= 4 && element; i++, element = element.parentElement) {
                if (['t-if', 't-elif', 't-else'].some(attr => element.hasAttribute(attr))) {
                    self.showBranchSelector(element);
                    break;
                }
            }

            el.classList.add('selected');

            // "Select then Edit" strategy:
            // text-node: ALWAYS open editor on any click (no wasSelected gate)
            // other elements: open editor only if already selected (or just dropped)
            // Allow MediumEditor for all elements
            const shouldSkipEditor = false;

            const isAlwaysOpenElement = isTextNode ||
                el.classList.contains('box-section-wrapper') ||
                el.classList.contains('table-wrapper') ||
                el.classList.contains('sign-wrapper') ||
                el.classList.contains('s_qr_block') ||
                el.classList.contains('field-block');

            const isMediumEditorElement = (element) => {
                return element && (
                    element.classList.contains('text-node') ||
                    element.classList.contains('box-section-wrapper') ||
                    element.classList.contains('table-wrapper') ||
                    element.classList.contains('sign-wrapper') ||
                    element.classList.contains('s_qr_block') ||
                    element.classList.contains('field-block')
                );
            };

            if (shouldSkipEditor || (!isAlwaysOpenElement && !wasSelected && !isNewDrop)) {
                if (self.editor) {
                    const prevEl = self.editor.elements[0];
                    self.editor.destroy();
                    self.editor = null;
                    if (isMediumEditorElement(prevEl)) {
                        prevEl.setAttribute('contenteditable', 'false');
                    }
                }
                return;
            }

            if (self.editor) {
                const prevEl = self.editor.elements[0];
                self.editor.destroy();
                if (isMediumEditorElement(prevEl)) {
                    prevEl.setAttribute('contenteditable', 'false');
                }
            }
            self.editor = null;

            if (e.target.classList.contains('tcm-delete-table') || e.target.closest('.tcm-delete-table')) {
                if (tableWrapper && confirm("Are you sure you want to delete this table?")) {
                    tableWrapper.remove();
                    return;
                }
            }

            if (isMediumEditorElement(el)) {
                el.setAttribute('contenteditable', 'true');
            }

            // Resolve MediumEditor and extension constructors from the iframe's
            // own window — they are loaded via the injected <script> tags in the
            // iframe head, NOT from the host page bundle.
            const IframeWin = iframeWin;
            const MEditor = IframeWin.MediumEditor || MediumEditor;
            const IframeSettingsButton = IframeWin.SettingsButton || window.SettingsButton;
            const IframeDeleteButton = IframeWin.DeleteButton || window.DeleteButton;
            const IframeUndoButton = IframeWin.UndoButton || window.UndoButton;
            const IframeRedoButton = IframeWin.RedoButton || window.RedoButton;
            self.editor = new MEditor(el, {
                ownerDocument: iframeDoc,
                elementsContainer: iframeDoc.body,
                toolbar: {
                    buttons: [
                        'bold', 'italic', 'underline', 'strikethrough',
                        'h1', 'h3', 'quote', 'anchor', 'deleteElement', 'settingsButton',
                    ],
                    // No relativeContainer — let MediumEditor float near the selected text
                },
                extensions: {
                    'deleteElement': IframeDeleteButton ? new IframeDeleteButton() : null,
                    'undoButton': IframeUndoButton ? new IframeUndoButton() : null,
                    'redoButton': IframeRedoButton ? new IframeRedoButton() : null,
                    'settingsButton': IframeSettingsButton ? new IframeSettingsButton() : null,
                },
                owner: self,
                placeholder: false,
                disableExtraSpaces: true,
            });
            self.editor.selectElement(el);
        });
    }

    async togglePreview() {
        const enteringPreview = !this.state.previewMode;

        if (enteringPreview) {
            // Destroy the medium editor if it's active
            if (this.editor) {
                this.editor.destroy();
                this.editor = null;
            }

            // Remove selection highlight
            $(this.reportFrameRef.el?.contentDocument).find('.selected').removeClass('selected');
            // Disable drag and drop
            this._destroySortableInstances();

            // Auto-save before preview if changes exist
            if (this.undoManager && this.undoManager.canUndo()) {
                await this.save_changes(this);
            }

            // SAFELY switch state AFTER save_changes so report_frame isn't destroyed
            this.state.previewMode = true;
            await this._fetchPreviewData();
        } else {
            this.state.previewMode = false;
            // Clear preview state so the editable frame is shown
            this.state.previewUrl = false;
            this.state.previewHtml = false;
            // The iframe will natively reload its src when preview is toggled off,
            // which will trigger onEditIframeLoad to set up Sortable and MediumEditor.
        }
        if (!this.state.previewMode) {
            // If we are exiting preview and source editor was ON,
            // we might need to re-init Ace to ensure it's properly sized
            // in the new layout if it's still visible.
            if (this.state.showSourceEditor) {
                this._initAceEditor();
            }
        }
    }

    async _fetchPreviewData() {
        this._updateHasQr();
        this._updateHasSign();
        const data = await this.rpc("/cyllo_studio/get_report_preview_data", {
            template: this._template,
            res_model: this._resModel,
        });
        if (data.success) {
            this.state.records = data.record_ids;
            this.state.reportInfo = data.report;
            // Normalize Odoo Many2one field from [id, "Name"] to just id
            if (Array.isArray(this.state.reportInfo.paperformat_id)) {
                this.state.reportInfo.paperformat_id = this.state.reportInfo.paperformat_id[0];
            }
            this.state.paperFormats = data.paper_formats;
            this.state.analytics = data.analytics || { total_scans: 0, recent_scans: [], tracking_enabled: false };
            this._recordVar = data.record_var || 'doc';
            this._recordBased = data.record_based;

            // Rely purely on the DOM/arch to decide visibility.
            this._updateHasQr();
            if (data.pricelist_preview_blocked) {
                this.notification.add(
                    'Please enable Pricelists in Settings > Sales > Pricing before previewing this report.',
                    { type: 'warning', sticky: true }
                );
                this.state.previewMode = false;
                this.state.previewUrl = false;
                this.state.previewHtml = false;
                return;
            }

            if (this.state.records.length > 0) {
                // Reset the pager to the first record so the pager index stays in
                // sync with the record actually shown after a re-fetch.
                this.state.currentIndex = 0;
                this._loadRealReport(this.state.records[0]);
            }
        }
    }

    async _loadRealReport(docId, _retryCount = 0) {
        const res = await this.rpc("/cyllo_studio/render_report_html", {
            report_id: this.state.reportInfo.id,
            doc_ids: [docId],
        });

        if (res.success) {
            // inside the iframe (srcdoc breaks relative asset bundle paths).
            this.state.previewUrl = res.preview_url || false;
            this.state.previewHtml = false;
            return;
        }

        if (res.error === 'pricelist_disabled') {
            this.notification.add(
                res.message || 'Please enable Pricelists in Settings > Sales > Pricing before previewing this report.',
                { type: 'warning', sticky: true }
            );
            return;
        }

        // Handle a stale/deleted record gracefully: skip it and advance to the
        if (res.error === 'record_missing') {
            // Guard against infinite recursion in case ALL records are stale.
            const totalRecords = this.state.records.length;
            if (_retryCount >= totalRecords) {
                this.notification.add(
                    'No valid records found in the preview list. All records may have been deleted.',
                    { type: 'warning', sticky: true }
                );
                return;
            }

            this.notification.add(
                res.message || 'Record no longer exists. Skipping to the next record.',
                { type: 'warning' }
            );

            // Advance to the next record index, wrapping safely at the end.
            const nextIndex = this.state.currentIndex + 1;
            if (nextIndex < totalRecords) {
                this.state.currentIndex = nextIndex;
                await this._loadRealReport(this.state.records[nextIndex], _retryCount + 1);
            } else {
                // We were on the last record — no further records to try.
                this.notification.add(
                    'No more valid records to preview.',
                    { type: 'warning' }
                );
            }
        }
        // For any other backend error, do nothing — leave the iframe as-is.
    }

    onIframeLoad(evt) {
        try {
            const iframe = evt.target;
            const doc = iframe.contentDocument || iframe.contentWindow.document;
            if (!doc || !doc.head) return;
            const style = doc.createElement('style');

            this._setupIframeAutoResize(iframe);

            // ── Detect errors inside the report iframe ───────────────────────
            const bodyText = doc.body ? (doc.body.textContent || '') : '';
            const isRecordMissing = (
                bodyText.includes('Record does not exist or has been deleted') ||
                bodyText.includes('MissingError')
            );
            const isRenderError = (
                doc.title === '500: Internal Server Error' ||
                !!doc.querySelector('.oe_error_box') ||
                bodyText.includes('Error while render the template')
            );

            if (isRecordMissing && this.state.previewMode) {
                // The record rendered inside the iframe no longer exists in the DB.
                // Instead of showing the "Oops!" traceback, skip transparently to the
                // next record in the pager. _loadRealReport handles the retry cap.
                this.notification.add(
                    'Record no longer exists in the database. Skipping to the next record.',
                    { type: 'warning' }
                );
                const nextIndex = this.state.currentIndex + 1;
                if (nextIndex < (this.state.records || []).length) {
                    this.state.currentIndex = nextIndex;
                    this._loadRealReport(this.state.records[nextIndex]);
                } else {
                    this.notification.add('No more valid records to preview.', { type: 'warning' });
                }
                return;
            }

            if (isRenderError) {
                const errMsg = doc.querySelector('.oe_error_box pre')
                    ? doc.querySelector('.oe_error_box pre').textContent
                    : 'Report Rendering Failed due to corrupted XML.';
                this.env.services.notification.add('Preview Failed: ' + errMsg, { type: 'danger', sticky: true });
                // Revert to edit mode
                this.togglePreview();
                return;
            }

            // Check if a cy-custom-footer is present in the rendered report
            const hasCustomFooter = !!(doc.querySelector('.cy-custom-footer'));

            style.textContent = `
                /* Cyllo Studio: left-align footer text in preview */
                .footer .text-center,
                .o_standard_footer .text-center,
                .o_footer_content .text-center {
                    text-align: left !important;
                }
                ${hasCustomFooter ? `
                /* Hide default standard footer when Cyllo custom footer is present */
                .footer.o_standard_footer,
                .o_standard_footer,
                footer.footer {
                    display: none !important;
                }
                /* Pin custom footer to the bottom of the HTML preview window */
                .cy-custom-footer {
                    position: fixed !important;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    background: white;
                    z-index: 1000;
                    box-shadow: 0 -1px 3px rgba(0,0,0,0.1);
                }
                /* Add padding so content doesn't hide behind the fixed footer */
                body {
                    padding-bottom: 80px !important;
                }
                ` : ''}
            `;
            doc.head.appendChild(style);

            doc.querySelectorAll('a[href]').forEach((a) => {
                a.setAttribute('target', '_blank');
                a.setAttribute('rel', 'noopener noreferrer');
            });
        } catch (e) {
            console.warn('[Cyllo Studio] Could not inject iframe CSS:', e);
        }
    }

    _setupIframeAutoResize(iframe) {
        if (!iframe || !iframe.contentDocument) return;
        const doc = iframe.contentDocument;

        // Force hide scrollbars on the iframe document so it doesn't create dual scrolling
        doc.documentElement.style.setProperty('overflow', 'hidden', 'important');
        doc.body.style.setProperty('overflow', 'hidden', 'important');
        // Ensure body height is auto so it shrinks when content shrinks
        doc.body.style.setProperty('height', 'auto', 'important');

        const resize = () => {
            if (this._isDragging) return; // Suppress iframe resize during drag to prevent drop sync drift
            if (!iframe.contentDocument) return;
            const b = iframe.contentDocument.body;
            const h = iframe.contentDocument.documentElement;
            if (b && h) {
                // Prevent scroll jumping when temporarily resetting height
                const parentScroll = iframe.closest('.cy-canvas-area');
                const scrollTop = parentScroll ? parentScroll.scrollTop : 0;

                // Temporarily remove height to let scrollHeight shrink to true content size
                iframe.style.height = '0px';

                // Determine the true scroll height of the internal document
                let targetHeight = Math.max(b.scrollHeight, h.scrollHeight);

                iframe.style.height = targetHeight + 'px';

                // Restore scroll position
                if (parentScroll) parentScroll.scrollTop = scrollTop;
            }
        };

        const ro = new ResizeObserver(() => {
            requestAnimationFrame(resize);
        });
        ro.observe(doc.body);

        const mo = new MutationObserver(() => {
            requestAnimationFrame(resize);
        });
        mo.observe(doc.body, { childList: true, subtree: true, characterData: true, attributes: true });

        // Disconnect observer if iframe unloads
        iframe.contentWindow.addEventListener('unload', () => {
            ro.disconnect();
            mo.disconnect();
        }, { once: true });

        // Initial resize
        setTimeout(resize, 50);
    }

    onPrevRecord() {
        if (this.state.currentIndex > 0) {
            this.state.currentIndex--;
            this._loadRealReport(this.state.records[this.state.currentIndex]);
        }
    }

    onNextRecord() {
        if (this.state.currentIndex < this.state.records.length - 1) {
            this.state.currentIndex++;
            this._loadRealReport(this.state.records[this.state.currentIndex]);
        }
    }

    async onReportPropertyChange(field, value) {
        if (field === "paperformat_id") {
            value = value ? parseInt(value) : false;
        }

        this.state.reportInfo[field] = value;

        await this.orm.write(
            "ir.actions.report",
            [this.state.reportInfo.id],
            { [field]: value }
        );

        if (this.state.previewMode) {
            await this._fetchPreviewData();
        }
        else {
            // Paper format changed — update the editable canvas dimensions immediately.
            requestAnimationFrame(() => this._applyPaperFormatToCanvas());
        }
    }

    async onEditSources() {
        this.state.showSourceEditor = !this.state.showSourceEditor;
        if (this.state.showSourceEditor) {
            // ── SYNC PENDING CHANGES ─────────────────────────────────────────
            // If there's an active undo stack or modified nodes, we should
            // save before fetching the source so that the 'combined' arch
            // returned by the backend includes current DnD changes.
            const hasChanges = $('.c_new').length > 0 || (this.undoManager && this.undoManager.canUndo());
            if (hasChanges && this.reportFrameRef.el) {
                await this.save_changes(this);
            }

            const res = await this.rpc('/cyllo_studio/get_report_source', {
                template: this._template,
            });
            if (res.success) {
                this.state.sourceCode = res.arch;
                // Store the resolved document template name so we save to the right view
                this._docTemplate = res.doc_template || this._template;
                // Store the record loop variable ("doc", "o", etc.) for QR/field expressions
                this._recordVar = res.record_var || 'doc';
                this._recordBased = res.record_based;
                this._initAceEditor();
            } else {
                this.notification.add(res.error, { type: "danger" });
                this.state.showSourceEditor = false;
            }
        }
    }

    _initAceEditor() {
        setTimeout(() => {
            const editorEl = this.aceEditorRef.el;
            if (editorEl && window.ace) {
                const code = this.state.sourceCode || "<!-- No source code found -->";

                if (this.aceEditor) {
                    if (this.aceEditor.container === editorEl) {
                        // The DOM element is the same (e.g. toggling preview mode). Safely update/resize.
                        if (this.aceEditor.getValue() !== code) {
                            this.aceEditor.setValue(code, -1);
                        }
                        this.aceEditor.resize(true);
                        return;
                    } else {
                        // The editor was unmounted and remounted (e.g. closed and reopened).
                        // The old Ace instance is bound to a dead DOM node.
                        this.aceEditor.destroy();
                        this.aceEditor = null;
                    }
                }

                this.aceEditor = ace.edit(editorEl);
                this.aceEditor.setTheme("ace/theme/monokai");
                this.aceEditor.session.setMode("ace/mode/xml");
                this.aceEditor.setValue(code, -1);

                this.aceEditor.on('change', () => {
                    this.state.sourceCode = this.aceEditor.getValue();
                });
            } else {
                console.error("[EditSources] Could not initialize Ace. Element:", !!editorEl, "Lib:", !!window.ace);
                if (!window.ace) {
                    this.notification.add("Ace library not loaded yet", { type: "warning" });
                }
            }
        }, 500);
    }

    async onSaveSource() {
        const confirmed = await new Promise((resolve) => {
            this.dialog.add(ConfirmationDialog, {
                title: "Save Source Changes",
                body: "Saving source code will overwrite any unsaved visual canvas changes. Are you sure you want to continue?",
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            });
        });
        if (!confirmed) return;
        const res = await this.rpc('/cyllo_studio/save_report_source', {
            template: this._template,
            doc_template: this._docTemplate || this._template,
            arch: this.state.sourceCode,
        });
        if (res.success) {
            this.notification.add("Source saved successfully", { type: "success" });

            // ── LIVE SYNC: Source -> UI ──────────────────────────────────────
            // Immediately re-fetch the arch and update the visual report frame
            // so the user sees their XML edits without a page reload.
            const result = await this.rpc('/cyllo_studio/get_arch', { template: this._template });
            if (result && result.success) {
                this._loadedArch = result.arch;
                if (!this.state.previewMode) {
                    // Force iframe to reload
                    if (this.reportFrameRef.el && this.reportFrameRef.el.tagName === 'IFRAME') {
                        this.reportFrameRef.el.contentWindow.location.reload();
                    }
                    this._setupSortable();
                } else {
                    await this._fetchPreviewData();
                }
            }
        } else {
            this.notification.add(res.error, { type: "danger" });
        }
    }

    async _savePendingDesignIfMounted() {
        const hasChanges = $('.c_new').length > 0 || (this.undoManager && this.undoManager.canUndo());
        if (hasChanges && this.reportFrameRef.el) {
            await this.save_changes(this);
        }
    }

    async saveReportFromActions() {
        this.state.showActionsMenu = false;
        if (!this.reportFrameRef.el) {
            this.notification.add("Switch off Preview before saving report layout changes.", { type: "warning" });
            return;
        }
        await this.save_changes(this);
    }

    openSaveTemplateDialog() {
        this.state.showActionsMenu = false;
        this.state.templateForm = {
            name: this.state.reportInfo.name ? `${this.state.reportInfo.name} Template` : "",
            description: "",
            category: "",
        };
        this.state.showTemplateDialog = true;
    }

    closeSaveTemplateDialog() {
        this.state.showTemplateDialog = false;
    }

    async saveAsTemplate() {
        const form = this.state.templateForm;
        if (!form.name || !form.name.trim()) {
            this.notification.add("Template Name is required.", { type: "warning" });
            return;
        }

        try {
            await this._savePendingDesignIfMounted();
            this.state.isSaving = true;
            const res = await this.rpc('/cyllo_studio/save_report_template', {
                template: this._template,
                name: form.name,
                description: form.description,
                category: form.category,
            });
            if (res.success) {
                this.state.showTemplateDialog = false;
                this.notification.add("Template saved successfully.", { type: "success" });
            } else {
                this.notification.add(res.error || "Template save failed.", { type: "danger" });
            }
        } finally {
            this.state.isSaving = false;
        }
    }

    async exportTemplate() {
        this.state.showActionsMenu = false;
        try {
            await this._savePendingDesignIfMounted();
            this.state.isSaving = true;
            const res = await this.rpc('/cyllo_studio/export_report_template', {
                template: this._template,
            });
            if (!res.success) {
                this.notification.add(res.error || "Template export failed.", { type: "danger" });
                return;
            }
            const blob = new Blob([JSON.stringify(res.payload, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = res.filename || "report_template.json";
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
        } finally {
            this.state.isSaving = false;
        }
    }

    onResetReport() {
        // Show the confirmation dialog
        this.state.showResetDialog = true;
    }

    async confirmResetReport() {
        this.state.showResetDialog = false;
        const res = await this.rpc('/cyllo_studio/reset_report_source', {
            template: this._template,
            include_header_footer: this.state.includeHeaderFooter,
        });
        if (res.success) {
            this.notification.add("Report reset to factory settings", { type: "success" });
            // If source editor is open, refresh it with the reset arch
            if (this.state.showSourceEditor && res.arch) {
                this.state.sourceCode = res.arch;
                if (this.aceEditor) {
                    this.aceEditor.setValue(res.arch, -1);
                }
            }
            // Reload the editor preview
            const result = await this.rpc('/cyllo_studio/get_arch', { template: this._template });
            if (result && result.success) {
                this._loadedArch = result.arch;
                if (!this.state.previewMode) {
                    if (this.reportFrameRef.el && this.reportFrameRef.el.tagName === 'IFRAME') {
                        this.reportFrameRef.el.contentWindow.location.reload();
                    }
                    this._setupSortable();
                } else {
                    await this._fetchPreviewData();
                }
            }
        } else {
            this.notification.add(res.error || "Reset failed", { type: "danger" });
        }
    }

    onPrintReport() {
        const report = this.state.reportInfo;
        const activeId = this.state.records[this.state.currentIndex];
        if (!report.id || !activeId) return;

        this.action.doAction({
            type: 'ir.actions.report',
            report_name: report.report_name,
            report_type: 'qweb-pdf',
            res_model: report.model,
            context: {
                active_ids: [activeId],
                active_id: activeId,
                active_model: report.model,
                report_pdf_no_attachment: true,
                cyllo_studio_pdf: true,
            }
        });
    }

    async onSignReport() {
        const report = this.state.reportInfo;
        const activeId = this.state.records[this.state.currentIndex];
        if (!report.id || !activeId) return;

        this.state.isSaving = true;
        try {
            // First save to ensure the node is persisted
            await this.save_changes(this);

            try {
                // Call the universal backend action
                const action = await this.orm.call(
                    'ir.actions.report',
                    'action_send_for_signature',
                    [[report.id], [activeId]]
                );

                if (action) {
                    this.action.doAction(action);
                }
            } catch (err) {
                if (err && err.message && (err.message.includes('AttributeError') || err.message.includes('action_send_for_signature'))) {
                    this.notification.add(
                        "The 'Sign' module is required to use this feature. Please install the 'cyllo_sign' module.",
                        { type: "warning", sticky: true }
                    );
                } else {
                    throw err;
                }
            }
        } finally {
            this.state.isSaving = false;
        }
    }


    onOpenFullAnalytics() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'QR Scan Analytics',
            res_model: 'qr.scan.event',
            view_mode: 'tree,form,pivot,graph',
            views: [[false, 'tree'], [false, 'form'], [false, 'pivot'], [false, 'graph']],
            domain: [['report_id', '=', this.state.reportInfo.id]],
            target: 'current',
        });
    }

    _updateHasSign(arch = null) {
        const targetArch = arch || this._loadedArch || '';
        // Check in arch string
        const hasSignInArch = /cy-type=['"]sign['"]|o_sign_placeholder|sign-wrapper|\[\[SIGN:/.test(targetArch);
        // Check in live DOM
        const rootEl = this.reportFrameRef.el?.tagName === 'IFRAME' ? this.reportFrameRef.el.contentDocument : this.reportFrameRef.el;
        const signEls = rootEl?.querySelectorAll('.sign-wrapper, [cy-type="sign"], .o_sign_placeholder');
        const hasSignInDom = signEls && signEls.length > 0;
        this.state.hasSign = hasSignInArch || hasSignInDom;
    }

    _updateHasQr(arch = null) {
        const targetArch = arch || this._loadedArch || '';
        const qrRegex = /cy-type=['"]qr['"]|s_qr_block|symbology['"]\s*:\s*['"]QR['"]|['"]QR['"]\s*:\s*symbology/;
        const hasQrInArch = qrRegex.test(targetArch);

        const rootEl = this.reportFrameRef.el?.tagName === 'IFRAME' ? this.reportFrameRef.el.contentDocument : this.reportFrameRef.el;
        // Check for Studio-managed QR blocks
        const qrBlocks = rootEl?.querySelectorAll('.s_qr_block, [cy-type="qr"]');
        const hasQrInDom = qrBlocks && qrBlocks.length > 0;

        const rawBarcodes = rootEl?.querySelectorAll('img[src*="barcode"][src*="QR"], img[src*="barcode"][src*="qr"], svg[data-code-type="QR"]');
        const hasRawQrInDom = rawBarcodes && rawBarcodes.length > 0;

        if (hasQrInDom) {
            let tracked = false;
            qrBlocks.forEach(el => {
                try {
                    const cfg = JSON.parse(el.dataset.qrConfig || '{}');
                    // Assume tracked unless explicitly disabled in config
                    if (cfg.config && cfg.config.trackAnalytics !== false) tracked = true;
                } catch (e) { }
            });
            this.state.hasQr = tracked;
        } else if (hasRawQrInDom) {
            // If we see a raw QR barcode in the DOM, show analytics if tracking was ever enabled for this report
            this.state.hasQr = !!(this.state.analytics && this.state.analytics.tracking_enabled);
        } else {
            // If no QR is rendered in the current view, hide the analytics panel.
            this.state.hasQr = false;
        }

    }

    get currentPaperFormat() {
        if (!this.state.reportInfo.paperformat_id) return null;
        const format = this.state.paperFormats.find(f => f.id === this.state.reportInfo.paperformat_id);
        if (format) {
            let width = format.page_width;
            let height = format.page_height;
            if ((!width || !height) && PAPER_FORMAT_MAP[format.format]) {
                [width, height] = PAPER_FORMAT_MAP[format.format];
            }
            return { ...format, page_width: width || 210, page_height: height || 297 };
        }
        return null;
    }

    get paperFormatOptions() {
        if (!this.state.paperFormats) return [];
        return this.state.paperFormats.map(fmt => ({
            value: fmt.id,
            label: fmt.name
        }));
    }

    _getPaperDimensions() {
        const fmt = this.currentPaperFormat;
        return {
            width: fmt ? fmt.page_width : 210,
            height: fmt ? fmt.page_height : 297,
        };
    }

    _applyPaperFormatToCanvas() {
        // Guard: only run in edit mode — in preview the edit iframe is unmounted
        if (this.state.previewMode) return;
        const iframeEl = this.reportFrameRef.el;
        if (!iframeEl) return;
        const container = iframeEl.closest('.cyllo-studio-report-container');
        if (!container) return;

        const { width, height } = this._getPaperDimensions();
        const canvasArea = container.closest('.cy-canvas-area');
        const editableArea = iframeEl.tagName === 'IFRAME' ? iframeEl.contentDocument?.body : iframeEl;

        if (canvasArea) {
            canvasArea.style.padding = '40px';
            canvasArea.style.maxHeight = '';
            canvasArea.style.overflowY = 'auto';
            canvasArea.style.overflowX = 'auto';
        }

        // Size the container width to paper width, let height grow with header
        container.style.height = 'auto';
        container.style.width = `${width}mm`;
        container.style.minHeight = 'auto';
        container.style.overflow = 'visible';
        container.style.setProperty('--cy-page-height', `${height}mm`);

        // Size the iframe width to match the container exactly.
        iframeEl.style.width = '100%';
        iframeEl.style.maxWidth = '100%';
        iframeEl.style.minHeight = 'auto'; // Let it shrink to fit content
        iframeEl.style.border = 'none';
        iframeEl.style.backgroundColor = 'white';
        iframeEl.style.display = 'block';

        if (editableArea) {
            const pageElements = editableArea.querySelectorAll('.page');
            pageElements.forEach(page => {
                page.style.boxSizing = 'border-box';
                page.style.minHeight = `${height}mm`;
                page.style.height = `${height}mm`;
                // page.style.width = `${width}mm`;
                page.style.overflow = 'hidden';
            });
        }

        container.querySelector('.cy-page-overflow-line')?.remove();
        container.parentElement?.querySelector('.cy-overflow-warning')?.remove();
        if (editableArea) {
            editableArea.querySelectorAll('.cy-overflowing').forEach(el => el.classList.remove('cy-overflowing'));
        }
        this.state.hasOverflow = false;
    }


    //    async onReportPropertyChange(field, value) {
    //        this.state.reportInfo[field] = value;
    //        await this.rpc("/web/dataset/call_kw/ir.actions.report/write", {
    //            model: "ir.actions.report",
    //            method: "write",
    //            args: [[this.state.reportInfo.id], { [field]: value }],
    //            kwargs: {},
    //        });
    //    }

    undo() { this.undoManager?.undo(); }
    redo() { this.undoManager?.redo(); }

    showBranchSelector(element) {
        this.currentGroup = this.findConditionalGroup(element);
        let optionsHtml = '';
        this.currentGroup?.forEach((branch, index) => {
            let type = branch.getAttribute('t-if') ? 't-if' :
                branch.getAttribute('t-elif') ? 't-elif' : 't-else';
            let condition = branch.getAttribute(type) || '(else)';
            let isActive = $(branch).is(':visible');
            optionsHtml += `
                <div class="branch-option ${isActive ? 'active' : ''}" data-index="${index}">
                    <span class="branch-type">${type}</span>
                    <span class="branch-condition">${condition}</span>
                </div>`;
        });
        $('#branchOptions').html(optionsHtml);
        $('#branchSelector').fadeIn(200);
        const self = this;
        $('.branch-option').on('click', function () {
            const index = $(this).closest('[data-index]').data('index');
            self.switchToBranch(index);
        });
    }

    findConditionalGroup(element) {
        let group = [];
        let current = element;
        while (current && !current.hasAttribute('t-if')) {
            if (!current.hasAttribute('t-elif') && !current.hasAttribute('t-else')) break;
            current = current.previousElementSibling;
        }
        if (!current) return null;
        group.push(current);
        let next = current.nextElementSibling;
        while (next && (next.hasAttribute('t-elif') || next.hasAttribute('t-else'))) {
            group.push(next);
            if (next.hasAttribute('t-else')) break;
            next = next.nextElementSibling;
        }
        return group;
    }

    switchToBranch(index) {
        if (!this.currentGroup[index]) return;
        this.currentGroup.forEach(branch => $(branch).hide());
        $(this.currentGroup[index]).show().addClass('selected');
        $('.branch-option').removeClass('active');
        $(`[data-index="${index}"]`).addClass('active');
    }

    async closeBranchSelector() {
        $('#branchSelector').fadeOut(200);
        $('#branchOptions').html('');
        $('.selected').removeClass('selected');
        this.currentGroup = [];
    }

    // ─────────────────────────────────────────────────────────────────────────
    // SortableJS drag-and-drop
    // ─────────────────────────────────────────────────────────────────────────

    _setupSortable() {
        this._snippetPanel = document.querySelector('#snippet-panel .cy-report-section');
        this._reportFrame = this.reportFrameRef.el?.contentDocument?.body;
        if (!this._reportFrame || !this._snippetPanel) return;

        // Destroy any previous instances before reinitialising
        this._destroySortableInstances();

        // ── 1. Native SortableJS Sidebar ───────────────────
        this._setupPanelSortable();

        // ── 2. Block-level [cy-template] containers become drop zones ──
        // Only DIV containers are valid drop zones. The server tags ~every node
        // (span/strong/td/p/t...) with cy-template; turning each into a nested
        // Sortable created dozens of overlapping zones that fought over the
        // insertion point on every mousemove, making the drop marker jump around
        // the sheet. Fields inside inline nodes stay draggable and still drop
        // correctly because their parent DIV is the zone.
        this._reportFrame.querySelectorAll('[cy-template]').forEach(zone => {
            if (zone.tagName !== 'DIV') return;
            this._createZoneSortable(zone);
        });
    }

    _setupPanelSortable() {
        const self = this;
        const panel = this._snippetPanel;
        if (!panel) return;

        const instance = Sortable.create(panel, {
            group: {
                name: 'studio',
                pull: 'clone',
                put: false,
            },
            sort: false,
            animation: 150,
            draggable: '.cy-node-card',
            filter: 'input, textarea, button, .cy-switch-wrap, .cy-slider',
            preventOnFilter: false,
            forceFallback: false, // Ensure native HTML5 Drag and Drop is used
            onStart() {
                self._isDragging = true;
                if (self.editor) { self.editor.destroy(); self.editor = null; }
            },
            onEnd() {
                self._isDragging = false;
                if (self._pendingSortableRebuild) {
                    self._pendingSortableRebuild = false;
                    setTimeout(() => self._setupSortable(), 0);
                }
            }
        });
        this._sortableInstances.push(instance);
    }

    /**
     * Build the inner HTML string for a box section wrapper.
     */
    _buildBoxInnerHTML(cfg) {
        const layoutMode = cfg.layoutMode || 'free';
        const label = cfg.label || 'Section';
        return `
            <div class="box-toolbar" contenteditable="false">
                <span class="box-drag-handle ri-drag-move-line" title="Drag to move"></span>
                <span class="box-settings-btn ri-settings-3-line" title="Settings" style="cursor: pointer; margin: 0 4px;"></span>
                <span class="box-label-text">${escapeHtml(label)}</span>
                <span class="box-layout-badge">${layoutMode}</span>
                <span class="box-delete-btn ri-delete-bin-line" title="Delete Section"></span>
            </div>
            <div class="box-dropzone layout-${layoutMode}"></div>
            <div class="box-resize-handles" contenteditable="false">
                <div class="box-resize-handle nw" data-dir="nw"></div>
                <div class="box-resize-handle n"  data-dir="n"></div>
                <div class="box-resize-handle ne" data-dir="ne"></div>
                <div class="box-resize-handle e"  data-dir="e"></div>
                <div class="box-resize-handle se" data-dir="se"></div>
                <div class="box-resize-handle s"  data-dir="s"></div>
                <div class="box-resize-handle sw" data-dir="sw"></div>
                <div class="box-resize-handle w"  data-dir="w"></div>
            </div>`;
    }

    /**
     * Create a SortableJS instance for a box inner drop zone.
     * Accepts all element types and stops propagation so the parent canvas
     * does not also receive the drop.
     */
    _createBoxDropzoneSortable(dropzone) {
        const self = this;
        const instance = Sortable.create(dropzone, {
            group: { name: 'studio_box', pull: true, put: ['studio', 'studio_zone', 'studio_box'] },
            animation: 150,
            direction: 'vertical',
            swapThreshold: 0.65,
            emptyInsertThreshold: 8,
            draggable: '.table-wrapper, .box-section-wrapper, .dynamic-field-wrapper, .field-block, .text-node, .s_qr_block, [cy-type="dynamic"]:not(.dynamic-field-wrapper *), [cy-type="qr"], [cy-type="sign"]',
            handle: '.table-handle, .box-drag-handle, .box-toolbar, .field-handle, .dynamic-field-wrapper, .field-block, .text-node, .s_qr_block, [cy-type="qr"], .sign-toolbar',
            onMove: function (evt, originalEvent) {
                const draggedItem = evt.dragged;
                const targetList = evt.to;
                if (draggedItem.classList.contains('snippet')) return true;

                const draggedTemplate = draggedItem.getAttribute('cy-template') || (draggedItem.closest('[cy-template]') ? draggedItem.closest('[cy-template]').getAttribute('cy-template') : null);
                const targetTemplate = targetList.closest('[cy-template]') ? targetList.closest('[cy-template]').getAttribute('cy-template') : null;

                if (draggedTemplate && targetTemplate && draggedTemplate !== targetTemplate) {
                    if (!self._dragWarningShown) {
                        self.notification.add("Cannot move elements across different template boundaries.", { type: "warning" });
                        self._dragWarningShown = true;
                        setTimeout(() => { self._dragWarningShown = false; }, 2000);
                    }
                    return false;
                }
                return true;
            },
            onStart() {
                self._isDragging = true;
                if (self.editor) { self.editor.destroy(); self.editor = null; }
                $('.selected').removeClass('selected');
            },
            onEnd() {
                self._isDragging = false;
                if (self._pendingSortableRebuild) {
                    self._pendingSortableRebuild = false;
                    setTimeout(() => self._setupSortable(), 0);
                }
            },
            async onAdd(evt) {
                evt.originalEvent && evt.originalEvent.stopPropagation && evt.originalEvent.stopPropagation();
                const item = evt.item;
                const fromPanel = evt.from === self._snippetPanel;
                if (!fromPanel) return;

                const type = item.dataset.type;
                item.style.opacity = '0.7';
                item.classList.add('awaiting-config-block');

                if (type === 'text') {
                    // Transform dropped snippet into an immediately-editable text node
                    item.className = 'text-node c_new selected';
                    item.setAttribute('contenteditable', 'true');
                    item.innerHTML = 'Click to edit';
                    item.style.opacity = '1';

                    // Destroy any existing editor first
                    if (self.editor) {
                        try { self.editor.destroy(); } catch (_) { }
                        self.editor = null;
                    }

                    // Init MediumEditor immediately so the node is ready to type into
                    setTimeout(() => {
                        const ifrWin1 = self.reportFrameRef.el?.contentWindow;
                        const ME1 = (ifrWin1 && ifrWin1.MediumEditor) || MediumEditor;
                        const SB1 = (ifrWin1 && ifrWin1.SettingsButton) || window.SettingsButton;
                        const DB1 = (ifrWin1 && ifrWin1.DeleteButton) || window.DeleteButton;
                        const UB1 = (ifrWin1 && ifrWin1.UndoButton) || window.UndoButton;
                        const RB1 = (ifrWin1 && ifrWin1.RedoButton) || window.RedoButton;
                        self.editor = new ME1(item, {
                            ownerDocument: self.reportFrameRef.el?.contentDocument,
                            elementsContainer: self.reportFrameRef.el?.contentDocument?.body,
                            toolbar: {
                                buttons: [
                                    'bold', 'italic', 'underline', 'strikethrough',
                                    'h1', 'h3', 'quote', 'anchor', 'deleteElement', 'settingsButton',
                                ],
                            },
                            extensions: {
                                'settingsButton': SB1 ? new SB1() : null,
                                'deleteElement': DB1 ? new DB1() : null,
                                'undoButton': UB1 ? new UB1() : null,
                                'redoButton': RB1 ? new RB1() : null,
                            },
                            owner: self,
                            placeholder: false,
                            disableExtraSpaces: true,
                        });
                        self.editor.selectElement(item);
                        item.focus();
                    }, 0);

                    self._refreshDragHandles();
                    return;
                }

                if (type === 'field') {
                    if (!self._canBindDynamicField()) { item.remove(); return; }
                    const resModel = self._resModel || '';
                    const { fieldPath, fieldInfo } = await self.openFieldSelectorPopover(dropzone, resModel, (f) => !['one2many', 'many2many'].includes(f.type));
                    if (!fieldPath) { item.remove(); return; }
                    item.className = 'field-block c_new dynamic-field-wrapper';
                    item.innerHTML = `
                        <div class="field-handle-container" contenteditable="false">
                            <span class="field-handle ri-drag-move-line" title="Drag to move"></span>
                            <span class="field-settings ri-settings-3-line" title="Settings" style="cursor: pointer; margin: 0 4px;"></span>
                            <span class="field-delete ri-delete-bin-line" title="Delete Field"></span>
                        </div>
                        <div class="field-container">
                            <strong class="field-label" style="margin-right: 4px;">${escapeHtml(fieldInfo.string)}: </strong>
                            ${fieldInfo.type === 'binary' ? `<img t-if="${self._recordVar}.${fieldPath}" src="/web/static/src/img/mimetypes/image.svg" t-att-src="${self._recordVar}.env['ir.actions.report'].get_safe_image_data_uri(${self._recordVar}.${fieldPath})" style="max-width: 100%; width: 200px; height: auto; object-fit: contain;" title="${escapeHtml(fieldInfo.string)}" />` : `<span t-field="${self._recordVar}.${fieldPath}" title="${escapeHtml(fieldInfo.string)}">${fieldPath}</span>`}
                        </div>`;
                    item.setAttribute('cy-type', 'dynamic');
                    item.style.opacity = '1';
                    item.querySelector('.field-delete').onclick = (e) => {
                        e.stopPropagation();
                        self.dialog.add(ConfirmationDialog, {
                            body: "Are you sure you want to delete this field?",
                            confirm: () => item.remove(),
                            cancel: () => { },
                        });
                        // if (confirm('Delete this field?')) item.remove();
                    };
                }

                if (type === 'box') {
                    const boxId = 'box_' + Math.random().toString(36).slice(2, 10);
                    const cfg = { id: boxId, label: 'Section', style: { width: 280, height: 160, backgroundColor: 'transparent', border: '1px solid #ccc', borderRadius: 4, padding: 8, marginTop: 16 }, layoutMode: 'free', children: [] };
                    item.className = 'box-section-wrapper c_new';
                    item.setAttribute('cy-type', 'box');
                    item.setAttribute('data-box-id', boxId);
                    item.setAttribute('data-box-config', JSON.stringify(cfg));
                    item.style.width = cfg.style.width + 'px';
                    item.style.height = cfg.style.height + 'px';
                    item.style.marginTop = cfg.style.marginTop + 'px';
                    item.style.opacity = '1';
                    item.innerHTML = self._buildBoxInnerHTML(cfg);
                    item.querySelector('.box-delete-btn').onclick = (e) => {
                        e.stopPropagation();
                        self.dialog.add(ConfirmationDialog, { body: 'Delete this section?', confirm: () => item.remove(), cancel: () => { } });
                    };
                    self._setupBoxResizeHandles(item);
                    const inner = item.querySelector('.box-dropzone');
                    if (inner) self._createBoxDropzoneSortable(inner);
                }

                if (type === 'table') {
                    const resModel = self._resModel || '';
                    const config = await self.openTableConfigModal(dropzone, resModel);
                    if (!config) { item.remove(); return; }
                    const tableHtml = self._generateTableHtml(config);
                    item.className = 'c_new table-wrapper';
                    item.innerHTML = `
                        <div class="table-handle-container" contenteditable="false">
                            <div class="table-handle ri-drag-move-line" title="Drag to move"></div>
                            <div class="table-settings ri-settings-3-line" title="Settings" ></div>
                            <div class="table-delete ri-delete-bin-line" title="Delete Table"></div>
                        </div>
                        ${tableHtml}`;
                    item.setAttribute('cy-type', 'table');
                    item.setAttribute('cy-config', JSON.stringify(config));
                    item.style.opacity = '1';
                    item.querySelector('.table-delete').onclick = (e) => {
                        e.stopPropagation();
                        self.dialog.add(ConfirmationDialog, { body: 'Delete this table?', confirm: () => item.remove(), cancel: () => { } });
                    };
                }

                if (type === 'qr') {
                    const config = await self.openQrWizard(item);
                    if (!config) { item.remove(); return; }
                    self.insertQrBlock(item, config);
                }

                if (type === 'sign') {
                    const signId = 'sign_' + Math.random().toString(36).slice(2, 10);
                    const defaultCfg = {
                        role: 'customer',
                        label: 'Authorized Signature',
                        required: true,
                        show_date: false,
                        show_name: false,
                        width: 200,
                        height: 100,
                        alignment: 'left',
                    };
                    item.className = 'sign-wrapper c_new';
                    item.setAttribute('cy-type', 'sign');
                    item.setAttribute('data-sign-id', signId);
                    item.setAttribute('data-sign-config', JSON.stringify(defaultCfg));
                    item.dataset.role = defaultCfg.role;
                    item.style.width = defaultCfg.width + 'px';
                    item.style.height = defaultCfg.height + 'px';
                    item.style.opacity = '1';
                    item.style.cursor = 'default';
                    item.style.textAlign = defaultCfg.alignment;

                    item.innerHTML = `
                        <div class="sign-toolbar" contenteditable="false">
                            <span class="sign-drag-handle ri-drag-move-line" title="Drag to move"></span>
                            <span class="sign-settings-btn ri-settings-3-line" title="Settings" style="cursor: pointer; margin: 0 4px;"></span>
                            <span class="sign-delete-btn ri-delete-bin-line" title="Delete Signature"></span>
                        </div>
                        <div class="sign-content-wrapper" style="pointer-events: none; border: 2px dashed #ccc; width: 100%; height: 100%; padding: 10px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; position: relative;">
                            <div class="sign-watermark" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); opacity: 0.1; font-size: 40px; color: #9ea700;"><i class="fa fa-pencil"></i></div>
                            <div class="sign-role-badge" style="position: absolute; top: -10px; right: 10px; background: #9ea700; color: white; padding: 2px 6px; font-size: 10px; border-radius: 4px; text-transform: uppercase;">${escapeHtml(defaultCfg.role)}</div>
                            <div class="sign-empty-line" style="border-bottom: 1px solid #333; width: 80%; margin: 10px auto;"></div>
                            <p class="sign-label" style="font-weight: bold; font-size: 14px; margin: 0;">${escapeHtml(defaultCfg.label)}</p>
                        </div>
                        <div class="sign-resize-handles" contenteditable="false">
                            <div class="sign-resize-handle" data-dir="se"></div>
                        </div>
                    `;

                    item.querySelector('.sign-delete-btn').onclick = (e) => {
                        e.stopPropagation();
                        self.dialog.add(ConfirmationDialog, {
                            body: 'Delete this Signature?',
                            confirm: () => {
                                if (self.state.showSignProps && self._selectedSignEl === item) {
                                    self.closeSignProps();
                                }
                                item.remove();
                                self._updateHasSign();
                            },
                            cancel: () => { },
                        });
                    };

                    self._setupSignResizeHandles(item);
                    self._updateHasSign();
                }

                self._refreshDragHandles();
            }
        });
        this._sortableInstances.push(instance);
    }

    /** Create (or re-create) a SortableJS instance for a single drop zone. */
    _createZoneSortable(zone) {
        const self = this;

        const instance = Sortable.create(zone, {
            group: {
                name: 'studio_zone',
                pull: true,
                put: ['studio', 'studio_zone', 'studio_box'],
            },
            animation: 150,
            direction: 'vertical',       // report is a vertical stack — stops horizontal insertion ambiguity
            swapThreshold: 0.65,         // require deeper overlap before re-inserting → less flip-flop
            emptyInsertThreshold: 8,     // easier to drop into (near-)empty zones

            draggable: '.table-wrapper, .box-section-wrapper, .dynamic-field-wrapper, .field-block, .text-node, .s_qr_block, [cy-type="dynamic"]:not(.dynamic-field-wrapper *), [cy-type="qr"], [cy-type="sign"]',
            handle: '.table-handle, .box-drag-handle, .field-handle, .dynamic-field-wrapper, .field-block, .text-node, .s_qr_block, [cy-type="dynamic"], [cy-type="qr"], .sign-toolbar',
            onMove: function (evt, originalEvent) {
                const draggedItem = evt.dragged;
                const targetList = evt.to;
                if (draggedItem.classList.contains('snippet')) return true;

                const draggedTemplate = draggedItem.getAttribute('cy-template') || (draggedItem.closest('[cy-template]') ? draggedItem.closest('[cy-template]').getAttribute('cy-template') : null);
                const targetTemplate = targetList.closest('[cy-template]') ? targetList.closest('[cy-template]').getAttribute('cy-template') : null;

                if (draggedTemplate && targetTemplate && draggedTemplate !== targetTemplate) {
                    if (!self._dragWarningShown) {
                        self.notification.add("Cannot move elements across different template boundaries.", { type: "warning" });
                        self._dragWarningShown = true;
                        setTimeout(() => { self._dragWarningShown = false; }, 2000);
                    }
                    return false;
                }
                return true;
            },
            onStart() {
                self._isDragging = true;
                if (self.editor) {
                    self.editor.destroy();
                    self.editor = null;
                }
                $('.selected').removeClass('selected');
            },

            onEnd() {
                self._isDragging = false;
                if (self._pendingSortableRebuild) {
                    self._pendingSortableRebuild = false;
                    setTimeout(() => self._setupSortable(), 0);
                }
            },

            async onAdd(evt) {
                const item = evt.item;
                const fromPanel = evt.from === self._snippetPanel;

                if (!fromPanel) return;

                const type = item.dataset.type; // read BEFORE anything

                await self._handleNewDrop(item, type, zone);
            }
        });
        this._sortableInstances.push(instance);
    }

    async _handleNewDrop(item, type, zone) {
        const self = this;
        // hide or style while async runs
        item.style.opacity = '0.7';
        item.classList.add('awaiting-config-block');

        if (type === 'text') {
            // Transform dropped snippet into an immediately-editable text node
            item.className = 'text-node c_new selected';
            item.setAttribute('contenteditable', 'true');
            item.innerHTML = 'Click to edit';
            item.style.position = '';
            item.style.left = '';
            item.style.top = '';
            item.style.opacity = '1';

            // Destroy any existing editor first
            if (self.editor) {
                try { self.editor.destroy(); } catch (_) { }
                self.editor = null;
            }

            // Init MediumEditor immediately so the node is ready to type into
            setTimeout(() => {
                const ifrWin2 = self.reportFrameRef.el?.contentWindow;
                const ME2 = (ifrWin2 && ifrWin2.MediumEditor) || MediumEditor;
                const SB2 = (ifrWin2 && ifrWin2.SettingsButton) || window.SettingsButton;
                const DB2 = (ifrWin2 && ifrWin2.DeleteButton) || window.DeleteButton;
                const UB2 = (ifrWin2 && ifrWin2.UndoButton) || window.UndoButton;
                const RB2 = (ifrWin2 && ifrWin2.RedoButton) || window.RedoButton;
                self.editor = new ME2(item, {
                    ownerDocument: self.reportFrameRef.el?.contentDocument,
                    elementsContainer: self.reportFrameRef.el?.contentDocument?.body,
                    toolbar: {
                        buttons: [
                            'bold', 'italic', 'underline', 'strikethrough',
                            'h1', 'h3', 'quote', 'anchor', 'deleteElement', 'settingsButton',
                        ],
                    },
                    extensions: {
                        'settingsButton': SB2 ? new SB2() : null,
                        'deleteElement': DB2 ? new DB2() : null,
                        'undoButton': UB2 ? new UB2() : null,
                        'redoButton': RB2 ? new RB2() : null,
                    },
                    owner: self,
                    placeholder: false,
                    disableExtraSpaces: true,
                });
                self.editor.selectElement(item);
                item.focus();
            }, 0);

            self._refreshDragHandles();
            return;
        }

        if (type === 'field') {
            if (!self._canBindDynamicField()) { item.remove(); return; }
            const resModel = self._resModel || self.props.action.params?.res_model || '';

            const { fieldPath, fieldInfo } =
                await self.openFieldSelectorPopover(
                    zone,
                    resModel,
                    (field) => !['one2many', 'many2many'].includes(field.type),
                );

            if (!fieldPath) {
                item.remove(); // cancelled
                return;
            }

            // transform existing dropped node
            item.className = 'field-block c_new dynamic-field-wrapper';
            item.innerHTML = `
                        <div class="field-handle-container" contenteditable="false">
                            <span class="field-handle ri-drag-move-line" title="Drag to move"></span>
                            <span class="field-delete ri-delete-bin-line" title="Delete Field"></span>
                        </div>
                        <div class="field-container" style="display: inline-block;">
                            <strong class="field-label" style="margin-right: 4px;">${escapeHtml(fieldInfo.string)}: </strong>
                            ${fieldInfo.type === 'binary' ? `<img t-if="${self._recordVar}.${fieldPath}" src="/web/static/src/img/mimetypes/image.svg" t-att-src="${self._recordVar}.env['ir.actions.report'].get_safe_image_data_uri(${self._recordVar}.${fieldPath})" style="max-width: 100%; width: 200px; height: auto; object-fit: contain;" title="${escapeHtml(fieldInfo.string)}" />` : `<span t-field="${self._recordVar}.${fieldPath}" title="${escapeHtml(fieldInfo.string)}">${fieldPath}</span>`}
                        </div>`;
            item.setAttribute('cy-type', 'dynamic');
            item.style.cursor = 'default';
            item.style.opacity = '1';

            // Internal delete handler
            item.querySelector('.field-delete').onclick = (e) => {
                e.stopPropagation();
                self.dialog.add(ConfirmationDialog, {
                    body: "Are you sure you want to delete this Field?",
                    confirm: () => item.remove(),
                    cancel: () => { },
                });
                // if (confirm("Delete this field?")) item.remove();
            };
        }

        if (type === 'box') {
            const boxId = 'box_' + Math.random().toString(36).slice(2, 10);
            const defaultCfg = {
                id: boxId,
                label: 'Section',
                style: { width: 300, height: 200, backgroundColor: 'transparent', border: '1px solid #ccc', borderRadius: 4, padding: 8, marginTop: 16 },
                layoutMode: 'free',
                children: [],
            };
            item.className = 'box-section-wrapper c_new';
            item.setAttribute('cy-type', 'box');
            item.setAttribute('data-box-id', boxId);
            item.setAttribute('data-box-config', JSON.stringify(defaultCfg));
            item.style.width = defaultCfg.style.width + 'px';
            item.style.height = defaultCfg.style.height + 'px';
            item.style.marginTop = defaultCfg.style.marginTop + 'px';
            item.style.opacity = '1';
            item.style.cursor = 'default';
            item.innerHTML = self._buildBoxInnerHTML(defaultCfg);

            // Wire box toolbar delete
            item.querySelector('.box-delete-btn').onclick = (e) => {
                e.stopPropagation();
                self.dialog.add(ConfirmationDialog, {
                    body: 'Delete this section container and all its contents?',
                    confirm: () => {
                        if (self.state.showBoxProps && self._selectedBoxEl === item) {
                            self.closeBoxProps();
                        }
                        item.remove();
                    },
                    cancel: () => { },
                });
            };

            // Wire resize handles
            self._setupBoxResizeHandles(item);

            // Register inner dropzone as sortable zone
            const dropzone = item.querySelector('.box-dropzone');
            if (dropzone) {
                self._createBoxDropzoneSortable(dropzone);
            }
        }

        if (type === 'table') {
            const resModel = self._resModel || self.props.action.params?.res_model || '';
            const config = await self.openTableConfigModal(zone, resModel);

            if (!config) {
                item.remove();
                return;
            }

            // transform existing dropped node
            const tableHtml = self._generateTableHtml(config);
            item.className = 'c_new table-wrapper';
            item.innerHTML = `
                            <div class="table-handle-container" contenteditable="false">
                                <div class="table-handle ri-drag-move-line" title="Drag to move"></div>
                                <div class="table-delete ri-delete-bin-line" title="Delete Table"></div>
                            </div>
                            ${tableHtml}`;
            item.setAttribute('cy-type', 'table');
            item.setAttribute('cy-config', JSON.stringify(config));
            item.style.cursor = 'default';
            item.style.opacity = '1';

            // Internal delete handler
            item.querySelector('.table-delete').onclick = (e) => {
                e.stopPropagation();
                self.dialog.add(ConfirmationDialog, {
                    body: "Are you sure you want to delete this table?",
                    confirm: () => item.remove(),
                    cancel: () => { },
                });
            };

            const refreshRes = await self.rpc('/cyllo_studio/get_report_source', {
                template: self._template,
            });
            if (refreshRes.success) {
                self.state.sourceCode = refreshRes.arch;
                if (self.aceEditor) {
                    self.aceEditor.setValue(refreshRes.arch, -1);
                }
            }
        }

        if (type === 'qr') {
            const config = await self.openQrWizard(item);
            if (!config) {
                item.remove();
                return;
            }
            self.insertQrBlock(item, config);
        }

        if (type === 'sign') {
            const signId = 'sign_' + Math.random().toString(36).slice(2, 10);
            const defaultCfg = {
                role: 'customer',
                label: 'Authorized Signature',
                required: true,
                show_date: false,
                show_name: false,
                width: 200,
                height: 100,
                alignment: 'left',
            };
            item.className = 'sign-wrapper c_new';
            item.setAttribute('cy-type', 'sign');
            item.setAttribute('data-sign-id', signId);
            item.setAttribute('data-sign-config', JSON.stringify(defaultCfg));
            item.dataset.role = defaultCfg.role;
            item.style.width = defaultCfg.width + 'px';
            item.style.height = defaultCfg.height + 'px';
            item.style.opacity = '1';
            item.style.cursor = 'default';
            item.style.textAlign = defaultCfg.alignment;

            item.innerHTML = `
                        <div class="sign-toolbar" contenteditable="false">
                            <span class="sign-drag-handle ri-drag-move-line" title="Drag to move"></span>
                            <span class="sign-delete-btn ri-delete-bin-line" title="Delete Signature"></span>
                        </div>
                        <div class="sign-content-wrapper" style="pointer-events: none; border: 2px dashed #ccc; width: 100%; height: 100%; padding: 10px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; position: relative;">
                            <div class="sign-watermark" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); opacity: 0.1; font-size: 40px; color: #9ea700;"><i class="fa fa-pencil"></i></div>
                            <div class="sign-role-badge" style="position: absolute; top: -10px; right: 10px; background: #9ea700; color: white; padding: 2px 6px; font-size: 10px; border-radius: 4px; text-transform: uppercase;">${escapeHtml(defaultCfg.role)}</div>
                            <div class="sign-empty-line" style="border-bottom: 1px solid #333; width: 80%; margin: 10px auto;"></div>
                            <p class="sign-label" style="font-weight: bold; font-size: 14px; margin: 0;">${escapeHtml(defaultCfg.label)}</p>
                        </div>
                        <div class="sign-resize-handles" contenteditable="false">
                            <div class="sign-resize-handle" data-dir="se"></div>
                        </div>
                    `;

            item.querySelector('.sign-delete-btn').onclick = (e) => {
                e.stopPropagation();
                self.dialog.add(ConfirmationDialog, {
                    body: 'Delete this Signature?',
                    confirm: () => {
                        if (self.state.showSignProps && self._selectedSignEl === item) {
                            self.closeSignProps();
                        }
                        item.remove();
                        self._updateHasSign();
                    },
                    cancel: () => { },
                });
            };

            self._setupSignResizeHandles(item);
            self._updateHasSign();
        }
        // Re-initialize drag handles for the new zone content
        self._refreshDragHandles();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Table Config Modal — Preset Definitions
    // ─────────────────────────────────────────────────────────────────────────

    static TABLE_PRESETS = {
        balance_sheet: {
            model: 'account.account',
            columns: [
                { label: 'Account', field: 'name', fieldType: 'char', aggregation: 'none', width: '40%' },
                { label: 'Debit', field: 'debit', fieldType: 'monetary', aggregation: 'sum', width: '30%' },
                { label: 'Credit', field: 'credit', fieldType: 'monetary', aggregation: 'sum', width: '30%' },
            ],
            rowSource: 'dynamic',
            headerRow: true,
            totalsRow: true,
            manualRows: 5,
            applyDomain: false,
            domain: '',
            includeAllCompanies: false,
            sections: [
                {
                    label: 'Assets',
                    rowType: 'static',
                    domain: [["account_type", "in", ["asset_receivable", "asset_cash", "asset_current", "asset_non_current"]]],
                    subtotal: true,
                },
                {
                    label: 'Liabilities & Equity',
                    rowType: 'static',
                    domain: [["account_type", "in", ["liability_payable", "liability_current", "equity"]]],
                    subtotal: true,
                },
            ],
            grandTotal: {
                rowType: 'computed',
                formula: 'Total Assets = Total Liabilities + Equity',
                validate: true,
            },
        },
        p_and_l: {
            model: 'account.move.line',
            columns: [
                { label: 'Account', field: 'account_id', fieldType: 'many2one', aggregation: 'none', width: '40%' },
                { label: 'Debit', field: 'debit', fieldType: 'monetary', aggregation: 'sum', width: '30%' },
                { label: 'Credit', field: 'credit', fieldType: 'monetary', aggregation: 'sum', width: '30%' },
            ],
            rowSource: 'dynamic',
            headerRow: true,
            totalsRow: true,
            manualRows: 5,
            applyDomain: false,
            domain: '',
            includeAllCompanies: false,
            sections: [
                {
                    label: 'Revenue',
                    rowType: 'static',
                    domain: [["account_id.account_type", "=", "income"]],
                    subtotal: true,
                },
                {
                    label: 'Expenses',
                    rowType: 'static',
                    domain: [["account_id.account_type", "=", "expense"]],
                    subtotal: true,
                },
            ],
            grandTotal: {
                rowType: 'computed',
                formula: 'Net Profit = Revenue - Expenses',
                validate: true,
            },
        },
        invoice: {
            model: 'account.move.line',
            columns: [
                { label: 'Description', field: 'name', fieldType: 'char', aggregation: 'none', width: '40%' },
                { label: 'Quantity', field: 'quantity', fieldType: 'float', aggregation: 'sum', width: '15%' },
                { label: 'Unit Price', field: 'price_unit', fieldType: 'float', aggregation: 'none', width: '20%' },
                { label: 'Amount', field: 'price_subtotal', fieldType: 'monetary', aggregation: 'sum', width: '25%' },
            ],
            rowSource: 'dynamic',
            headerRow: true,
            totalsRow: true,
            manualRows: 5,
            applyDomain: false,
            domain: '',
            includeAllCompanies: false,
            sections: [],
            grandTotal: null,
        },
        blank: {
            model: '',
            columns: [],
            rowSource: 'dynamic',
            headerRow: true,
            totalsRow: false,
            manualRows: 5,
            applyDomain: false,
            domain: '',
            includeAllCompanies: false,
            sections: [],
            grandTotal: null,
        },
    };

    _getDefaultTcmState() {
        const preset = EditReport.TABLE_PRESETS.balance_sheet;
        return {
            preset: 'balance_sheet',
            model: preset.model,
            columns: JSON.parse(JSON.stringify(preset.columns)),
            rowSource: preset.rowSource,
            manualRows: preset.manualRows,
            headerRow: preset.headerRow,
            totalsRow: preset.totalsRow,
            applyDomain: preset.applyDomain,
            domain: preset.domain,
            includeAllCompanies: preset.includeAllCompanies,
            sections: JSON.parse(JSON.stringify(preset.sections)),
            grandTotal: preset.grandTotal ? JSON.parse(JSON.stringify(preset.grandTotal)) : null,
            availableModels: [],
            availableFields: [],
        };
    }


    async openTableConfigModal(targetEl, resModel) {
        // Reset state to default
        Object.assign(this.state.tcm, this._getDefaultTcmState());

        // Fetch available models
        try {
            const models = await this.orm.searchRead('ir.model', [], ['name', 'model'], { order: 'name' });
            this.state.tcm.availableModels = models.map(m => ({ name: m.name, model: m.model }));
        } catch (e) {
            console.warn('[TableConfig] Could not fetch models:', e);
            this.state.tcm.availableModels = [
                { name: 'Account', model: 'account.account' },
                { name: 'Journal Item', model: 'account.move.line' },
                { name: 'Invoice', model: 'account.move' },
            ];
        }

        // Apply default preset to load fields for the default model
        await this._loadModelFields(this.state.tcm.model);

        // Show the modal and return a promise
        this.state.showTableModal = true;

        return new Promise((resolve) => {
            this._tcmResolve = resolve;
        });
    }

    onSelectPreset(presetName) {
        const preset = EditReport.TABLE_PRESETS[presetName];
        if (!preset) return;

        this.state.tcm.preset = presetName;
        this.state.tcm.model = preset.model;
        this.state.tcm.columns = JSON.parse(JSON.stringify(preset.columns));
        this.state.tcm.rowSource = preset.rowSource;
        this.state.tcm.manualRows = preset.manualRows;
        this.state.tcm.headerRow = preset.headerRow;
        this.state.tcm.totalsRow = preset.totalsRow;
        this.state.tcm.applyDomain = preset.applyDomain;
        this.state.tcm.domain = preset.domain;
        this.state.tcm.includeAllCompanies = preset.includeAllCompanies;
        this.state.tcm.sections = JSON.parse(JSON.stringify(preset.sections));
        this.state.tcm.grandTotal = preset.grandTotal ? JSON.parse(JSON.stringify(preset.grandTotal)) : null;

        if (preset.model) {
            this._loadModelFields(preset.model);
        } else {
            this.state.tcm.availableFields = [];
        }
    }

    async onModelChange(ev) {
        const model = ev.target.value;
        this.state.tcm.model = model;
        if (model) {
            await this._loadModelFields(model);
        } else {
            this.state.tcm.availableFields = [];
        }
    }

    async _loadModelFields(modelName) {
        if (!modelName) {
            this.state.tcm.availableFields = [];
            return;
        }
        try {
            const fields = await this.orm.call(modelName, 'fields_get', [], {
                attributes: ['string', 'type', 'store', 'relation'],
            });
            const HIDDEN_TYPES = ['one2many', 'many2many', 'binary'];
            const fieldList = Object.entries(fields)
                .filter(([name, info]) => !HIDDEN_TYPES.includes(info.type) && !name.startsWith('__'))
                .map(([name, info]) => ({
                    name,
                    string: info.string || name,
                    type: info.type,
                    store: info.store,
                    relation: info.relation || null,
                }))
                .sort((a, b) => (a.string || a.name).localeCompare(b.string || b.name));
            this.state.tcm.availableFields = fieldList;
        } catch (e) {
            console.warn('[TableConfig] Could not fetch fields for', modelName, e);
            this.state.tcm.availableFields = [];
        }
    }

    // ── Column management ────────────────────────────────────────────────────

    onAddColumn() {
        this.state.tcm.columns.push({
            label: '',
            field: '',
            fieldType: '',
            aggregation: 'none',
            width: '',
        });
    }

    onRemoveColumn(index) {
        this.state.tcm.columns.splice(index, 1);
    }

    onColumnLabelChange(index, ev) {
        this.state.tcm.columns[index].label = ev.target.value;
    }

    onColumnFieldChange(index, ev) {
        const fieldName = ev.target.value;
        this.state.tcm.columns[index].field = fieldName;
        // Auto-detect field type from availableFields
        const fieldInfo = this.state.tcm.availableFields.find(f => f.name === fieldName);
        if (fieldInfo) {
            this.state.tcm.columns[index].fieldType = fieldInfo.type;
            // Auto-set label if empty
            if (!this.state.tcm.columns[index].label) {
                this.state.tcm.columns[index].label = fieldInfo.string || fieldName;
            }
        }
    }

    onColumnAggChange(index, ev) {
        this.state.tcm.columns[index].aggregation = ev.target.value;
    }

    onColumnWidthChange(index, ev) {
        this.state.tcm.columns[index].width = ev.target.value;
    }

    // ── Modal confirm / cancel ───────────────────────────────────────────────

    onTableModalConfirm() {
        const config = JSON.parse(JSON.stringify(this.state.tcm));
        // Remove internal UI fields
        delete config.availableModels;
        delete config.availableFields;
        this.state.showTableModal = false;
        if (this._tcmResolve) {
            this._tcmResolve(config);
            this._tcmResolve = null;
        }
    }

    onTableModalCancel() {
        this.state.showTableModal = false;
        if (this._tcmResolve) {
            this._tcmResolve(null);
            this._tcmResolve = null;
        }
    }

    _generateTableHtml(config) {
        const cols = config.columns || [];
        const colCount = cols.length || 3;

        // Column width style helper
        const colStyle = (col, align) => {
            let s = `text-align: ${align || 'left'}; padding: 8px;`;
            if (col.width) s += ` width: ${col.width};`;
            return s;
        };

        // Determine if a field type is numeric
        const isNumeric = (type) => ['float', 'monetary', 'integer'].includes(type);

        const colgroupHtml = cols.length
            ? `<colgroup>${cols.map(col => `<col style="width: ${col.width || 'auto'};">`).join('')}</colgroup>`
            : '';

        let html = `
            <table class="table table-sm mt-3" style="width: 100%; border-collapse: collapse; table-layout: fixed;">
            ${colgroupHtml}`;

        // ── Header Row ────────────────────────────────────────────────
        if (config.headerRow && cols.length > 0) {
            html += `<thead style="border-bottom: 2px solid #333;"><tr>`;
            cols.forEach(col => {
                const align = isNumeric(col.fieldType) ? 'right' : 'left';
                html += `<th style="${colStyle(col, align)}">${escapeHtml(col.label || col.field || 'Column')}</th>`;
            });
            html += `</tr></thead>`;
        }

        html += `<tbody style="border-bottom: 1px solid #dee2e6;">`;

        // ── Preset: Balance Sheet ─────────────────────────────────────
        if (config.preset === 'balance_sheet' && config.sections && config.sections.length > 0) {
            config.sections.forEach(section => {
                const domainStr = JSON.stringify(section.domain || []);
                // Section header
                html += `
                    <tr class="table-active section-header" style="background-color: #f2f2f2; font-weight: bold; border-top: 2px solid #333;">
                        <td colspan="${colCount}">${escapeHtml((section.label || 'Section').toUpperCase())}</td>
                    </tr>`;
                // Data rows — use t-foreach with the model on the tr directly
                html += `
                    <tr t-foreach="docs.filtered(lambda r: r.account_type in ${this._pythonDomainValues(section.domain)})" t-as="doc" class="data-row" style="border-bottom: 1px solid #eee;">`;
                cols.forEach(col => {
                    const align = isNumeric(col.fieldType) ? 'right' : 'left';
                    if (col.fieldType === 'many2one') {
                        html += `<td style="${colStyle(col, align)}"><span t-field="doc.${col.field}"/></td>`;
                    } else if (isNumeric(col.fieldType)) {
                        html += `<td style="${colStyle(col, align)}"><span t-field="doc.${col.field}" t-att-class="doc.${col.field} &lt; 0 and 'text-danger' or ''"/></td>`;
                    } else {
                        html += `<td style="${colStyle(col, align)}"><span t-field="doc.${col.field}"/></td>`;
                    }
                });
                html += `</tr>`;
                // Section subtotal
                if (section.subtotal) {
                    html += `
                    <tr class="total-row" style="border-top: 1px solid #333; font-weight: bold; background-color: #fafafa;">`;
                    cols.forEach((col, ci) => {
                        const align = isNumeric(col.fieldType) ? 'right' : 'left';
                        if (ci === 0) {
                            html += `<td style="${colStyle(col, align)}">Total ${escapeHtml(section.label || '')}</td>`;
                        } else if (isNumeric(col.fieldType) && col.aggregation === 'sum') {
                            html += `<td style="${colStyle(col, 'right')}"><span t-esc="sum(section_records.mapped('${col.field}'))"/></td>`;
                        } else {
                            html += `<td style="${colStyle(col, align)}"></td>`;
                        }
                    });
                    html += `</tr>`;
                }
            });

            // ── Preset: Invoice ───────────────────────────────────────────
        } else if (config.preset === 'invoice') {
            html += `
                    <t t-foreach="doc.invoice_line_ids" t-as="line">
                        <tr style="border-bottom: 1px solid #f8f9fa;">`;
            cols.forEach(col => {
                const align = isNumeric(col.fieldType) ? 'right' : 'left';
                html += `<td style="${colStyle(col, align)}"><span t-field="line.${col.field}" /></td>`;
            });
            html += `
                        </tr>
                </t>`;

            // ── Preset: P&L ───────────────────────────────────────
        } else if (config.preset === 'p_and_l' && config.sections && config.sections.length > 0) {
            config.sections.forEach(section => {
                html += `
                    <tr class="table-active section-header" style="background-color: #f2f2f2; font-weight: bold; border-top: 2px solid #333;">
                        <td colspan="${colCount}">${escapeHtml((section.label || 'Section').toUpperCase())}</td>
                    </tr>
                    <t t-foreach="doc.line_ids.filtered(lambda l: l.${section.domain?.[0]?.[0] || 'account_id.account_type'} ${section.domain?.[0]?.[1] || '='} '${section.domain?.[0]?.[2] || 'income'}')" t-as="line">
                        <tr class="data-row" style="border-bottom: 1px solid #eee;">`;
                cols.forEach(col => {
                    const align = isNumeric(col.fieldType) ? 'right' : 'left';
                    html += `<td style="${colStyle(col, align)}"><span t-field="line.${col.field}" /></td>`;
                });
                html += `
                        </tr>
                    </t>`;
                if (section.subtotal) {
                    html += `
                        <tr class="total-row" style="border-top: 1px solid #333; font-weight: bold; background-color: #fafafa;">`;
                    cols.forEach((col, ci) => {
                        if (ci === 0) {
                            html += `<td>Total ${section.label || ''}</td>`;
                        } else if (isNumeric(col.fieldType)) {
                            html += `<td style="text-align: right;">—</td>`;
                        } else {
                            html += `<td></td>`;
                        }
                    });
                    html += `</tr>`;
                }
            });

            // ── Dynamic / Manual / Blank ─────────────────────────────────
        } else {
            if (config.rowSource === 'manual') {
                const rows = config.manualRows || 5;
                for (let r = 0; r < rows; r++) {
                    html += `<tr style="border-bottom: 1px solid #f8f9fa;">`;
                    cols.forEach(col => {
                        html += `<td style="padding: 8px;">${col.label || ''}</td>`;
                    });
                    html += `</tr>`;
                }
            } else if (config.model && cols.length > 0) {
                // Dynamic with model — t-foreach over docs
                html += `
                <tr t-foreach="docs" t-as="doc" style="border-bottom: 1px solid #f8f9fa;">`;
                cols.forEach(col => {
                    const align = isNumeric(col.fieldType) ? 'right' : 'left';
                    if (col.field) {
                        html += `<td style="${colStyle(col, align)}"><span t-field="doc.${col.field}"/></td>`;
                    } else {
                        html += `<td style="padding: 8px;">${col.label || ''}</td>`;
                    }
                });
                html += `</tr>`;
            } else {
                // Fallback — empty placeholder rows
                for (let r = 0; r < 3; r++) {
                    html += `<tr style="border-bottom: 1px solid #f8f9fa;">`;
                    for (let c = 0; c < Math.max(colCount, 3); c++) {
                        html += `<td style="padding: 8px;">Data ${r + 1}-${c + 1}</td>`;
                    }
                    html += `</tr>`;
                }
            }
        }

        html += `</tbody>`;

        // ── Totals Row ────────────────────────────────────────────────
        if (config.totalsRow && cols.length > 0) {
            html += `<tfoot style="border-top: 2px solid #333; font-weight: bold;"><tr>`;
            cols.forEach((col, ci) => {
                const align = isNumeric(col.fieldType) ? 'right' : 'left';
                if (ci === 0) {
                    html += `<td style="${colStyle(col, align)}">Total</td>`;
                } else if (col.aggregation && col.aggregation !== 'none' && isNumeric(col.fieldType)) {
                    html += `<td style="${colStyle(col, 'right')}">—</td>`;
                } else {
                    html += `<td style="${colStyle(col, align)}"></td>`;
                }
            });
            html += `</tr></tfoot>`;
        }

        html += `</table>`;
        return html;
    }

    /**
     * Helper: extract domain values for Python filtering.
     * Converts [["account_type", "in", ["asset_receivable",...]]] → the list values.
     */
    _pythonDomainValues(domain) {
        if (!domain || !domain.length) return '[]';
        const first = domain[0];
        if (Array.isArray(first) && first.length >= 3 && Array.isArray(first[2])) {
            return JSON.stringify(first[2]).replace(/"/g, "'");
        }
        return '[]';
    }
    /**
     * Remove orphaned <t>/<cy-qweb-t> structural nodes that the HTML parser
     * foster-parents as siblings of the table wrapper.
     *
     * Background: `<t t-foreach>` / `<t t-set>` are not valid inside <tbody>,
     * so the browser hoists them *before* the <table> as zone siblings while
     * leaving the actual <tr> rows inside <tbody>.  When the .table-wrapper is
     * removed these empty <t> ghosts remain and get serialised into the saved
     * QWeb XML.  We kill them here BEFORE calling wrapper.remove().
     *
     * @param {HTMLElement} wrapper  The .table-wrapper about to be deleted.
     */
    _removeOrphanedQwebElements(wrapper) {
        const zone = wrapper.parentElement;
        if (!zone) return;

        const siblings = Array.from(zone.children);
        const wrapperIdx = siblings.indexOf(wrapper);

        siblings.forEach((sib, idx) => {
            const tag = (sib.tagName || '').toLowerCase();
            if (tag !== 't' && tag !== 'cy-qweb-t') return;

            // Determine whether this <t> carries visible user content.
            // Structural nodes (t-foreach, t-set, t-as, t-value …) foster-parented
            // out of the table will be empty or only contain other <t> nodes.
            const hasVisibleContent =
                sib.textContent.trim().length > 0 &&
                Array.from(sib.children).some(
                    c => !['t', 'cy-qweb-t'].includes((c.tagName || '').toLowerCase())
                );

            // Remove if: (a) it has no real visible content, OR
            //             (b) it is immediately adjacent to the wrapper (within 2 slots)
            //                 and has no visible content at all.
            const isAdjacent = Math.abs(idx - wrapperIdx) <= 2;
            if (!hasVisibleContent || isAdjacent) {
                sib.remove();
            }
        });

        // Safety sweep: catch any remaining empty structural orphans in the zone.
        zone.querySelectorAll('t, cy-qweb-t').forEach(el => {
            if (!el.textContent.trim() && el.children.length === 0) {
                el.remove();
            }
        });
    }

    /** Destroy all tracked SortableJS instances. */
    _destroySortableInstances() {
        // Abort the cross-document panel drag shim listener
        if (this._panelDragAbort) {
            this._panelDragAbort.abort();
            this._panelDragAbort = null;
        }
        this._sortableInstances.forEach(s => { try { s.destroy(); } catch (_) { } });
        this._sortableInstances = [];
    }

    /**
     * Re-create zone sortables so newly inserted elements participate in DnD.
     * Called after inserting new nodes into the report frame.
     */
    _refreshDragHandles() {
        if (!this._reportFrame) return;

        // Destroy existing zone sortables (keep panel sortable alive – index 0)
        const [panelSortable, ...zoneSortables] = this._sortableInstances;
        zoneSortables.forEach(s => { try { s.destroy(); } catch (_) { } });
        this._sortableInstances = panelSortable ? [panelSortable] : [];

        // Recreate for every cy-template zone (main canvas zones)
        this._reportFrame.querySelectorAll('[cy-template]').forEach(zone => {
            this._createZoneSortable(zone);
        });

        // Also register every box dropzone as a sortable target
        this._reportFrame.querySelectorAll('.box-dropzone').forEach(dz => {
            this._createBoxDropzoneSortable(dz);
        });

        // Re-wire resize handles for all box wrappers
        this._reportFrame.querySelectorAll('.box-section-wrapper').forEach(bw => {
            this._setupBoxResizeHandles(bw);
        });
    }

    /** Kept for compatibility. */
    _reinitDrake() {
        this._refreshDragHandles();
    }

    /**
     * Dynamic fields are inserted as `t-field="<recordVar>.<field>"`, which only
     * renders when the report iterates a document *record* (a `t-foreach="docs"`
     * loop). The whole family of Cyllo financial reports (Aged Payable/Receivable,
     * P&L, Balance Sheet, Trial Balance, Bank/Cash Book, Partner Ledger, Tax) is
     * model-less: they pass hand-built dicts and never expose `doc`, so a bound
     * field 500s at render with `KeyError: 'doc'` and the preview reports
     * "corrupted XML". `_recordBased` (from _detect_record_context on the server)
     * is false for exactly these reports — refuse the drop with a clear pointer to
     * Edit Sources / QWeb inheritance instead of silently corrupting the template.
     *
     * Only blocks when we positively know the report is NOT record-based
     * (`=== false`); an undefined flag (detection didn't run) is left permissive.
     */
    _canBindDynamicField() {
        if (this._recordBased === false) {
            this.notification.add(
                "This report can't take drag-and-drop fields: it renders custom data with no " +
                "document record in scope, so a dropped field can't be bound and the preview would " +
                "fail. Add columns via “Edit Sources” or a module-level QWeb inheritance instead.",
                { type: "warning", sticky: true }
            );
            return false;
        }
        return true;
    }

    async openFieldSelectorPopover(targetEl, resModel, filter) {
        // The report canvas is an <iframe>; `targetEl` (the drop zone) lives in the
        // iframe document, but the popover service renders in the host-document
        // overlay and positions via getBoundingClientRect() in host coordinates.
        // Anchoring to an in-iframe element mis-positions the popover (or prevents
        // it opening), which is why dropped fields appeared to do nothing. Anchor to
        // the host-side iframe element so the field selector reliably opens; the
        // dropped node is still inserted at its dropped position by the caller.
        const hostAnchor = (this.reportFrameRef && this.reportFrameRef.el) || targetEl;
        return new Promise((resolve) => {
            this.popover.add(hostAnchor, StudioFieldSelectorPopover, {
                resModel,
                update: async (path) => { path = path; },
                showSearchInput: true,
                isDebugMode: (odoo.debug == 1),
                filter,
                complete: async (finalPath = null) => {
                    if (finalPath) {
                        const fieldInfo = await this.loadFieldInfo(resModel, finalPath);
                        resolve({ fieldPath: finalPath, fieldInfo: fieldInfo.fieldDef });
                    } else {
                        resolve({ fieldPath: null, fieldInfo: null });
                    }
                },
            });
        });
    }

    // \u2500\u2500 Company Logo Upload \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    onLogoClick(ev) {
        if (this.state.hideLogo && this.state.companyLogo) {
            // Restore hidden logo for this report (no file picker needed)
            this.state.hideLogo = false;
            if (this.undoManager) this.undoManager.debouncedSave();
            return;
        }

        if (this.state.companyLogo) {
            // Remove existing dropdown if any
            const existing = document.getElementById('cy-logo-actions-menu');
            if (existing) existing.remove();

            const rect = ev.currentTarget.getBoundingClientRect();
            const menu = document.createElement('div');
            menu.id = 'cy-logo-actions-menu';
            menu.className = 'bg-white border rounded shadow-sm py-1 position-fixed';
            menu.style.top = `${rect.bottom + 5}px`;
            menu.style.left = `${rect.left}px`;
            menu.style.zIndex = '9999';
            menu.style.minWidth = '150px';

            const uploadBtn = document.createElement('button');
            uploadBtn.className = 'dropdown-item text-start w-100 px-3 py-2 border-0 bg-white';
            uploadBtn.innerText = 'Upload New Logo';
            uploadBtn.onclick = () => {
                menu.remove();
                if (this.logoInputRef.el) this.logoInputRef.el.click();
            };

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'dropdown-item text-start w-100 px-3 py-2 border-0 bg-white text-danger';
            deleteBtn.innerText = 'Delete Logo';
            deleteBtn.onclick = async () => {
                menu.remove();
                await this.orm.write('res.company', [this._companyId], { logo: false });
                this.state.companyLogo = false;
                this.notification.add('Company logo removed', { type: 'success' });
            };
            menu.appendChild(uploadBtn);
            menu.appendChild(deleteBtn);
            document.body.appendChild(menu);
            // Close on outside click
            setTimeout(() => {
                const closeMenu = (e) => {
                    if (!menu.contains(e.target)) {
                        menu.remove();
                        document.removeEventListener('click', closeMenu);
                    }
                };
                document.addEventListener('click', closeMenu);
            }, 0);
            return;
        }

        // No logo yet — open file picker to upload one
        if (this.logoInputRef.el) this.logoInputRef.el.click();
    }

    onRemoveLogoClick(ev) {
        // Hides the logo for THIS report only. Does NOT touch res.company.logo.
        this.state.hideLogo = true;
        this.state.logoHovered = false;

        // Hide visually from canvas
        if (this.reportFrameRef && this.reportFrameRef.el) {
            const logoImgs = this.reportFrameRef.el.querySelectorAll('img[alt="Logo"], .company_logo');
            logoImgs.forEach(logoImg => {
                logoImg.classList.add('cy-logo-hidden');
                logoImg.style.setProperty('display', 'none', 'important');
            });
        }
        if (this.undoManager) this.undoManager.debouncedSave();
    }

    onLogoVisibilityChange(ev) {
        const checked = ev.target.checked;
        this.state.hideLogo = checked;

        // Visual update in the canvas
        if (this.reportFrameRef && this.reportFrameRef.el) {
            const logoImgs = this.reportFrameRef.el.querySelectorAll('img[alt="Logo"], .company_logo');
            logoImgs.forEach(logoImg => {
                if (checked) {
                    logoImg.classList.add('cy-logo-hidden');
                    logoImg.style.setProperty('display', 'none', 'important');
                } else {
                    logoImg.classList.remove('cy-logo-hidden');
                    logoImg.style.removeProperty('display');
                }
            });
        }

        if (this.undoManager) this.undoManager.debouncedSave();
    }

    async onLogoFileChange(ev) {
        const file = ev.target.files[0];
        if (!file) return;
        // Use stored company ID (this.env.company may not be available in Community)
        const companyId = this._companyId;
        if (!companyId) {
            this.notification.add('Could not determine company. Please reload and try again.', { type: 'warning' });
            return;
        }
        const reader = new FileReader();
        reader.onload = async (e) => {
            const base64 = e.target.result.split(',')[1];
            try {
                await this.orm.write('res.company', [companyId], { logo: base64 });
                this.state.companyLogo = base64;
                this.notification.add('Company logo updated', { type: 'success' });
            } catch (err) {
                this.notification.add('Failed to save logo: ' + err.message, { type: 'danger' });
            }
        };
        reader.readAsDataURL(file);
    }

    // Name of the business view Reports was opened from (e.g. "User Dashboard",
    // "Discuss", "Sales") — persisted by navbar.js's _getBusinessContext().
    get businessBreadcrumbName() {
        return sessionStorage.getItem('CyConfigBusinessName') || 'Home';
    }

    async goToBusinessParent(component) {
        const actionId = sessionStorage.getItem('CyConfigBusinessActionId');
        if (actionId) {
            component.action.doAction(parseInt(actionId, 10));
        } else {
            this.close_edit(component);
        }
    }

    async close_edit(component) {
        // Scope back to whatever business model Reports was opened from
        // (persisted by navbar.js's _getBusinessContext()) — not this._resModel,
        // which is the *edited report's own* data-source model and has nothing
        // to do with how the Reports list should be filtered on return.
        const businessModel = sessionStorage.getItem('CyConfigBusinessModel');

        const action = {
            name: 'Reports',
            type: 'ir.actions.act_window',
            res_model: 'ir.actions.report',
            target: 'current',
            views: [[false, 'kanban']],
            context: businessModel ? {
                default_model: businessModel,
                search_default_model: businessModel,
            } : {}
        };

        component.action.doAction(action);
    }

    async save_changes(component) {
        if (component.state.hasOverflow) {
            component.notification.add(
                "Cannot save: content exceeds the page boundary. " +
                "Remove or resize elements above the red line first.",
                { type: "danger", sticky: true }
            );
            // this.action.doAction("studio_reload");
            return;
        }
        if (component.state.isSaving) return;
        component.state.isSaving = true;
        try {
            document.querySelectorAll('.selected').forEach(el => el.classList.remove('selected'));
            document.querySelectorAll('[class="/"], [class=""]').forEach(el => el.removeAttribute('class'));
            $('[t-if], [t-elif], [t-else]').removeAttr('style');
            if (component.editor) component.editor.destroy();
            component.editor = null;

            // Ensure any pending DOM updates are finished
            await new Promise(r => setTimeout(r, 100));

            const frameEl = component.reportFrameRef.el;
            const editedHTML = frameEl.tagName === 'IFRAME' ? frameEl.contentDocument.documentElement.outerHTML : frameEl.innerHTML;

            const parser = new DOMParser();
            const editedDoc = parser.parseFromString(editedHTML, 'text/html');
            const originalDoc = parser.parseFromString(component._loadedArch || '', 'text/html');

            // Normalize BOTH docs by unwrapping UI shells and removing handles so we compare apples-to-apples
            component._cleanStudioAttrs(originalDoc.body, true);
            component._cleanStudioAttrs(editedDoc.body, true);

            let changes = component.getChangedElements(originalDoc, editedDoc);
            // ── Compare footer state against the persisted baseline (not originalDoc) ──
            // _loadedArch is captured AFTER onEditIframeLoad strips cy-custom-footer from the
            // live DOM, so originalDoc never contains .cy-custom-footer. Instead we maintain
            // a _savedFooterState object that is updated on every successful save/load.
            const sf = component._savedFooterState || {};
            const originalShowF = sf.showF !== undefined ? sf.showF : true;
            const originalShowD = sf.showD !== undefined ? sf.showD : false;
            const originalShowP = sf.showP !== undefined ? sf.showP : true;
            const originalHasCustom = sf.hasCustom !== undefined ? sf.hasCustom : false;
            const originalCustomText = sf.customText || '';

            const footerChanged = (
                component.state.footerShowReportFooter !== originalShowF ||
                component.state.footerShowDocName !== originalShowD ||
                component.state.footerShowPageNum !== originalShowP ||
                component.state.hasCustomFooter !== originalHasCustom ||
                (component.state.hasCustomFooter && component.state.companyReportFooterText !== originalCustomText)
            );


            // ── Logo hide/show persistence ──────────────────────────────────
            // We track whether hideLogo changed relative to what was originally loaded.
            const originallyHiddenLogo = !!(component._loadedArch || '').includes('cy-logo-override');
            const nowHidingLogo = component.state.hideLogo;

            // Build a standalone mini-template that injects or removes the CSS override
            // inside the report page div. We anchor it to the first cy-xpath node in
            // the edited document so the XPath is always valid.
            let logoOverrideTemplates = [];
            if (nowHidingLogo !== originallyHiddenLogo) {
                // Find any anchored node to get a valid cy-template
                const anchorEl = component.reportFrameRef.el.querySelector('[cy-xpath][cy-template]');
                const cyTemplate = anchorEl ? anchorEl.getAttribute('cy-template') : null;

                if (cyTemplate && nowHidingLogo) {
                    // Inject the override: find the page div xpath to append inside it
                    const pageEl = component.reportFrameRef.el.querySelector('.page[cy-xpath]');
                    const pageXpath = pageEl ? pageEl.getAttribute('cy-xpath') : null;
                    if (pageXpath) {
                        logoOverrideTemplates.push(
                            `<template id="cy_logo_override_${Date.now()}" inherit_id="${cyTemplate}">` +
                            `<xpath expr="${pageXpath}" position="inside">` +
                            `<style class="cy-logo-override">` +
                            `img[alt="Logo"]{display:none!important;}` +
                            `.company_logo{display:none!important;}` +
                            `</style>` +
                            `</xpath>` +
                            `</template>`
                        );
                    }
                } else if (cyTemplate && !nowHidingLogo) {
                    // The override was previously saved. We'll rely on the full content
                    // replace (position="replace" with cleaned content) to drop it.
                    // No separate template needed — the DOM save already excludes it.
                }
            }

            if (changes.length === 0 && logoOverrideTemplates.length === 0 && !footerChanged) {
                component.state.isSaving = false;
                return;
            }

            // ── Ensure _docTemplate is resolved before building XPaths ──
            // _docTemplate is only set when the source editor is opened.
            // On a fresh save we must resolve it so the footer xpath targets
            // the correct inner document view, not the outer wrapper template.
            if (!component._docTemplate) {
                try {
                    const srcRes = await component.rpc('/cyllo_studio/get_report_source', {
                        template: component._template,
                    });
                    if (srcRes && srcRes.success && srcRes.doc_template) {
                        component._docTemplate = srcRes.doc_template;
                        component._recordVar = srcRes.record_var || 'doc';
                        component._recordBased = srcRes.record_based;
                    } else {
                        component._docTemplate = component._template;
                        component._recordVar = 'doc';
                    }
                } catch (e) {
                    console.warn('[Cyllo Studio] Could not resolve _docTemplate, falling back to _template:', e);
                    component._docTemplate = component._template;
                    component._recordVar = 'doc';
                }
            }

            let newTemplates = component.buildInheritanceXML(changes);
            if (logoOverrideTemplates.length) {
                newTemplates = newTemplates.concat(logoOverrideTemplates);
            }

            const templateKeys = Object.keys(groupBy(changes, 'template'));
            if (templateKeys.length > 0) {
                const checkRes = await component.rpc('/cyllo_studio/check_shared_templates', {
                    templates: templateKeys,
                });
                if (checkRes && checkRes.success && checkRes.shared_templates && checkRes.shared_templates.length > 0) {
                    const sharedNames = checkRes.shared_templates.join(", ");
                    // const userConfirmed = await new Promise((resolve) => {
                    //     component.dialog.add(ConfirmationDialog, {
                    //         body: `The following templates are shared across multiple reports: ${sharedNames}. Changes will apply to all of them. Are you sure you want to save?`,
                    //         confirm: () => resolve(true),
                    //         cancel: () => resolve(false),
                    //     });
                    // });
                    // if (!userConfirmed) {
                    //     component.state.isSaving = false;
                    //     return;
                    // }
                }
            }
            const result = await component.rpc('/cyllo_studio/create/inherited_view', {
                all_arch: newTemplates,
            });

            if (result && result['success'] === true) {
                if (result.skipped_protected && result.skipped_protected.length > 0) {
                    component.notification.add(
                        `Report saved, but some changes were skipped (protected layout templates): ${result.skipped_protected.join(', ')}. These layout zones cannot be overridden safely — try anchoring your field inside the document body instead.`,
                        { type: "warning", sticky: true }
                    );
                } else {
                    component.notification.add("Report saved successfully", { type: "success" });
                }

                // ── Persist footer baseline so subsequent saves compare against what was just saved ──
                component._savedFooterState = {
                    showF: component.state.footerShowReportFooter,
                    showD: component.state.footerShowDocName,
                    showP: component.state.footerShowPageNum,
                    hasCustom: component.state.hasCustomFooter,
                    customText: component.state.companyReportFooterText || '',
                };

                // ── CAPTURE THUMBNAIL (Server-Side PDF to Image) ────
                if (!component.state.hasThumbnail) {
                    const sampleRecordId = component.state.records && component.state.records.length > 0 ? component.state.records[0] : null;
                    if (sampleRecordId) {
                        // Fire and forget - let the server generate the thumbnail quietly in the background
                        component.rpc('/cyllo_studio/generate_report_thumbnail', {
                            report_id: component._reportId,
                            record_id: sampleRecordId
                        }).then((res) => {
                            if (res && res.success) {
                                component.state.hasThumbnail = true;
                            } else {
                                console.error("[Cyllo Studio] Server thumbnail error:", res ? res.error : "Unknown");
                            }
                        }).catch((e) => {
                            console.error("[Cyllo Studio] Failed to generate thumbnail server-side:", e);
                        });
                    }
                }

                // ── PERSISTENT SAVE: Refresh local state instead of closing ────
                const resArch = await component.rpc('/cyllo_studio/get_arch', {
                    template: component._template,
                    show_placeholders: false
                });
                if (resArch && resArch.success) {
                    component._loadedArch = resArch.arch;
                    if (!component.state.previewMode) {
                        if (component.reportFrameRef.el && component.reportFrameRef.el.tagName === 'IFRAME') {
                            component.reportFrameRef.el.contentWindow.location.reload();
                        }
                    } else {
                        await component._fetchPreviewData();
                    }

                    // If source editor is open, refresh it too (UI -> Source sync)
                    if (component.state.showSourceEditor) {
                        const refreshRes = await component.rpc('/cyllo_studio/get_report_source', {
                            template: component._template,
                        });
                        if (refreshRes.success) {
                            component.state.sourceCode = refreshRes.arch;
                            if (component.aceEditor) {
                                component.aceEditor.setValue(refreshRes.arch, -1);
                            }
                        }
                    }
                }
            } else {
                alert('Save failed: ' + ((result && result.error) || 'Unknown error'));
            }
        } finally {
            component.state.isSaving = false;
        }
    }

    getChangedElements(originalDoc, editedDoc) {
        let allChanges = []
        const newNodeSelector = '.c_new:not([cy-xpath]), [data-cy-new-field]:not([cy-xpath])';
        const changeKey = (template, xpath) => `${template || ''}::${xpath || ''}`;
        const ownedNewNodes = new Map();
        const ownedNewNodeOwners = new Set();

        const hasStructuralNodes = (node) => {
            if (!node || !node.hasAttribute) return false;
            const attrs = ['t-foreach', 't-set', 't-if', 't-elif', 't-else', 't-call', 't-as', 't-value', 't-field', 't-esc', 't-out'];
            if (attrs.some(a => node.hasAttribute(a))) return true;
            const tag = (node.tagName || '').toLowerCase();
            if (tag === 't' || tag === 'cy-qweb-t') return true;
            const selector = attrs.map(a => `t[${a}], cy-qweb-t[${a}]`).join(',') + ',t,cy-qweb-t';
            try {
                return !!(node.querySelector && node.querySelector(selector));
            } catch (e) {
                return Array.from(node.getElementsByTagName('*')).some(el => {
                    const etag = (el.tagName || '').toLowerCase();
                    if (etag === 't' || etag === 'cy-qweb-t') return true;
                    return attrs.some(a => el.hasAttribute(a));
                });
            }
        };

        const hasTIfElIfChainInChildren = (node) => {
            return Array.from(node.children).some(c => {
                const tag = (c.tagName || '').toLowerCase();
                if (tag !== 'cy-qweb-t' && tag !== 't') return false;
                if (c.hasAttribute('t-if')) return true;
                if (c.hasAttribute('t-elif') || c.hasAttribute('t-else')) return true;
                return Array.from(c.children).some(gc => {
                    const gtag = (gc.tagName || '').toLowerCase();
                    if (gtag !== 'cy-qweb-t' && gtag !== 't') return false;
                    return gc.hasAttribute('t-if') || gc.hasAttribute('t-elif') || gc.hasAttribute('t-else');
                });
            });
        };

        const containsTable = (node) => {
            return !!(node.querySelector && node.querySelector('table'));
        };
        const isNewNode = (node) => !!(node && node.nodeType === 1 && (
            node.classList.contains('c_new') || node.hasAttribute('data-cy-new-field')
        ));

        Array.from(editedDoc.querySelectorAll(newNodeSelector)).forEach(node => {
            const owner = node.closest('[cy-xpath]');
            if (!owner) return;
            const ownerXpath = owner.getAttribute('cy-xpath');
            const ownerTemplate = owner.getAttribute('cy-template');
            const key = changeKey(ownerTemplate, ownerXpath);
            if (!ownedNewNodes.has(key)) ownedNewNodes.set(key, []);
            ownedNewNodes.get(key).push(node);
            ownedNewNodeOwners.add(owner);
        });

        editedDoc.querySelectorAll('[cy-template]').forEach(el => {
            const xpath = el.getAttribute('cy-xpath');
            const template = el.getAttribute('cy-template');
            const original = originalDoc.querySelector(
                `[cy-template="${template}"][cy-xpath="${xpath}"]`);
            if (!original) return;

            const text = (node) => Array.from(node.childNodes)
                .filter(n => n.nodeType === 3)
                .map(n => n.textContent.trim()).join('');

            const inner = (node) => Array.from(node.children)
                .filter(c => !c.hasAttribute('cy-xpath') && !isNewNode(c))
                .map(c => c.outerHTML.trim()).join('');

            const cyXpathChildren = (node) => Array.from(node.children)
                .filter(c => c.hasAttribute('cy-xpath'))
                .map(c => c.getAttribute('cy-xpath')).join(',');

            let textChanged = text(original) !== text(el);
            let innerChanged = inner(original) !== inner(el);

            const insertedNodes = ownedNewNodes.get(changeKey(template, xpath)) || [];
            const hasNestedInsertionOwner = Array.from(ownedNewNodeOwners).some(owner => owner !== el && el.contains(owner));
            const hasNewNodes = insertedNodes.length > 0 || (!!el.querySelector(newNodeSelector) && !hasNestedInsertionOwner);

            const tag = (el.tagName || '').toLowerCase();
            const isTable = ['table', 'tbody', 'thead', 'tfoot', 'tr'].includes(tag);
            const isDangerous = isTable || hasStructuralNodes(original) || hasTIfElIfChainInChildren(original) || original.classList.contains('page') || original.hasAttribute('name');

            // Protect dangerous structures from innerHTML/text replacement because replacing them
            // corrupts QWeb scope loops and t-if chains.
            if (isDangerous) {
                innerChanged = false;
                textChanged = false;
            }
            if (hasNestedInsertionOwner && insertedNodes.length === 0) {
                innerChanged = false;
                textChanged = false;
            }

            const rawStructChanged = cyXpathChildren(original) !== cyXpathChildren(el) || hasNewNodes;

            const structChanged = rawStructChanged && !isDangerous;
            const promoteInsertionOwner = insertedNodes.length > 0 && !structChanged;

            if (textChanged || innerChanged || structChanged || hasNewNodes || promoteInsertionOwner) {
                allChanges.push({
                    el,
                    xpath,
                    template,
                    structChanged: structChanged || promoteInsertionOwner,
                    hasNewNodes,
                });
            }

            // ── Detect attribute-only changes on cy-xpath children ──
            // When d-print-none / t-if is toggled via the editor wrappers,
            // _cleanStudioAttrs pushes those attributes down to the underlying cy-xpath children.
            // The inner/text comparison misses them because those nodes are excluded from diffs.
            // We generate separate change entries directly targeting the child xpath.
            Array.from(el.children)
                .filter(c => c.hasAttribute('cy-xpath') && !isNewNode(c))
                .forEach(editedChild => {
                    const childXpath = editedChild.getAttribute('cy-xpath');
                    const childTemplate = editedChild.getAttribute('cy-template') || template;
                    const originalChild = originalDoc.querySelector(
                        `[cy-template="${childTemplate}"][cy-xpath="${childXpath}"]`
                    ) || originalDoc.querySelector(`[cy-xpath="${childXpath}"]`);
                    if (!originalChild) return;

                    const editedHasHidden = editedChild.classList.contains('d-print-none');
                    const originalHasHidden = originalChild.classList.contains('d-print-none');
                    const editedTif = editedChild.getAttribute('t-if');
                    const originalTif = originalChild.getAttribute('t-if');

                    const attrChanged = (editedHasHidden !== originalHasHidden) || (editedTif !== originalTif);
                    if (attrChanged) {
                        allChanges.push({
                            el: editedChild,
                            xpath: childXpath,
                            template: childTemplate,
                            structChanged: false,
                            attrOnly: true,
                            isHidden: editedHasHidden,
                            tif: editedTif,
                        });
                    }

                    // ── Detect inline style changes (Block Settings: colour, bg, width…) ──
                    // The settings popup writes to the wrapper's inline style; without this
                    // the change is invisible to the diff and Save silently drops it.
                    const editedStyle = (editedChild.getAttribute('style') || '').trim();
                    const originalStyle = (originalChild.getAttribute('style') || '').trim();
                    if (editedStyle !== originalStyle) {
                        allChanges.push({
                            el: editedChild,
                            xpath: childXpath,
                            template: childTemplate,
                            structChanged: false,
                            styleOnly: true,
                            styleValue: editedStyle,
                        });
                    }
                });

            // ── Detect DELETED cy-xpath children ─────────────────────────────
            // `inner()` explicitly skips cy-xpath children, so the normal text/
            // inner comparison never notices when a labelled child is removed.
            // `structChanged` covers reordering but is vetoed for .page zones and
            // zones that contain structural QWeb nodes or tables.
            // This pass independently checks whether any cy-xpath child that was
            // present in the ORIGINAL zone is absent in the EDITED zone, and emits
            // a dedicated deletion entry for it so buildInheritanceXML can issue a
            // position="replace" with empty body.
            Array.from(original.children)
                .filter(origChild => origChild.hasAttribute('cy-xpath'))
                .forEach(origChild => {
                    const childXpath = origChild.getAttribute('cy-xpath');
                    const childTemplate = origChild.getAttribute('cy-template') || template;

                    // Skip if element is still present in the edited DOM
                    const stillPresent = el.querySelector(`[cy-xpath="${CSS.escape(childXpath)}"]`);
                    if (stillPresent) return;

                    // Skip structural/QWeb nodes — deleting t-foreach rows etc. is too dangerous
                    if (hasStructuralNodes(origChild)) return;
                    if (hasTIfElIfChainInChildren(origChild)) return;

                    allChanges.push({
                        el: origChild,
                        xpath: childXpath,
                        template: childTemplate,
                        structChanged: false,
                        isDeleted: true,
                    });
                });
        });

        return allChanges.filter(change => {
            const parentInsertionOwner = allChanges.some(parent =>
                parent !== change &&
                parent.hasNewNodes &&
                change.xpath &&
                parent.xpath &&
                change.xpath.startsWith(parent.xpath + '/')
            );
            if (parentInsertionOwner && !change.hasNewNodes && !change.attrOnly && !change.styleOnly && !change.isDeleted) {
                return false;
            }
            // Only suppress a nested change when its covering ancestor is a genuine
            // full-content replace: structChanged=true AND hasNewNodes=false.
            // Pure insertion-only ancestors (hasNewNodes=true, position="inside/before/after")
            // and attribute-only ancestors must NOT suppress their descendants — they do not
            // replace the descendant's own content, so the descendant's change is still valid.
            return !allChanges.some(p =>
                p !== change &&
                p.xpath &&
                change.xpath &&
                change.xpath.startsWith(p.xpath + '/') &&
                p.structChanged === true &&
                !p.hasNewNodes
            );
        });
    }


    _cleanStudioAttrs(node, keepStudioAttrs = false) {
        if (!node) return;
        const self = this;
        // Wrap in a temporary span to allow unwrapping the root itself
        const temp = document.createElement('span');
        const parent = node.parentNode;
        const next = node.nextSibling;
        temp.appendChild(node);

        const studioAttrs = ['cy-xpath', 'cy-template', 'cy-type', 'draggable', 'data-type', 'cy-config'];
        const markNewNode = (el) => {
            if (!el || !el.setAttribute) return;
            el.setAttribute('data-cy-new-field', '1');
        };
        const clean = (el) => {
            if (!el || !el.removeAttribute) return;

            // ── QR Block Serialization ──
            if (el.classList && el.classList.contains('s_qr_block')) {
                const configStr = el.dataset.qrConfig;
                if (configStr) {
                    try {
                        const qr = JSON.parse(configStr);
                        const align = qr.config.align || 'center';
                        const size = qr.config.size || 100;
                        const qwebExpr = self._buildQrExpression(true, qr);

                        el.innerHTML = '';
                        el.style.textAlign = align;
                        el.style.cursor = '';
                        el.style.opacity = '';

                        const img = document.createElement('img');
                        // Use url_quote (now provided in the backend context) for safe path encoding
                        img.setAttribute('t-att-src', `'/report/barcode/?barcode_type=QR&value=%s&width=${size}&height=${size}' % url_quote(str(${qwebExpr}) or 'No Data')`);
                        img.style.width = size + 'px';
                        img.style.height = size + 'px';
                        el.appendChild(img);

                        if (qr.config.caption) {
                            const caption = document.createElement('div');
                            caption.style.fontSize = '8pt';
                            caption.style.marginTop = '3px';
                            caption.style.textAlign = 'center';
                            caption.innerText = qr.config.caption;
                            el.appendChild(caption);
                        }

                        el.classList.add('report-qr');
                    } catch (e) {
                        console.error("[Cyllo Studio] QR Serialization failed", e);
                    }
                }
                el.classList.remove('s_qr_block', 'c_new', 'selected');
            }

            if (!keepStudioAttrs) {
                // studioAttrs.forEach(a => el.removeAttribute(a));
                el.removeAttribute('onmouseover');
                el.removeAttribute('onmouseout');
                el.removeAttribute('onclick');
                el.removeAttribute('contenteditable');
                if (el.style) {
                    if (el.style.cursor) el.style.removeProperty('cursor');
                    if (el.style.outline) el.style.removeProperty('outline');
                    if (el.style.opacity) el.style.removeProperty('opacity');
                    if (el.getAttribute('style') === '') el.removeAttribute('style');
                }
                if (el.classList) {
                    el.classList.remove('c_new', 'awaiting-config-block', 'selected');
                    if (el.getAttribute('class') === '') el.removeAttribute('class');
                }
            }

            const handles = el.querySelectorAll ? Array.from(el.querySelectorAll('.table-handle, .box-handle, .box-toolbar, .box-resize-handles, .box-resize-handle, .field-handle, .tcm-delete-table, .table-toolbar, .text-handle, .resize-handle, .field-delete, .table-handle-container, .table-delete, .field-handle-container, .qr-handle-container')) : [];
            handles.forEach(h => h.remove());

            // Unwrap wrappers

            // \u2500\u2500 Logo enrich wrapper: unwrap and persist hidden state as d-print-none \u2500\u2500
            if (el.classList && el.classList.contains('cy-logo-enrich-wrapper')) {
                if (el.parentNode) {
                    // Find the logo img inside the wrapper
                    const img = el.querySelector('img[alt="Logo"], .company_logo');
                    if (img) {
                        // Convert editor-side hidden marker to d-print-none for PDF output
                        if (img.classList.contains('cy-logo-hidden')) {
                            img.classList.remove('cy-logo-hidden');
                            img.classList.add('d-print-none');
                        }
                        // Remove UI-only elements before saving
                        el.querySelectorAll('.cy-canvas-remove-logo-btn, .cy-canvas-logo-restore-hint').forEach(n => n.remove());
                        // Unwrap: move img (and any siblings) back to parent
                        const children = Array.from(el.childNodes);
                        children.forEach(child => el.parentNode.insertBefore(child, el));
                        el.remove();
                        children.forEach(child => clean(child));
                        return;
                    }
                }
            }

            if (el.classList && el.classList.contains('table-wrapper')) {
                if (el.parentNode) {
                    const wasNew = el.classList.contains('c_new') || el.hasAttribute('data-cy-new-field');
                    const children = Array.from(el.childNodes);
                    const promotedChildren = [];

                    const isHidden = el.classList.contains('cy-block-hidden');
                    const isInactive = el.getAttribute('t-if') === 'False';
                    const isPbBefore = el.classList.contains('page-break-before');
                    const isPbAfter = el.classList.contains('page-break-after');

                    children.forEach(child => {
                        // Skip whitespace nodes introduced by the wrapper's HTML template
                        if (child.nodeType === 3 && !child.textContent.trim()) return;

                        if (child.tagName === 'TABLE' || (child.classList && child.classList.contains('table'))) {
                            if (isHidden) child.classList.add('d-print-none');
                            if (isInactive) child.setAttribute('t-if', 'False');
                            if (isPbBefore) child.classList.add('page-break-before');
                            if (isPbAfter) child.classList.add('page-break-after');
                        }

                        promotedChildren.push(child);
                        el.parentNode.insertBefore(child, el);
                    });
                    if (wasNew) {
                        const semanticChild = promotedChildren.find(child => {
                            if (!child || child.nodeType !== 1) return false;
                            return child.tagName === 'TABLE' || child.classList.contains('table');
                        });
                        if (semanticChild) markNewNode(semanticChild);
                    }
                    el.remove();
                    promotedChildren.forEach(child => clean(child));
                    return;
                }
            }
            // ── Box Section Container Serialization ──
            if (el.classList && el.classList.contains('box-section-wrapper')) {
                const wasNew = el.classList.contains('c_new') || el.hasAttribute('data-cy-new-field');
                let cfg = {};
                try { cfg = JSON.parse(el.dataset.boxConfig || '{}'); } catch (ex) { }
                const s = cfg.style || {};
                const layoutMode = cfg.layoutMode || 'free';

                // Build the output <div class="report-section">
                const section = document.createElement('div');
                section.className = 'report-section';

                const isHidden = el.classList.contains('cy-block-hidden');
                const isInactive = el.getAttribute('t-if') === 'False';
                const isPbBefore = el.classList.contains('page-break-before');
                const isPbAfter = el.classList.contains('page-break-after');

                if (isHidden) section.classList.add('d-print-none');
                if (isInactive) section.setAttribute('t-if', 'False');
                if (isPbBefore) section.classList.add('page-break-before');
                if (isPbAfter) section.classList.add('page-break-after');

                if (el.hasAttribute('cy-xpath')) section.setAttribute('cy-xpath', el.getAttribute('cy-xpath'));
                if (el.hasAttribute('cy-template')) section.setAttribute('cy-template', el.getAttribute('cy-template'));
                section.setAttribute('data-box-id', cfg.id || '');
                section.setAttribute('data-layout-mode', layoutMode);

                let styleStr = 'position:relative;';
                styleStr += 'box-sizing:border-box;';
                if (s.width) styleStr += `width:${s.width}px;`;
                if (s.height) styleStr += `height:${s.height}px;`;
                styleStr += `background-color:${s.backgroundColor || 'transparent'};`;
                if (s.border && s.border !== 'none') styleStr += `border:${s.border};`;
                if (s.borderRadius) styleStr += `border-radius:${s.borderRadius}px;`;
                if (s.padding) styleStr += `padding:${s.padding}px;`;
                if (s.marginTop) styleStr += `margin-top:${s.marginTop}px;`;
                if (layoutMode === 'flow') styleStr += 'display:flex;flex-direction:column;gap:8px;align-items:flex-start;';
                section.setAttribute('style', styleStr);

                // Move children from the dropzone into the section
                const dropzone = el.querySelector('.box-dropzone');
                if (dropzone) {
                    Array.from(dropzone.children).forEach(child => {
                        const childClone = child.cloneNode(true);
                        section.appendChild(childClone);
                    });
                }

                if (el.parentNode) {
                    if (wasNew) markNewNode(section);
                    el.parentNode.replaceChild(section, el);
                    // Recursively clean the children inside the new section
                    Array.from(section.children).forEach(child => clean(child));
                }
                return;
            }

            // ── Sign Node Serialization ──
            if (el.classList && el.classList.contains('sign-wrapper')) {
                const wasNew = el.classList.contains('c_new') || el.hasAttribute('data-cy-new-field');
                let cfg = {};
                try { cfg = JSON.parse(el.dataset.signConfig || '{}'); } catch (ex) { }

                const role = cfg.role || 'customer';
                const label = cfg.label || 'Authorized Signature';
                const alignment = cfg.alignment || 'left';
                const width = cfg.width || 200;

                const section = document.createElement('div');
                section.className = 'o_sign_placeholder';

                const isHidden = el.classList.contains('cy-block-hidden');
                const isInactive = el.getAttribute('t-if') === 'False';
                const isPbBefore = el.classList.contains('page-break-before');
                const isPbAfter = el.classList.contains('page-break-after');

                if (isHidden) section.classList.add('d-print-none');
                if (isInactive) section.setAttribute('t-if', 'False');
                if (isPbBefore) section.classList.add('page-break-before');
                if (isPbAfter) section.classList.add('page-break-after');
                if (el.hasAttribute('cy-xpath')) section.setAttribute('cy-xpath', el.getAttribute('cy-xpath'));
                if (el.hasAttribute('cy-template')) section.setAttribute('cy-template', el.getAttribute('cy-template'));
                section.setAttribute('data-role', role);

                // Style: width + alignment, clear box-model for PDF
                let styleStr = `display:inline-block; width:${width}px; text-align:${alignment}; vertical-align:top; padding:4px 0;`;
                section.setAttribute('style', styleStr);

                // Invisible backend-detection anchor ([[SIGN:role]] in 2pt white text)
                const anchor = document.createElement('span');
                anchor.setAttribute('style', 'color:white;font-size:2pt;line-height:1px;display:block;overflow:hidden;height:1px;');
                anchor.textContent = `[[SIGN:${role}]]`;
                section.appendChild(anchor);

                // Signature line (underscores) — clean static line, no t-if/t-else
                const sigLine = document.createElement('div');
                sigLine.setAttribute('style', 'border-bottom:1px solid #333;width:80%;margin:8px auto 4px;min-height:40px;');
                section.appendChild(sigLine);

                // Label
                const labelP = document.createElement('p');
                labelP.setAttribute('style', 'font-weight:bold;font-size:11pt;margin:2px 0 0;');
                labelP.textContent = label;
                section.appendChild(labelP);

                if (cfg.show_date) {
                    const dateP = document.createElement('p');
                    dateP.setAttribute('style', 'font-size:9pt;margin:2px 0 0;color:#555;');
                    dateP.textContent = 'Date: _______________';
                    section.appendChild(dateP);
                }

                if (cfg.show_name) {
                    const nameP = document.createElement('p');
                    nameP.setAttribute('style', 'font-size:9pt;margin:2px 0 0;color:#555;');
                    nameP.textContent = 'Name: _______________';
                    section.appendChild(nameP);
                }

                if (el.parentNode) {
                    if (wasNew) markNewNode(section);
                    el.parentNode.replaceChild(section, el);
                    Array.from(section.children).forEach(child => clean(child));
                }
                return;
            }

            // Legacy box-wrapper (old format) compat
            if (el.classList && el.classList.contains('box-wrapper')) {
                if (el.parentNode) {
                    const children = Array.from(el.childNodes);
                    children.forEach(child => el.parentNode.insertBefore(child, el));
                    el.remove();
                    children.forEach(child => clean(child));
                    return;
                }
            }
            if (!keepStudioAttrs && el.classList && (el.classList.contains('dynamic-field-wrapper') || el.classList.contains('field-block'))) {
                if (el.parentNode) {
                    const wasNew = el.classList.contains('c_new') || el.hasAttribute('data-cy-new-field');
                    const children = Array.from(el.childNodes);
                    const promotedChildren = [];

                    const isHidden = el.classList.contains('cy-block-hidden');
                    const isInactive = el.getAttribute('t-if') === 'False';
                    const isPbBefore = el.classList.contains('page-break-before');
                    const isPbAfter = el.classList.contains('page-break-after');

                    children.forEach(child => {
                        // Skip whitespace nodes
                        if (child.nodeType === 3 && !child.textContent.trim()) return;

                        // DISCARD the handle container completely — do not promote it!
                        if (child.nodeType === 1 && child.classList.contains('field-handle-container')) {
                            return;
                        }

                        // UNWRAP the field-container so the actual t-field element is promoted directly
                        if (child.nodeType === 1 && child.classList.contains('field-container')) {
                            Array.from(child.childNodes).forEach(gc => {
                                if (gc.nodeType === 3 && !gc.textContent.trim()) return;
                                if (gc.nodeType === 1) {
                                    if (isHidden) gc.classList.add('d-print-none');
                                    if (isInactive) gc.setAttribute('t-if', 'False');
                                    if (isPbBefore) gc.classList.add('page-break-before');
                                    if (isPbAfter) gc.classList.add('page-break-after');
                                }
                                promotedChildren.push(gc);
                                el.parentNode.insertBefore(gc, el);
                            });
                            return; // skip the field-container itself
                        }

                        // For any other valid children
                        if (child.nodeType === 1) {
                            if (isHidden) child.classList.add('d-print-none');
                            if (isInactive) child.setAttribute('t-if', 'False');
                            if (isPbBefore) child.classList.add('page-break-before');
                            if (isPbAfter) child.classList.add('page-break-after');
                        }

                        promotedChildren.push(child);
                        el.parentNode.insertBefore(child, el);
                    });
                    if (wasNew) {
                        const semanticChild = promotedChildren.find(child => child && child.nodeType === 1);
                        if (semanticChild) markNewNode(semanticChild);
                    }
                    el.remove();
                    promotedChildren.forEach(child => clean(child));
                    return;
                }
            }

            // Cleanup residual classes; convert editor-side hidden marker to real d-print-none
            if (!keepStudioAttrs && el.classList) {
                // cy-block-hidden is the editor-side marker; save as d-print-none in XML
                if (el.classList.contains('cy-block-hidden')) {
                    el.classList.add('d-print-none');
                    el.classList.remove('cy-block-hidden');
                }
                el.classList.remove('c_new', 'selected', 'bg-white');
                // if (!keepStudioAttrs && el.hasAttribute('data-cy-new-field')) el.removeAttribute('data-cy-new-field');
                if (el.classList.length === 0) el.removeAttribute('class');
            }

            if (el.hasAttribute && (el.hasAttribute('t-elif') || el.hasAttribute('t-else'))) {
                if (el.style && el.style.display === 'none') {
                    el.style.removeProperty('display');
                    if (el.getAttribute('style') === '') el.removeAttribute('style');
                }
            }

            if (el.children) {
                Array.from(el.children).forEach(child => {
                    if (child.hasAttribute && (child.hasAttribute('t-elif') || child.hasAttribute('t-else'))) {
                        let prev = child.previousSibling;
                        let nodesToMove = [];
                        while (prev) {
                            if (prev.nodeType === 1 && (prev.hasAttribute('t-if') || prev.hasAttribute('t-elif'))) {
                                break;
                            }
                            nodesToMove.unshift(prev);
                            prev = prev.previousSibling;
                        }
                        if (prev && nodesToMove.length > 0) {
                            let ref = child.nextSibling;
                            nodesToMove.forEach(n => el.insertBefore(n, ref));
                        }
                    }
                });
                Array.from(el.children).forEach(child => clean(child));
            }
        };
        clean(node);

        // Return to original position if it had one
        if (parent) {
            while (temp.firstChild) {
                parent.insertBefore(temp.firstChild, next);
            }
            return node;
        }
        return temp;
    }

    _isStructuralNode(el) {
        if (!el || !el.hasAttribute) return false;
        const tagName = el.tagName ? el.tagName.toLowerCase() : '';
        if (tagName === 't' || tagName === 'cy-qweb-t') return true;
        const qwebAttrs = ['t-foreach', 't-if', 't-elif', 't-else', 't-field', 't-esc', 't-out', 't-call'];
        return qwebAttrs.some(attr => el.hasAttribute(attr));
    }

    _enrichReportDOM(container) {
        // ── Enrich existing report-section boxes saved from previous edits ──
        container.querySelectorAll('div.report-section:not(.box-section-wrapper *)').forEach(section => {
            if (section.closest('.box-section-wrapper')) return;
            // Extract stored config from data attrs or build default
            let cfg;
            try { cfg = section.dataset.boxConfig ? JSON.parse(section.dataset.boxConfig) : null; } catch (e) { cfg = null; }
            if (!cfg) {
                const boxId = section.dataset.boxId || ('box_' + Math.random().toString(36).slice(2, 10));
                cfg = {
                    id: boxId, label: section.dataset.boxLabel || 'Section',
                    style: {
                        width: section.offsetWidth || 300,
                        height: section.offsetHeight || 200,
                        backgroundColor: section.style.backgroundColor || 'transparent',
                        border: section.style.border || '1px solid #ccc',
                        borderRadius: parseInt(section.style.borderRadius) || 4,
                        padding: parseInt(section.style.padding) || 8,
                        marginTop: parseInt(section.style.marginTop) || 16,
                    },
                    layoutMode: section.dataset.layoutMode || 'free',
                    children: [],
                };
            }

            // Grab all children before replace
            const childNodes = Array.from(section.children);

            const wrapper = document.createElement('div');
            wrapper.className = 'box-section-wrapper';
            wrapper.setAttribute('cy-type', 'box');
            if (section.hasAttribute('cy-xpath')) wrapper.setAttribute('cy-xpath', section.getAttribute('cy-xpath'));
            if (section.hasAttribute('cy-template')) wrapper.setAttribute('cy-template', section.getAttribute('cy-template'));
            wrapper.setAttribute('data-box-id', cfg.id);
            wrapper.setAttribute('data-box-config', JSON.stringify(cfg));
            wrapper.style.width = (cfg.style.width || 300) + 'px';
            wrapper.style.height = (cfg.style.height || 200) + 'px';
            wrapper.style.marginTop = (cfg.style.marginTop !== undefined ? cfg.style.marginTop : 16) + 'px';
            wrapper.innerHTML = this._buildBoxInnerHTML(cfg);

            section.parentNode.insertBefore(wrapper, section);
            section.remove();

            // Move original children into the new dropzone
            const dropzone = wrapper.querySelector('.box-dropzone');
            childNodes.forEach(child => dropzone.appendChild(child));

            // Wire delete
            wrapper.querySelector('.box-delete-btn').onclick = (e) => {
                e.stopPropagation();
                this.dialog.add(ConfirmationDialog, {
                    body: 'Delete this section container and all its contents?',
                    confirm: () => {
                        if (this._selectedBoxEl === wrapper) this.closeBoxProps();
                        wrapper.remove();
                    },
                    cancel: () => { },
                });
            };
            this._setupBoxResizeHandles(wrapper);
        });

        // ── Enrich existing report-qr from previous edits ──
        container.querySelectorAll('div.report-qr:not(.s_qr_block)').forEach(qrDiv => {
            let qrConfig = null;
            try {
                if (qrDiv.dataset.qrConfig) {
                    qrConfig = JSON.parse(qrDiv.dataset.qrConfig);
                }
            } catch (e) { }

            if (qrConfig) {
                this.insertQrBlock(qrDiv, qrConfig, 'enrich');
            }
        });

        // ── Enrich existing o_sign_placeholder from previous saves ──
        container.querySelectorAll('div.o_sign_placeholder:not(.sign-wrapper)').forEach(placeholder => {
            if (placeholder.closest('.sign-wrapper')) return;
            const role = placeholder.dataset.role || 'customer';
            // Parse existing cfg from style
            const existingStyle = placeholder.getAttribute('style') || '';
            const widthMatch = existingStyle.match(/width:\s*(\d+)px/);
            const alignMatch = existingStyle.match(/text-align:\s*(\w+)/);
            // Look for label in existing children
            const labelEl = placeholder.querySelector('p');
            const labelText = labelEl ? labelEl.textContent.trim() : 'Authorized Signature';

            const signId = 'sign_' + Math.random().toString(36).slice(2, 10);
            const cfg = {
                role,
                label: labelText,
                required: true,
                show_date: false,
                show_name: false,
                width: widthMatch ? parseInt(widthMatch[1]) : 200,
                height: 100,
                alignment: alignMatch ? alignMatch[1] : 'left',
            };

            const wrapper = document.createElement('div');
            wrapper.className = 'sign-wrapper';
            wrapper.setAttribute('cy-type', 'sign');
            if (placeholder.hasAttribute('cy-xpath')) wrapper.setAttribute('cy-xpath', placeholder.getAttribute('cy-xpath'));
            if (placeholder.hasAttribute('cy-template')) wrapper.setAttribute('cy-template', placeholder.getAttribute('cy-template'));
            wrapper.setAttribute('data-sign-id', signId);
            wrapper.setAttribute('data-sign-config', JSON.stringify(cfg));
            wrapper.dataset.role = role;
            wrapper.style.width = cfg.width + 'px';
            wrapper.style.height = cfg.height + 'px';
            wrapper.style.cursor = 'default';
            wrapper.style.textAlign = cfg.alignment;

            wrapper.innerHTML = `
                <div class="sign-toolbar" contenteditable="false">
                    <span class="sign-drag-handle ri-drag-move-line" title="Drag to move"></span>
                    <span class="sign-settings-btn ri-settings-3-line" title="Settings" style="cursor: pointer; margin: 0 4px;"></span>
                    <span class="sign-delete-btn ri-delete-bin-line" title="Delete Signature"></span>
                </div>
                <div class="sign-content-wrapper" style="pointer-events: none; border: 2px dashed #ccc; width: 100%; height: 100%; padding: 10px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; position: relative;">
                    <div class="sign-watermark" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); opacity: 0.1; font-size: 40px; color: #9ea700;"><i class="fa fa-pencil"></i></div>
                    <div class="sign-role-badge" style="position: absolute; top: -10px; right: 10px; background: #9ea700; color: white; padding: 2px 6px; font-size: 10px; border-radius: 4px; text-transform: uppercase;">${role}</div>
                    <div class="sign-empty-line" style="border-bottom: 1px solid #333; width: 80%; margin: 10px auto;"></div>
                    <p class="sign-label" style="font-weight: bold; font-size: 14px; margin: 0;">${labelText}</p>
                </div>
                <div class="sign-resize-handles" contenteditable="false">
                    <div class="sign-resize-handle" data-dir="se"></div>
                </div>
            `;

            wrapper.querySelector('.sign-delete-btn').onclick = (e) => {
                e.stopPropagation();
                this.dialog.add(ConfirmationDialog, {
                    body: 'Delete this Signature?',
                    confirm: () => {
                        if (this.state.showSignProps && this._selectedSignEl === wrapper) {
                            this.closeSignProps();
                        }
                        wrapper.remove();
                        this._updateHasSign();
                    },
                    cancel: () => { },
                });
            };

            placeholder.parentNode.insertBefore(wrapper, placeholder);
            placeholder.remove();
            this._setupSignResizeHandles(wrapper);
        });

        const tables = container.querySelectorAll('table:not(.table-wrapper table)');
        tables.forEach(table => {
            if (table.closest('.table-wrapper')) return;
            // Skip tables inside studio UI shells
            if (table.closest('.cy-custom-footer') || table.closest('.cy-footer-preview-wrapper') || table.closest('.cy-report-header')) return;
            let targetNode = table;
            while (targetNode.parentElement && this._isStructuralNode(targetNode.parentElement) &&
                targetNode.parentElement.children.length === 1 &&
                !targetNode.parentElement.classList.contains('page')) {
                targetNode = targetNode.parentElement;
            }
            const wrapper = document.createElement('div');
            wrapper.className = 'table-wrapper';

            // Re-hydrate visibility state from the saved table onto the wrapper
            const tblHidden = targetNode.classList.contains('d-print-none');
            const tblInactive = targetNode.getAttribute('t-if') === 'False';
            const tblPbBefore = targetNode.classList.contains('page-break-before');
            const tblPbAfter = targetNode.classList.contains('page-break-after');
            if (tblHidden) { wrapper.classList.add('cy-block-hidden'); targetNode.classList.remove('d-print-none'); }
            if (tblInactive) { wrapper.setAttribute('t-if', 'False'); }
            if (tblPbBefore) { wrapper.classList.add('page-break-before'); targetNode.classList.remove('page-break-before'); }
            if (tblPbAfter) { wrapper.classList.add('page-break-after'); targetNode.classList.remove('page-break-after'); }

            wrapper.innerHTML = `
                <div class="table-handle-container" contenteditable="false">
                    <div class="table-handle ri-drag-move-line" title="Drag to move"></div>
                    <div class="table-settings ri-settings-3-line" title="Settings"></div>
                    <div class="table-delete ri-delete-bin-line" title="Delete Table"></div>
                </div>`;
            targetNode.parentNode.insertBefore(wrapper, targetNode);
            wrapper.appendChild(targetNode);
            wrapper.querySelector('.table-delete').onclick = (e) => {
                e.stopPropagation();
                this.dialog.add(ConfirmationDialog, {
                    body: "Are you sure you want to delete this table?",
                    confirm: async () => {
                        this._removeOrphanedQwebElements && this._removeOrphanedQwebElements(wrapper);
                        wrapper.remove();
                        await this.save_changes(this);
                    },
                    cancel: () => { },
                });
            };
        });

        const fields = container.querySelectorAll('[t-field]:not(.field-block [t-field]):not(.field-container [t-field]), [t-esc]:not(.field-block [t-esc]):not(.field-container [t-esc])');
        fields.forEach(field => {
            if (field.closest('.field-block') || field.closest('table')) return;
            // Skip elements inside studio UI shells (custom footer preview, header)
            if (field.closest('.cy-custom-footer') || field.closest('.cy-footer-preview-wrapper') || field.closest('.cy-report-header')) return;
            let targetNode = field;
            while (targetNode.parentElement && this._isStructuralNode(targetNode.parentElement) &&
                targetNode.parentElement.children.length === 1 &&
                !targetNode.parentElement.classList.contains('page')) {
                targetNode = targetNode.parentElement;
            }
            const wrapper = document.createElement('div');
            wrapper.className = 'field-block dynamic-field-wrapper';

            // Re-hydrate visibility from saved element
            const fldHidden = targetNode.classList.contains('d-print-none');
            const fldInactive = targetNode.getAttribute('t-if') === 'False';
            if (fldHidden) { wrapper.classList.add('cy-block-hidden'); targetNode.classList.remove('d-print-none'); }
            if (fldInactive) { wrapper.setAttribute('t-if', 'False'); }

            // ── Propagate cy-xpath/cy-template so node.closest('[cy-xpath]') never skips
            // this wrapper and lands on the wrong ancestor (e.g. the t-call node that
            // carries the parent template's cy-template instead of the sub-template's).
            if (targetNode.hasAttribute('cy-xpath')) wrapper.setAttribute('cy-xpath', targetNode.getAttribute('cy-xpath'));
            if (targetNode.hasAttribute('cy-template')) wrapper.setAttribute('cy-template', targetNode.getAttribute('cy-template'));

            wrapper.innerHTML = `
                <div class="field-handle-container" contenteditable="false">
                    <span class="field-handle ri-drag-move-line" title="Drag to move"></span>
                    <span class="field-settings ri-settings-3-line" title="Settings" style="cursor: pointer; margin: 0 4px;"></span>
                    <span class="field-delete ri-delete-bin-line" title="Delete Field"></span>
                </div>
                <div class="field-container"></div>
            `;
            targetNode.parentNode.insertBefore(wrapper, targetNode);
            wrapper.querySelector('.field-container').appendChild(targetNode);

            // Clear cy-xpath/cy-template from targetNode so the wrapper is the sole
            // owner anchor for this zone — prevents double-counting in getChangedElements.
            targetNode.removeAttribute('cy-xpath');
            targetNode.removeAttribute('cy-template');
            wrapper.querySelector('.field-delete').onclick = (e) => {
                e.stopPropagation();
                this.dialog.add(ConfirmationDialog, {
                    body: "Are you sure you want to delete this field?",
                    confirm: () => wrapper.remove(),
                    cancel: () => { },
                });
                // if (confirm("Delete this field?")) wrapper.remove();
            };
        });

        const fieldContainers = container.querySelectorAll('.field-container:not(.field-block .field-container)');
        fieldContainers.forEach(fc => {
            if (fc.closest('.field-block') || fc.closest('table')) return;
            // Skip elements inside studio UI shells
            if (fc.closest('.cy-custom-footer') || fc.closest('.cy-footer-preview-wrapper') || fc.closest('.cy-report-header')) return;
            let targetNode = fc;
            while (targetNode.parentElement && this._isStructuralNode(targetNode.parentElement) &&
                targetNode.parentElement.children.length === 1 &&
                !targetNode.parentElement.classList.contains('page')) {
                targetNode = targetNode.parentElement;
            }
            const wrapper = document.createElement('div');
            wrapper.className = 'field-block dynamic-field-wrapper';

            // Re-hydrate visibility from saved fieldContainer
            const fcHidden = targetNode.classList.contains('d-print-none');
            const fcInactive = targetNode.getAttribute('t-if') === 'False';
            if (fcHidden) { wrapper.classList.add('cy-block-hidden'); targetNode.classList.remove('d-print-none'); }
            if (fcInactive) { wrapper.setAttribute('t-if', 'False'); }

            // ── Propagate cy-xpath/cy-template
            if (targetNode.hasAttribute('cy-xpath')) wrapper.setAttribute('cy-xpath', targetNode.getAttribute('cy-xpath'));
            if (targetNode.hasAttribute('cy-template')) wrapper.setAttribute('cy-template', targetNode.getAttribute('cy-template'));

            wrapper.innerHTML = `
                <div class="field-handle-container" contenteditable="false">
                    <span class="field-handle ri-drag-move-line" title="Drag to move"></span>
                    <span class="field-settings ri-settings-3-line" title="Settings" style="cursor: pointer; margin: 0 4px;"></span>
                    <span class="field-delete ri-delete-bin-line" title="Delete Field"></span>
                </div>
            `;
            // targetNode.parentNode.insertBefore(targetNode, wrapper);
            targetNode.parentNode.insertBefore(wrapper, targetNode);
            wrapper.appendChild(targetNode);

            targetNode.removeAttribute('cy-xpath');
            targetNode.removeAttribute('cy-template');
            wrapper.querySelector('.field-delete').onclick = (e) => {
                e.stopPropagation();
                this.dialog.add(ConfirmationDialog, {
                    body: "Are you sure you want to delete this field?",
                    confirm: () => wrapper.remove(),
                    cancel: () => { },
                });
            };
        });

        container.querySelectorAll('.text-node').forEach(n => n.setAttribute('contenteditable', 'false'));

        // \u2500\u2500 Enrich the report canvas logo (img[alt="Logo"] from external_layout) \u2500\u2500
        const reportLogoImgs = container.querySelectorAll('img[alt="Logo"], .company_logo');
        reportLogoImgs.forEach(logoImg => {
            // Skip if already wrapped
            if (logoImg.closest('.cy-logo-enrich-wrapper')) return;

            // Create wrapper
            const wrapper = document.createElement('div');
            wrapper.className = 'cy-logo-enrich-wrapper';
            wrapper.style.display = 'inline-block';
            wrapper.style.position = 'relative';
            wrapper.style.cursor = 'pointer';
            wrapper.title = 'Click to manage logo';

            // Add hover effects
            wrapper.onmouseover = () => {
                wrapper.style.outline = '2px dashed #007bff';
                wrapper.style.outlineOffset = '2px';
            };
            wrapper.onmouseout = () => {
                wrapper.style.outline = '';
            };

            // Move logo into wrapper
            logoImg.parentNode.insertBefore(wrapper, logoImg);
            wrapper.appendChild(logoImg);

            // Add overlay buttons based on state
            if (this.state.hideLogo || logoImg.getAttribute('cy-logo-removed') === '1') {
                logoImg.classList.add('cy-logo-hidden');
                logoImg.style.setProperty('display', 'none', 'important');

                // Add restore hint
                const restoreHint = document.createElement('div');
                restoreHint.className = 'cy-canvas-logo-restore-hint';
                restoreHint.style.cssText = 'padding: 10px; border: 2px dashed #ccc; background: #f9f9f9; min-width: 100px; text-align: center; cursor: pointer;';
                restoreHint.textContent = 'Logo hidden — click to restore';
                wrapper.appendChild(restoreHint);

                restoreHint.onclick = (e) => {
                    e.stopPropagation();
                    this.state.hideLogo = false;
                    logoImg.removeAttribute('cy-logo-removed');
                    logoImg.classList.remove('cy-logo-hidden');
                    logoImg.style.removeProperty('display');
                    restoreHint.remove();
                    if (this.undoManager) this.undoManager.debouncedSave();
                };
            } else {
                logoImg.classList.remove('cy-logo-hidden');
                logoImg.style.removeProperty('display');

                // Add remove button
                const removeBtn = document.createElement('button');
                removeBtn.className = 'cy-canvas-remove-logo-btn';
                removeBtn.innerHTML = '×';
                removeBtn.style.cssText = 'position: absolute; top: -8px; right: -8px; width: 20px; height: 20px; border-radius: 50%; background: #dc3545; color: white; border: none; cursor: pointer; font-size: 14px; line-height: 1; display: flex; align-items: center; justify-content: center; z-index: 10;';
                wrapper.appendChild(removeBtn);

                removeBtn.onclick = (e) => {
                    e.stopPropagation();
                    this.state.hideLogo = true;
                    logoImg.classList.add('cy-logo-hidden');
                    logoImg.style.setProperty('display', 'none', 'important');
                    removeBtn.remove();

                    // Add restore hint
                    const restoreHint = document.createElement('div');
                    restoreHint.className = 'cy-canvas-logo-restore-hint';
                    restoreHint.style.cssText = 'padding: 10px; border: 2px dashed #ccc; background: #f9f9f9; min-width: 100px; text-align: center; cursor: pointer;';
                    restoreHint.textContent = 'Logo hidden — click to restore';
                    wrapper.appendChild(restoreHint);

                    restoreHint.onclick = (e) => {
                        e.stopPropagation();
                        this.state.hideLogo = false;
                        logoImg.removeAttribute('cy-logo-removed');
                        logoImg.classList.remove('cy-logo-hidden');
                        logoImg.style.removeProperty('display');
                        restoreHint.remove();

                        // Re-add remove button
                        wrapper.appendChild(removeBtn);
                        if (this.undoManager) this.undoManager.debouncedSave();
                    };

                    if (this.undoManager) this.undoManager.debouncedSave();
                };
            }
        });
    }

    _formatCompanyInfo(co) {
        return [
            co.street,
            co.city,
            co.phone ? '\u260e ' + co.phone : '',
            co.email ? '\u2709 ' + co.email : '',
            co.website ? '\uD83C\uDF10 ' + co.website : ''
        ].filter(Boolean).join('\n');
    }

    async saveCompanyFooter(silent = false) {
        try {
            this.state.hasCustomFooter = true;
            await this.save_changes(this);
            if (!silent) {
                this.notification.add('Footer text updated successfully for this report', { type: 'success' });
            }

            // Re-render preview strip and iframe footer
            this._updateFooterInIframe();
            // Re-fetch iframe if previewing
            if (this.state.previewMode) {
                this._fetchPreviewData();
            }
        } catch (e) {
            console.error('[Cyllo Studio] Save footer error:', e);
            this.notification.add('Failed to update report footer', { type: 'danger' });
        }
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Box Section: Resize Handles
    // ──────────────────────────────────────────────────────────────────────────

    /**
     * Wire up pointer-based resize logic for all 8 handles on a box wrapper.
     * Stores result back into data-box-config.
     */

    _buildNewNodesXpath(change, newNodes) {
        if (!newNodes || !newNodes.length) return "";
        const children = Array.from(change.el.children);
        const findXpathNode = (node) => {
            if (!node) return null;

            // Only anchor to a DIRECT-CHILD sibling that carries its own cy-xpath.
            // Descending into descendants (querySelector) returns a deep grandchild
            // path such as ".../div[10]/p[2]/span". Using that as a before/after
            // anchor inserts the new node at the wrong nesting level AND yields a
            // positional path Odoo's inheritance engine cannot resolve, raising
            // "Element cannot be located in parent view" on save. If a direct child
            // lacks cy-xpath, processGroup simply scans to the next eligible sibling
            // (and ultimately falls back to position="inside" on the zone).
            if (node.hasAttribute?.("cy-xpath")) {
                return node;
            }

            return null;
        };
        let xpathBlock = "";
        let currentGroup = [];
        const isNewNode = (node) => !!(node && node.nodeType === 1 && (
            node.classList.contains('c_new') || node.hasAttribute('data-cy-new-field')
        ));
        const processGroup = (group) => {
            if (!group.length) return;
            let groupContent = "";
            group.forEach(node => {
                const cloned = node.cloneNode(true);
                // Create a temporary parent so _cleanStudioAttrs can replace/unwrap the node if needed
                const tempDiv = document.createElement('div');
                tempDiv.appendChild(cloned);
                this._cleanStudioAttrs(tempDiv.firstElementChild);
                // After cleaning, tempDiv contains the cleaned (and potentially unwrapped) nodes
                let content = tempDiv.innerHTML.replace(/ xmlns="[^"]*"/g, "").replace(/<br>/gi, '<br/>');
                groupContent += content;
            });

            const firstNodeIndex = children.indexOf(group[0]);
            const lastNodeIndex = children.indexOf(group[group.length - 1]);

            // Find next sibling with cy-xpath
            // let nextSibling = null;
            // for (let i = lastNodeIndex + 1; i < children.length; i++) {
            //     if (children[i].hasAttribute('cy-xpath') && !isNewNode(children[i]) && !this._isStructuralNode(children[i])) {
            //         nextSibling = children[i];
            //         break;
            //     }
            // }
            let nextSibling = null;

            for (let i = lastNodeIndex + 1; i < children.length; i++) {

                const xpathNode = findXpathNode(children[i]);

                if (
                    xpathNode &&
                    !isNewNode(xpathNode) &&
                    !this._isStructuralNode(xpathNode)
                ) {
                    nextSibling = xpathNode;
                    break;
                }
            }

            if (nextSibling) {
                xpathBlock += `<xpath expr="${nextSibling.getAttribute('cy-xpath')}" position="before">${groupContent}</xpath>`;
                return;
            }

            // Find prev sibling with cy-xpath
            let prevSibling = null;

            for (let i = firstNodeIndex - 1; i >= 0; i--) {

                const xpathNode = findXpathNode(children[i]);

                if (
                    xpathNode &&
                    !isNewNode(xpathNode) &&
                    !this._isStructuralNode(xpathNode)
                ) {
                    prevSibling = xpathNode;
                    break;
                }
            }
            // let prevSibling = null;
            // for (let i = firstNodeIndex - 1; i >= 0; i--) {
            //     if (children[i].hasAttribute('cy-xpath') && !isNewNode(children[i]) && !this._isStructuralNode(children[i])) {
            //         prevSibling = children[i];
            //         break;
            //     }
            // }

            if (prevSibling) {
                xpathBlock += `<xpath expr="${prevSibling.getAttribute('cy-xpath')}" position="after">${groupContent}</xpath>`;
                return;
            }

            // Fallback to parent inside
            xpathBlock += `<xpath expr="${change.xpath}" position="inside">${groupContent}</xpath>`;
        };

        children.forEach(child => {
            if (isNewNode(child) && !child.hasAttribute('cy-xpath')) {
                currentGroup.push(child);
            } else {
                processGroup(currentGroup);
                currentGroup = [];
            }
        });
        processGroup(currentGroup);
        return xpathBlock;
    }

    buildInheritanceXML(changes) {
        let new_inherits = [];
        for (const [key, items] of Object.entries(groupBy(changes, 'template'))) {
            let xpathBlock = "";
            items.forEach(change => {
                const markerNodes = Array.from(change.el.querySelectorAll('.c_new:not([cy-xpath]), [data-cy-new-field]:not([cy-xpath])'));
                const newNodes = Array.from(change.el.children)
                    .filter(child => markerNodes.includes(child));

                // ── Deletion: emit position="replace" with empty body ──────
                if (change.isDeleted) {
                    xpathBlock += `<xpath expr="${change.xpath}" position="replace"></xpath>`;
                    return;
                }

                // ── Inline style change (Block Settings colour/bg/width…) ──
                if (change.styleOnly) {
                    if (change.styleValue) {
                        xpathBlock += `<xpath expr="${change.xpath}" position="attributes"><attribute name="style">${escapeHtml(change.styleValue)}</attribute></xpath>`;
                    } else {
                        xpathBlock += `<xpath expr="${change.xpath}" position="attributes"><attribute name="style"/></xpath>`;
                    }
                    return;
                }

                if (newNodes.length) {
                    // xpathBlock += this._buildNewNodesXpath(change, newNodes);
                    const block = this._buildNewNodesXpath(change, newNodes);
                    xpathBlock += block;
                    return;
                }

                if (change.structChanged) {
                    // Secondary guard: never do a full position="replace" on a zone that still has
                    // QWeb structural (t-foreach / t-set / t-if / t-elif / t-else)
                    // descendants in the live DOM.
                    const structuralAttrs = [
                        't-foreach', 't-set', 't-if', 't-elif', 't-else', 't-call', 't-as', 't-value'
                    ];
                    const hasStructuralDescendant = structuralAttrs.some(attr =>
                        change.el.querySelector(`cy-qweb-t[${attr}], t[${attr}]`)
                    );

                    // Extra check: if ANY direct child of this zone is a t-if/t-elif/
                    // t-else node, never replace the zone — the sibling chain would break.
                    const hasConditionalChainChild = Array.from(change.el.children).some(c => {
                        const tag = (c.tagName || '').toLowerCase();
                        if (tag !== 'cy-qweb-t' && tag !== 't') return false;
                        return c.hasAttribute('t-if') || c.hasAttribute('t-elif') || c.hasAttribute('t-else');
                    });

                    // If zone contains a table with QWeb directives, the browser HTML
                    // parser hoists <t t-foreach/t-if> out of <tbody>, breaking the t-if/t-elif
                    // sibling chain. A position="replace" on such a zone produces invalid QWeb.
                    // Always fall back to sibling-relative positioning or inside positioning in this case.
                    const hasQwebTable = !!(change.el.querySelector && change.el.querySelector(
                        'table t[t-foreach], table t[t-if], table t[t-elif], ' +
                        'table cy-qweb-t[t-foreach], table cy-qweb-t[t-if], table cy-qweb-t[t-elif]'
                    ));

                    if (hasStructuralDescendant || hasConditionalChainChild || hasQwebTable) {
                        // Fall back to saving only genuinely new user-added nodes with precise sibling positioning.
                        // Any non-new structural edits in this zone are already captured by the node-level diffs.
                        // xpathBlock += this._buildNewNodesXpath(change, newNodes);
                        const block = this._buildNewNodesXpath(change, newNodes);
                        xpathBlock += block;
                        return;
                    }

                    const clonedZone = change.el.cloneNode(true);
                    const holder = document.createElement('div');  // parent so _cleanStudioAttrs unwraps its temp span
                    holder.appendChild(clonedZone);
                    this._cleanStudioAttrs(holder.firstElementChild);
                    let content = holder.innerHTML.replace(/ xmlns="[^"]*"/g, "").replace(/<br>/gi, '<br/>');
                    xpathBlock += `<xpath expr="${change.xpath}" position="replace">${content}</xpath>`;
                    return;
                }

                // ── Attribute-only change (visibility/t-if on existing cy-xpath element) ──
                if (change.attrOnly) {
                    // change.isHidden = cy-block-hidden was on wrapper (maps to d-print-none in saved XML)
                    // change.tif = t-if value on the wrapper
                    if (change.isHidden) {
                        xpathBlock += `<xpath expr="${change.xpath}" position="attributes"><attribute name="class" add="d-print-none" separator=" "/></xpath>`;
                    } else {
                        xpathBlock += `<xpath expr="${change.xpath}" position="attributes"><attribute name="class" remove="d-print-none" separator=" "/></xpath>`;
                    }
                    if (change.tif === 'False') {
                        xpathBlock += `<xpath expr="${change.xpath}" position="attributes"><attribute name="t-if">False</attribute></xpath>`;
                    } else {
                        // Clear t-if if previously set to False
                        xpathBlock += `<xpath expr="${change.xpath}" position="attributes"><attribute name="t-if"/></xpath>`;
                    }
                    return;
                }

                if (this._isStructuralNode(change.el)) return;
                const cloned = change.el.cloneNode(true);
                const holder = document.createElement('div');  // parent so _cleanStudioAttrs unwraps its temp span
                holder.appendChild(cloned);
                this._cleanStudioAttrs(holder.firstElementChild);
                let content = holder.innerHTML.replace(/ xmlns="[^"]*"/g, "").replace(/<br>/gi, '<br/>');
                xpathBlock += `<xpath expr="${change.xpath}" position="replace">${content}</xpath>`;
            });
            if (xpathBlock.trim()) {
                new_inherits.push({
                    key,
                    xpathBlocks: `<data>\n${xpathBlock}\n</data>`,
                    hasTemplateInfo: true,
                });
            }
        }


        // ── INJECT CUSTOM FOOTER XPATH ──
        // The footer must be anchored to the *document* template (the inner
        // template that contains the <div class="page">) — NOT the outer wrapper.
        // Using _template (wrapper) causes "cannot be located in parent view"
        // because the wrapper arch does not contain the .page div.
        let footerTemplateKey = this._docTemplate || this._template;
        let pageXpath = "(//div[hasclass('page')])[1]";

        // ── Resolve footer template key and page xpath from the live iframe DOM ──
        // Always prefer the iframe DOM over traversing change elements — this ensures
        // the footer is anchored to the correct sub-template even when changes.length === 0
        // (pure footer-only saves, e.g. toggling Company Footer toggle then autosave).
        let foundValidTemplate = false;
        try {
            if (this.reportFrameRef && this.reportFrameRef.el) {
                const ifrDoc = this.reportFrameRef.el.tagName === 'IFRAME'
                    ? (this.reportFrameRef.el.contentDocument || this.reportFrameRef.el.contentWindow.document)
                    : null;
                if (ifrDoc) {
                    const pageEl = ifrDoc.querySelector('.page[cy-xpath]');
                    if (pageEl) {
                        pageXpath = pageEl.getAttribute('cy-xpath');
                        if (pageEl.hasAttribute('cy-template')) {
                            footerTemplateKey = pageEl.getAttribute('cy-template');
                        }
                        foundValidTemplate = true;
                    }
                }
            }
        } catch (e) {
            console.warn('[Cyllo Studio] Error resolving page xpath from iframe DOM:', e);
        }

        // Fallback: if not found in iframe, derive from the first change element
        if (!foundValidTemplate && changes && changes.length > 0) {
            const firstChange = changes[0];
            footerTemplateKey = firstChange.template;
            try {
                let el = firstChange.el;
                while (el) {
                    if (el.classList && el.classList.contains('page') && el.hasAttribute && el.hasAttribute('cy-xpath')) {
                        pageXpath = el.getAttribute('cy-xpath');
                        foundValidTemplate = true;
                        break;
                    }
                    if (el.hasAttribute && el.hasAttribute('cy-template')) {
                        footerTemplateKey = el.getAttribute('cy-template');
                    }
                    el = el.parentElement;
                }
            } catch (e) {
                console.warn('[Cyllo Studio] Error finding page element from changes:', e);
            }
        }

        let mainInherit = new_inherits.find(h => h.key === footerTemplateKey);
        if (!mainInherit) {
            mainInherit = { key: footerTemplateKey, xpathBlocks: "<data>\n</data>", hasTemplateInfo: true };
            new_inherits.push(mainInherit);
        }

        // Clean out any existing custom footer xpaths from the payload to prevent duplicates.
        // IMPORTANT: Only remove xpaths whose content specifically refers to cy-custom-footer.
        // Do NOT remove all page-anchored xpaths — that would wipe real DOM changes too.
        let parser = new DOMParser();
        let doc;
        let parseFailed = false;
        try {
            doc = parser.parseFromString(mainInherit.xpathBlocks, "application/xml");
            if (doc.querySelector('parsererror')) {
                parseFailed = true;
            } else {
                doc.querySelectorAll('xpath').forEach(xpathEl => {
                    const hasFooterContent = (
                        xpathEl.innerHTML.includes('cy-custom-footer') ||
                        xpathEl.innerHTML.includes('cy-footer-hide-std')
                    );
                    if (hasFooterContent) {
                        xpathEl.remove();
                    }
                });
            }
        } catch (e) {
            parseFailed = true;
        }

        const showF = this.state.footerShowReportFooter;
        const showD = this.state.footerShowDocName;
        const showP = this.state.footerShowPageNum;

        const encodedText = this.state.hasCustomFooter ? encodeURIComponent(this.state.companyReportFooterText || '') : '';

        // IMPORTANT: Use position="after" on the .page div so the footer is rendered
        // BELOW the page content, not appended inside it. Using position="inside"
        // causes the footer to appear at the bottom of the content body and overlap
        // existing content on reports that have long content.
        let footerXml = '';

        if (showF || showP || showD) {
            footerXml = `
                <xpath expr="${pageXpath}" position="after">
                    <div class="footer cy-custom-footer" data-show-footer="${showF}" data-show-doc="${showD}" data-show-page="${showP}" data-has-custom="${this.state.hasCustomFooter ? 'true' : 'false'}" data-custom-text="${encodedText}" style="width: 100%; font-size: 12px; padding: 8px 15px; border-top: 1px solid #e0e0e0; margin-top: 8px;">
                        <div class="row">
                            <div class="col-8 text-start cy-footer-text-content">
                                <t t-if="${showF ? 'True' : 'False'}">
                                    ${this.state.hasCustomFooter
                    ? `<span>${escapeHtml(this.state.companyReportFooterText)}</span>`
                    : '<span t-field="res_company.report_footer"/>'}
                                </t>
                                <t t-if="${showF && showD ? 'True' : 'False'}"><span> | </span></t>
                                <t t-if="${showD ? 'True' : 'False'}"><span t-esc="o.name"/></t>
                            </div>
                            <div class="col-4 text-end">
                                <t t-if="${showP ? 'True' : 'False'}"><div class="text-muted">Page: <span class="page"/> / <span class="topage"/></div></t>
                            </div>
                        </div>
                    </div>
                    <!-- Suppress the Odoo standard footer so only our custom footer shows -->
                    <style class="cy-footer-hide-std">.footer.o_standard_footer, footer.o_standard_footer { display: none !important; }</style>
                </xpath>
            `;
        } else {
            footerXml = `
                <xpath expr="${pageXpath}" position="after">
                    <div class="footer cy-custom-footer" data-show-footer="${showF}" data-show-doc="${showD}" data-show-page="${showP}" data-has-custom="${this.state.hasCustomFooter ? 'true' : 'false'}" data-custom-text="${encodedText}" style="display: none;"/>
                </xpath>
            `;
        }
        if (parseFailed) {
            console.error('[Cyllo Studio] xpathBlocks failed strict-XML parsing for key', mainInherit.key, '— using string-based footer cleanup to avoid discarding unsaved changes. Raw value:', mainInherit.xpathBlocks);
            let cleaned = mainInherit.xpathBlocks.replace(
                /<xpath\b[^>]*>[\s\S]*?(?:cy-custom-footer|cy-footer-hide-std)[\s\S]*?<\/xpath>/g,
                ''
            );
            mainInherit.xpathBlocks = cleaned.includes('</data>')
                ? cleaned.replace('</data>', footerXml + '\n</data>')
                : cleaned.replace('<data/>', '<data>\n' + footerXml + '\n</data>');
        } else {
            try {
                const footerDoc = parser.parseFromString(footerXml, "application/xml");
                if (footerDoc.documentElement && footerDoc.documentElement.nodeName !== 'parsererror') {
                    doc.documentElement.appendChild(footerDoc.documentElement);
                } else {
                    console.warn('[Cyllo Studio] Error parsing footer XML:', footerDoc.documentElement.textContent);
                }
                mainInherit.xpathBlocks = new XMLSerializer().serializeToString(doc);
            } catch (e) {
                console.error('[Cyllo Studio] Failed to append footer XML:', e);
                // Fallback to string concatenation if DOM append fails
                let serialized = new XMLSerializer().serializeToString(doc);
                if (serialized.includes('</data>')) {
                    mainInherit.xpathBlocks = serialized.replace('</data>', footerXml + '\n</data>');
                } else {
                    mainInherit.xpathBlocks = serialized.replace('<data/>', '<data>\n' + footerXml + '\n</data>');
                }
            }
        }

        return new_inherits;
    }

    _removeTableToolbar() {
        document.querySelectorAll('.table-toolbar').forEach(t => t.remove());
    }

    _setupTextNodeEvents(textNode) { }

    // ─────────────────────────────────────────────────────────────────────────
    // Overflow Guard – Page Boundary Indicator
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Inject (or move) the red page-boundary line inside the paper container
     * and show/hide the sticky overflow warning based on whether content
     * exceeds the boundary.
     *
     * The boundary is calculated from the current paper format height minus
     * the top padding (20mm default), converted to pixels via the container's
     * own pixel height / mm ratio so it is always accurate regardless of zoom.
     */

    _updateOverflowGuard() {
        this._applyPaperFormatToCanvas();
    }

    /**
     * Attach a MutationObserver to the report frame so the overflow guard
     * re-evaluates automatically whenever content changes.
     * Called once from _setupReportFrame.
     */
    _startOverflowGuardObserver() {
        if (this._overflowObserver) {
            this._overflowObserver.disconnect();
        }

        const editableArea = this.reportFrameRef.el;
        if (!editableArea) return;

        // Debounce to avoid flooding on heavy DOM mutations
        let debounceTimer = null;
        const check = () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => this._updateOverflowGuard(), 150);
        };

        this._overflowObserver = new MutationObserver(check);
        this._overflowObserver.observe(editableArea, {
            childList: true,
            subtree: true,
            characterData: true,
            attributes: true,
            attributeFilter: ['style', 'class'],
        });

        // Also re-check whenever the window is resized (zoom change, etc.)
        if (this._overflowResizeHandler) {
            window.removeEventListener('resize', this._overflowResizeHandler);
        }
        this._overflowResizeHandler = check;
        window.addEventListener('resize', this._overflowResizeHandler);

        // Initial check after the frame is painted
        requestAnimationFrame(() => this._updateOverflowGuard());
    }
}

// ── Apply focused mixins ─────────────────────────────────────────────────────
// QR wizard and Box section methods live in dedicated files to keep
// studio_report.js under a manageable size.
Object.assign(EditReport.prototype, QrMixin, BoxMixin, SignMixin);

EditReport.template = "custom_report.edit_report";
EditReport.components = { CylloStudioDropdown };
registry.category("actions").add("edit_report", EditReport);
