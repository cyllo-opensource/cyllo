/** @odoo-module **/
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { browser } from "@web/core/browser/browser";
import { Component, onWillStart, useState, useRef, onMounted } from "@odoo/owl";
import { session } from "@web/session";
import { jsonrpc } from "@web/core/network/rpc_service";
import { SignatureDialog } from "@web/core/signature/signature_dialog";
import { DialogContainer } from '@cyllo_sign/js/dialog/dialogService'


export class SignConfigureAction extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialogs = owl.reactive({});
        this.dialogId = 0;
        this.notification = useService("notification");
        this.root = useRef("root");
        this.iframe = useRef("sign_iframe");
        this.FieldEditModal = useRef("FieldEditModal");
        this.state = useState({
            signDatas: [],
            modalValues: [],
            isRequestModel: false,
        })
        this.resId = this.props.action?.params?.['res_id'] || this.props.res_id;
        this.pdf_url = this.getPdfUrl();
        this.pdfjs_url = "/web/static/lib/pdfjs/web/viewer.html?file=" + this.pdf_url;
        if (!this.pdf_url) {
            this.action.doAction("cyllo_sign.action_view_templates", {
                clearBreadcrumbs: true,
            });
        }
        this.fieldColor = {
            '0': 'rgba(255, 255, 255, 0.7)',
            '1': 'rgba(255, 178, 178, 0.7)',
            '2': 'rgba(255, 229, 180, 0.7)',
            '3': 'rgba(255, 250, 205, 0.7)',
            '4': 'rgba(176, 224, 230, 0.7)',
            '5': 'rgba(255, 192, 203, 0.7)',
            '6': 'rgba(173, 216, 230, 0.7)',
            '7': 'rgba(127, 255, 212, 0.7)',
            '8': 'rgba(192, 192, 192, 0.7)',
            '9': 'rgba(255, 105, 180, 0.7)',
            '10': 'rgba(144, 238, 144, 0.7)',
            '11': 'rgba(230, 230, 250, 0.7)',
        };

        onWillStart(async () => {
            if (this.props.action) {
                this.state.isRequestModel = this.props.action.context.active_model === 'sign.request' ||
                    this.props.action.context.active_model === 'sign.generate';
            }
            const isSigningMode = this.state.isRequestModel || this.props.portal;
            const requestId = isSigningMode ?
                (this.props.request_id || this.props.action.params.request_id || this.props.action?.context?.active_id) : false;
            this.state.signDatas = await jsonrpc('/web/dataset/call_kw/sign.template/get_datas', {
                model: 'sign.template',
                method: 'get_datas',
                args: [this.resId],
                kwargs: {
                    request_id: requestId
                },
            });
        })
        onMounted(async () => {
            const isSigningMode = this.state.isRequestModel || this.props.portal;
            if (isSigningMode) {
                this.preventCurrentAction();
                this.addFieldsForSignRequest(this.iframe.el.contentDocument);
            } else {
                this.initializeDragula();
                this.waitForPDFPagesAndAddFields(this.iframe.el.contentDocument);
            }
        });
    }
    preventCurrentAction() {
        const originalSetItem = sessionStorage.setItem;
        sessionStorage.setItem = function (key, value) {
            if (key === 'current_action') {
                return;
            }
            try {
                originalSetItem.apply(this, [key, value]);
            } catch (error) {
                if (error.name === 'QuotaExceededError') {
                    console.warn('Session storage quota exceeded.');
                } else {
                    console.error('Error setting sessionStorage key:', error);
                }
            }
        };
    }
    getPdfUrl() {
        var res_id = this.props.action?.params?.res_id || this.props.res_id
        var model = this.props.action?.params?.res_model || this.props.res_model
        if (model && res_id) {
            return "/web/content/" + model + "/" + res_id + "/data";
        }
    }
    async addFieldsForSignRequest(iframeDoc) {
        const checkSignPagesAndAddFields = async () => {
            const totalPages = await this.orm.call('sign.template', 'get_pdf_page_count', [this.resId]);
            const pageElements = this.iframe.el.contentDocument.querySelectorAll('.page');
            if (pageElements.length === totalPages) {
                const allPagesLoaded = Array.from(pageElements).every(page => {
                    const rect = page.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                });
                if (allPagesLoaded) {
                    await new Promise(resolve => setTimeout(resolve, 500));
                    this.onReloadingIframeContent();
                    const processedFields = new Set();
                    this.state.signDatas.template_items.forEach((fieldItem) => {
                        const pageElement = pageElements[fieldItem.page - 1];
                        if (!pageElement || processedFields.has(fieldItem.id)) return;
                        processedFields.add(fieldItem.id);
                        if (fieldItem.signature) {
                            this.renderSignatureField(iframeDoc, fieldItem, pageElement);
                        } else {
                            this.addFieldToPDFPage(
                                null,
                                this.iframe.el,
                                fieldItem.page,
                                fieldItem.position_x,
                                fieldItem.position_y,
                                pageElement,
                                fieldItem
                            );
                        }
                    });
                    pageElements.forEach(page => {
                        const fields = page.querySelectorAll('.insertedField');
                        fields.forEach(field => {
                            field.style.display = 'none';
                            field.offsetHeight;
                            field.style.display = 'flex';
                            field.style.zIndex = '1000';
                            field.style.pointerEvents = 'auto';
                        });
                    });
                    const iframePage = this.iframe.el.contentDocument.querySelector('#viewer');
                    if (iframePage) {
                        const iframePages = iframePage.querySelectorAll('.page');
                        iframePages.forEach((page) => {
                            const insertedFields = page.querySelectorAll('.insertedField');
                            insertedFields.forEach((field) => {
                                if (field?.children[0]?.tagName === 'IMG') {
                                    field.children[0].style.webkitUserDrag = 'none';
                                    field.children[0].style.userDrag = 'none';
                                }
                            });
                        });
                    }
                    return;
                }
            }
        };
        await checkSignPagesAndAddFields();
        setTimeout(async () => {
            await checkSignPagesAndAddFields();
        }, 1000);
    }
    renderSignatureField(iframeDoc, fieldItem, pageElement) {
        const backgroundColor = this.fieldColor[fieldItem.color] || '#90EE90';
        const fieldElement = iframeDoc.createElement('div');
        fieldElement.className = 'insertedField';
        fieldElement.textContent = fieldItem.placeholder || fieldItem.name;
        fieldElement.style = `
            background: ${backgroundColor};
            position: absolute;
            left: ${fieldItem.position_x}%;
            top: ${fieldItem.position_y}%;
            border: 1px solid black;
            width: ${fieldItem.width}%;
            height: ${fieldItem.height}%;
            cursor: ${fieldItem.signature ? "default" : "pointer"};
            box-sizing: border-box;
            text-align: center;
            display: flex;
            justify-content: center;
            align-items: center;
        `;
        fieldElement.dataset.templateItemId = fieldItem?.id || null;
        const isSigningMode = this.state.isRequestModel || this.props.portal;
        if (isSigningMode) {
            fieldElement.dataset.requestItemId = fieldItem.request_item_id || null;
        }
        const content = fieldItem.signature ? fieldItem.signature.replace(/<\/?p>/g, "") : "";
        if (content) {
            const imgElement = document.createElement('img');
            imgElement.src = `data:image/png;base64,${content}`;
            imgElement.alt = 'Signature';
            imgElement.style.cssText = `
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
            `;
            fieldElement.innerHTML = '';
            fieldElement.appendChild(imgElement);
        }
        pageElement.appendChild(fieldElement);
    }
    async waitForPDFPagesAndAddFields(iframeDoc) {
        const checkPagesAndAddFields = async () => {
            try {
                const totalPages = await this.orm.call('sign.template', 'get_pdf_page_count', [this.resId]);
                const pageElements = this.iframe.el.contentDocument.querySelectorAll('.page');
                if (pageElements.length === totalPages) {
                    const allPagesLoaded = Array.from(pageElements).every(page => {
                        const rect = page.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    });
                    if (allPagesLoaded) {
                        await new Promise(resolve => setTimeout(resolve, 500));
                        this.onReloadingIframeContent();
                        await this.addFieldsToPages(pageElements);
                        return;
                    }
                }
            } catch (error) {
                console.error('Error checking PDF pages:', error);
            }
        };
        await checkPagesAndAddFields();
        setTimeout(async () => {
            await checkPagesAndAddFields();
        }, 1000);
    }
    async addFieldsToPages(pageElements) {
        if (!this.state.signDatas.template_items) {
            console.warn('No template items found');
            return;
        }
        if (!pageElements || pageElements.length === 0) {
            await new Promise(resolve => setTimeout(resolve, 300));
            pageElements = this.iframe.el.contentDocument.querySelectorAll('.page');
        }
        const processedFields = new Set();
        this.state.signDatas.template_items.forEach((fieldItem) => {
            if (processedFields.has(fieldItem.id)) return;
            processedFields.add(fieldItem.id);
            const pageElement = pageElements[fieldItem.page - 1];
            if (pageElement) {
                this.addFieldToPDFPage(
                    null,
                    this.iframe.el,
                    fieldItem.page,
                    fieldItem.position_x,
                    fieldItem.position_y,
                    pageElement,
                    fieldItem
                );
            } else {
                console.warn(`Page element not found for page ${fieldItem.page}`);
            }
        });
        pageElements.forEach(page => {
            const fields = page.querySelectorAll('.insertedField');
            fields.forEach(field => {
                field.style.display = 'none';
                field.offsetHeight;
                field.style.display = 'flex';
                field.style.zIndex = '1000';
                field.style.pointerEvents = 'auto';
                const dragHandle = field.querySelector('.drag-handle');
                const resizeHandle = field.querySelector('.resize-handle');
                if (dragHandle) {
                    dragHandle.style.zIndex = '1001';
                    dragHandle.style.pointerEvents = 'auto';
                }
                if (resizeHandle) {
                    resizeHandle.style.zIndex = '1001';
                    resizeHandle.style.pointerEvents = 'auto';
                }
            });
        });
        const viewerContainer = this.iframe.el.contentDocument.querySelector('#viewerContainer');
        if (viewerContainer) {
            viewerContainer.style.zIndex = '0';
        }
    }
    initializeDragula() {
        const container = this.root.el.querySelector('.cy-sign_editor');
        const iframe = this.iframe.el;

        const initDragSource = () => {
            const draggableItems = container.querySelectorAll('.cy-sign_editor-option');
            draggableItems.forEach(item => {
                item.setAttribute('draggable', 'true');
                item.addEventListener('dragstart', (e) => {
                    e.dataTransfer.setData('text/plain', '');
                    e.dataTransfer.effectAllowed = 'copy';
                    const fieldData = {
                        fieldId: item.dataset.fieldId,
                        fieldName: item.dataset.fieldName,
                        fieldHeight: item.dataset.fieldHeight,
                        fieldWidth: item.dataset.fieldWidth,
                        fieldPlaceholder: item.dataset.fieldPlaceholder,
                        fieldType: item.dataset.fieldType
                    };
                    e.dataTransfer.setData('application/json', JSON.stringify(fieldData));
                });
            });
        };
        const initDropTarget = () => {
            const handleDrop = async (e) => {
                e.preventDefault();
                try {
                    const fieldData = JSON.parse(e.dataTransfer.getData('application/json'));
                    const iframeDoc = iframe.contentDocument;
                    const scrollX = iframeDoc.documentElement.scrollLeft || iframeDoc.body.scrollLeft;
                    const scrollY = iframeDoc.documentElement.scrollTop || iframeDoc.body.scrollTop;
                    const iframeRect = iframe.getBoundingClientRect();
                    const mouseX = e.clientX - iframeRect.left;
                    const mouseY = e.clientY - iframeRect.top;
                    const adjustedX = mouseX + scrollX;
                    const adjustedY = mouseY + scrollY;
                    const pages = iframeDoc.querySelectorAll('.page');
                    let targetPage = null;
                    let pageNumber = null;
                    for (let i = 0; i < pages.length; i++) {
                        const pageRect = pages[i].getBoundingClientRect();
                        const pageTop = pageRect.top + scrollY - iframeRect.top;
                        const pageBottom = pageRect.bottom + scrollY - iframeRect.top;
                        const pageLeft = pageRect.left + scrollX - iframeRect.left;
                        const pageRight = pageRect.right + scrollX - iframeRect.left;
                        if (adjustedX >= pageLeft && adjustedX <= pageRight &&
                            adjustedY >= pageTop && adjustedY <= pageBottom) {
                            targetPage = pages[i];
                            pageNumber = i + 1;
                            break;
                        }
                    }
                    if (!targetPage) {
                        console.warn('Drop position not found within any page');
                        return;
                    }
                    const pageRect = targetPage.getBoundingClientRect();
                    const relativeX = ((adjustedX - (pageRect.left + scrollX - iframeRect.left)) / pageRect.width) * 100;
                    const relativeY = ((adjustedY - (pageRect.top + scrollY - iframeRect.top)) / pageRect.height) * 100;
                    const tempElement = document.createElement('div');
                    Object.assign(tempElement.dataset, fieldData);
                    const fieldDimensions = this.getFieldDimensions(tempElement);
                    const newFieldItem = {
                        color: '10',
                        placeholder: fieldData.fieldPlaceholder,
                        name: fieldData.fieldName,
                        field_type: fieldData.fieldType,
                        width: fieldDimensions.width,
                        height: fieldDimensions.height,
                        page: pageNumber,
                        position_x: relativeX,
                        position_y: relativeY
                    };
                    const createdElement = this.addFieldToPDFPage(
                        tempElement,
                        iframe,
                        pageNumber,
                        relativeX,
                        relativeY,
                        targetPage,
                        newFieldItem
                    );
                    if (createdElement) {
                        const element_id = await this.orm.call('sign.template', 'add_item', [this.resId], {
                            field: parseInt(fieldData.fieldId),
                            required: false,
                            page: pageNumber,
                            position_x: relativeX,
                            position_y: relativeY,
                            placeholder: fieldData.fieldPlaceholder,
                            position_x_px: relativeX * pageRect.width / 100,
                            position_y_px: relativeY * pageRect.height / 100
                        });
                        const newItemData = await this.orm.call('sign.template.item', 'get_datas', [element_id]);
                        this.state.signDatas.template_items = [
                            ...this.state.signDatas.template_items,
                            {
                                ...newItemData,
                                id: element_id,
                                field_id: [parseInt(fieldData.fieldId), fieldData.fieldPlaceholder],
                                role_id: [1, 'Default'],
                                required: false
                            }
                        ];
                        createdElement.dataset.templateItemId = element_id;
                    }
                } catch (error) {
                    console.error('Error handling drop:', error);
                }
            };
            iframe.addEventListener('load', () => {
                const iframeDoc = iframe.contentDocument;
                const dropContainer = iframeDoc.body;
                dropContainer.addEventListener('dragover', (e) => {
                    e.preventDefault();
                    e.dataTransfer.dropEffect = 'copy';
                });
                dropContainer.addEventListener('drop', handleDrop.bind(this));
            });
        };
        initDragSource();
        initDropTarget();
    }
    getFieldDimensions(el) {
        const defaultDimensions = { width: 14, height: 5 };
        if (!el?.dataset?.fieldId) {
            return defaultDimensions;
        }
        if (el.dataset.fieldWidth && el.dataset.fieldHeight) {
            return {
                width: parseFloat(el.dataset.fieldWidth),
                height: parseFloat(el.dataset.fieldHeight)
            };
        }
        if (this.state.signDatas?.template_items?.length > 0) {
            const existingField = this.state.signDatas.template_items.find(
                item => item.field_id[0] === parseInt(el.dataset.fieldId)
            );
            if (existingField?.width && existingField?.height) {
                return {
                    width: existingField.width,
                    height: existingField.height
                };
            }
        }
        const draggableItem = this.root.el.querySelector(
            `.cy-sign_editor-option[data-field-id="${el.dataset.fieldId}"]`
        );
        if (draggableItem) {
            return {
                width: parseFloat(draggableItem.dataset.fieldWidth) || defaultDimensions.width,
                height: parseFloat(draggableItem.dataset.fieldHeight) || defaultDimensions.height
            };
        }
        return defaultDimensions;
    }
    getDropPositionOnPDFPage(iframe, iframeDoc, fieldDimensions) {
        const iframeRect = iframe.getBoundingClientRect();
        const scrollX = iframeDoc.documentElement.scrollLeft || iframeDoc.body.scrollLeft;
        const scrollY = iframeDoc.documentElement.scrollTop || iframeDoc.body.scrollTop;
        const mouseX = window.event.clientX;
        const mouseY = window.event.clientY;
        const x = mouseX - iframeRect.left + scrollX;
        const y = mouseY - iframeRect.top + scrollY;
        const pageElements = this.iframe.el.contentDocument?.querySelectorAll('.page');
        let page = null;
        let relativeX = null;
        let relativeY = null;
        let relativeXpX = null;
        let relativeYpX = null;

        if (pageElements && pageElements.length > 0) {
            for (const [index, pageEl] of pageElements.entries()) {
                const pageRect = pageEl.getBoundingClientRect();
                const pageLeft = pageRect.left + scrollX;
                const pageTop = pageRect.top + scrollY;
                const pageRight = pageRect.right + scrollX;
                const pageBottom = pageRect.bottom + scrollY;

                if (x >= pageLeft && x <= pageRight && y >= pageTop && y <= pageBottom) {
                    page = index + 1;

                    const { width, height } = fieldDimensions;
                    const rawRelativeX = ((x - pageLeft) / pageRect.width) * 100;
                    const rawRelativeY = ((y - pageTop) / pageRect.height) * 100;
                    const maxX = Math.max(0, 100 - width);
                    const maxY = Math.max(0, 100 - height);
                    relativeX = Math.min(maxX, Math.max(0, rawRelativeX));
                    relativeY = Math.min(maxY, Math.max(0, rawRelativeY));
                    relativeXpX = (relativeX * pageRect.width / 100);
                    relativeYpX = (relativeY * pageRect.height / 100);

                    break;
                }
            }
        }
        if (!page) {
            console.warn('Drop position is outside of any PDF page.');
            return null;
        }
        return {
            page,
            x: relativeX,
            y: relativeY,
            relativeXpX,
            relativeYpX
        };
    }
    addFieldToPDFPage(el, iframe, page, x, y, pageElement, fieldItemId) {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document
        if (!pageElement) {
            console.error("Page not found.");
            return;
        }
        const backgroundColor = this.fieldColor[fieldItemId.color] || '#90EE90';
        const fieldWidth = fieldItemId.width ||
            (el?.dataset?.fieldId ? this.getFieldDimensions(el).width : 14);
        const fieldHeight = fieldItemId.height ||
            (el?.dataset?.fieldId ? this.getFieldDimensions(el).height : 5);
        const maxX = 100 - fieldWidth;
        const maxY = 100 - fieldHeight;
        const boundedX = Math.max(0, Math.min(maxX, x));
        const boundedY = Math.max(0, Math.min(maxY, y));

        const fieldElement = iframeDoc.createElement('div');
        fieldElement.className = 'insertedField';
        let displayText;
        const isSigningMode = this.state.isRequestModel || this.props.portal;
        displayText = fieldItemId.placeholder || el?.dataset.fieldPlaceholder || fieldItemId.name || 'Sign';
        fieldElement.textContent = displayText;
        fieldElement.style.position = 'absolute';
        fieldElement.style.left = `${boundedX}%`;
        fieldElement.style.top = `${boundedY}%`;
        fieldElement.style.width = fieldItemId.width ? `${fieldItemId.width}%` : '14%';
        fieldElement.style.height = fieldItemId.height ? `${fieldItemId.height}%` : '5%';
        fieldElement.style.background = backgroundColor;
        if (fieldItemId.required) {
            fieldElement.style.border = '2px solid red';
        } else {
            fieldElement.style.border = '1px solid black';
        }
        fieldElement.style.cursor = 'pointer';
        fieldElement.style.boxSizing = 'border-box';
        fieldElement.style.textAlign = 'center';
        fieldElement.style.display = 'flex';
        fieldElement.style.alignItems = 'center';
        fieldElement.dataset.templateItemId = fieldItemId?.id || null;
        fieldElement.dataset.requestItemId = fieldItemId?.request_item_id || null;
        fieldElement.style.justifyContent = 'space-around';
        fieldElement.style.overflow = 'hidden';
        fieldElement.addEventListener('click', async (event) => {
            let user = await jsonrpc('/web/dataset/call_kw/sign.request/get_user', {
                model: 'sign.request', method: 'get_user',
                args: [session.partner_id || parseInt(this.props.partner_id)],
                kwargs: {},
            });
            const userData = user[0] || {};
            const userName = session.name || userData.name || "";
            const userEmail = userData.email;
            const userPhone = userData.phone;
            const roles = this.props.action?.params?.roles?.map(role => role.role_id[0]) || this.props.roles
            if (!isSigningMode) {
                const isDragHandle = event.target.closest('.drag-handle');
                const isResizeHandle = event.target.closest('.resize-handle');
                if (!isDragHandle && !isResizeHandle) {
                    this.showModal(fieldElement);
                }
            } else {
                if (roles.includes(fieldItemId.role_id)) {
                    const nameAndSignatureProps = {
                        displaySignatureRatio: 3,
                        signatureType: "signature",
                        noInputName: true,
                    };
                    let defaultName = userName
                    const dialogProps = {
                        defaultName,
                        nameAndSignatureProps,
                        uploadSignature: (data) => this.uploadSignature(data, fieldElement),
                    };
                    if (fieldItemId.field_type == 'signature') {
                        this.onAddDialog({
                            dialog: SignatureDialog,
                            props: dialogProps
                        })
                    } else if (fieldItemId.field_type === 'text') {
                        const fieldName = fieldItemId.placeholder.toLowerCase();
                        if (fieldName === 'name') {
                            fieldElement.textContent = userName;
                            fieldItemId.placeholder = userName;
                            this.saveFieldValue(fieldElement, userName);
                        } else if (fieldName === 'email') {
                            if (userEmail) {
                                fieldElement.textContent = userEmail;
                                fieldItemId.placeholder = userEmail;
                                this.saveFieldValue(fieldElement, userEmail);
                            } else {
                                this.makeEditableField(fieldElement, fieldItemId, iframeDoc)
                            }
                        } else if (fieldName === 'phone') {
                            if (userPhone) {
                                fieldElement.textContent = userPhone;
                                fieldItemId.placeholder = userPhone;
                                this.saveFieldValue(fieldElement, userPhone);
                            } else {
                                this.makeEditableField(fieldElement, fieldItemId, iframeDoc)
                            }
                        } else {
                            this.makeEditableField(fieldElement, fieldItemId, iframeDoc)
                        }
                    } else if (fieldItemId.field_type === 'date') {
                        this.makeEditableField(fieldElement, fieldItemId, iframeDoc)
                    }
                } else {
                    console.error('You are not authorized to access this field')
                }
            }
        });

        const dragHandle = iframeDoc.createElement('div');
        dragHandle.className = 'drag-handle';
        dragHandle.style.position = 'absolute';
        dragHandle.style.top = '0';
        dragHandle.style.left = '0';
        dragHandle.style.width = '25px';
        dragHandle.style.height = '100%';
        dragHandle.style.cursor = 'move';
        dragHandle.style.backgroundColor = '#2e2e2e';
        dragHandle.style.display = 'flex';
        dragHandle.style.justifyContent = 'center';
        dragHandle.style.alignItems = 'center';
        dragHandle.style.color = 'white';
        dragHandle.style.borderRight = '1px solid black';
        const svgInline = `
            <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24" style="pointer-events: none;">
                <path d="M8 7a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm5 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm5 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM8 12a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm5 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm5 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM8 17a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm5 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0Zm5 0a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"/>
            </svg>
        `;
        dragHandle.innerHTML = svgInline;
        if (!this.state.isRequestModel && !this.props.portal) {
            fieldElement.appendChild(dragHandle);
        }

        const resizeHandle = iframeDoc.createElement('div');
        resizeHandle.className = 'resize-handle';
        resizeHandle.style.cssText = `
            position: absolute;
            bottom: 0;
            right: 0;
            width: 12px;
            height: 12px;
            background: transparent;
            border-right: 2px solid black;
            border-bottom: 2px solid black;
            cursor: nwse-resize;
            transition: border-color 0.3s;
        `;
        if (!this.state.isRequestModel && !this.props.portal) {
            fieldElement.appendChild(resizeHandle);
        }
        pageElement.appendChild(fieldElement);
        this.makeResizable(iframeDoc, fieldElement, resizeHandle);
        this.makeDraggable(iframeDoc, fieldElement, dragHandle);
        return fieldElement;
    }
    makeEditableField(fieldElement, fieldItemId, iframeDoc) {
        const originalText = fieldElement.textContent;
        if (fieldElement.querySelector('input')) return;
        let input;
        if (fieldItemId.field_type === 'date') {
            input = iframeDoc.createElement('input');
            input.type = 'date';
            if (fieldItemId.value) {
                const [day, month, year] = fieldItemId.value.split('-');
                input.value = `${year}-${month}-${day}`;
            }
        } else {
            input = iframeDoc.createElement('input');
            input.type = 'text';
        }
        input.value = fieldItemId.value || '';
        input.style.width = '100%';
        input.style.height = '100%';
        input.style.border = 'none';
        input.style.textAlign = 'center';
        input.style.background = 'transparent';
        input.style.outline = 'none';
        input.style.boxSizing = 'border-box';
        fieldElement.textContent = '';
        fieldElement.appendChild(input);
        input.focus();
        const saveFieldValue = async (value) => {
            try {
                let itemToUpdate;
                const updateData = { value };

                if (fieldItemId.field_type === 'date') {
                    const [year, month, day] = value.split('-');
                    if (!/^\d{4}$/.test(year)) {
                        alert('invalid year format!!!!')
                        return;
                    }
                    const formattedDate = `${day}-${month}-${year}`;
                    updateData.value = formattedDate;
                    updateData.placeholder = formattedDate;
                } else {
                    updateData.placeholder = value;
                }
                const isSigningMode = this.state.isRequestModel || this.props.portal;
                if (isSigningMode) {
                    itemToUpdate = parseInt(fieldElement.dataset.requestItemId);
                    await this.orm.write("sign.request.item", [itemToUpdate], updateData);
                } else {
                    itemToUpdate = parseInt(fieldElement.dataset.templateItemId);
                    await this.orm.write("sign.template.item", [itemToUpdate], updateData);
                }
                const templateItems = this.state.signDatas.template_items || [];
                this.state.signDatas.template_items = templateItems.map(item =>
                    (isSigningMode && item.request_item_id === itemToUpdate) ||
                        (!isSigningMode && item.id === itemToUpdate)
                        ? { ...item, value: updateData.value, placeholder: updateData.placeholder }
                        : item
                );
                return true;
            } catch (error) {
                console.error('Error saving field value:', error);
                this.notification.add({
                    message: 'Failed to save field value',
                    type: 'danger',
                });
                return false;
            }
        };
        input.addEventListener('blur', async () => {
            const newValue = input.value.trim();
            if (newValue) {
                const saveSuccess = await saveFieldValue(newValue);
                if (saveSuccess) {
                    if (fieldItemId.field_type === 'date') {
                        const [year, month, day] = newValue.split('-');
                        fieldElement.textContent = `${day}-${month}-${year}`;
                        fieldItemId.value = `${day}-${month}-${year}`;
                    } else {
                        fieldElement.textContent = newValue;
                        fieldItemId.value = newValue;
                    }
                    fieldItemId.placeholder = fieldItemId.value;
                } else {
                    fieldElement.textContent = originalText;
                }
            } else {
                fieldElement.textContent = originalText;
            }
            if (fieldElement.contains(input)) {
                fieldElement.removeChild(input);
            }
        });
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                input.blur();
            }
        });
    }
    async saveFieldValue(fieldElement, value) {
        try {
            let itemToUpdate;
            const updateData = {
                value: value,
                placeholder: value
            };
            const isSigningMode = this.state.isRequestModel || this.props.portal;
            if (isSigningMode) {
                itemToUpdate = parseInt(fieldElement.dataset.requestItemId);
                await this.orm.write("sign.request.item", [itemToUpdate], updateData);
            } else {
                itemToUpdate = parseInt(fieldElement.dataset.templateItemId);
                await this.orm.write("sign.template.item", [itemToUpdate], updateData);
            }
            const templateItems = this.state.signDatas.template_items || [];
            const updatedItems = templateItems.map(item => {
                if ((isSigningMode && item.request_item_id === itemToUpdate) ||
                    (!isSigningMode && item.id === itemToUpdate)) {
                    return {
                        ...item,
                        value: value,
                        placeholder: value
                    };
                }
                return item;
            });

            this.state.signDatas = {
                ...this.state.signDatas,
                template_items: updatedItems,
            };
        } catch (error) {
            console.error('Error saving field value:', error);
            this.notification.add({
                message: 'Failed to save field value',
                type: 'danger',
            });
        }
    }

    onReloadingIframeContent() {
        let printButton = this.iframe.el.contentDocument.querySelector('button[id="print"]');
        let presentationMode = this.iframe.el.contentDocument.querySelector('button[id="presentationMode"]');
        let openFile = this.iframe.el.contentDocument.querySelector('button[id="openFile"]');
        let download = this.iframe.el.contentDocument.querySelector('button[id="download"]');
        if (printButton && presentationMode && openFile && download) {
            printButton.style.display = 'none';
            presentationMode.style.display = 'none';
            openFile.style.display = 'none';
            download.style.display = 'none';
        }
        let baseWidth = window.innerWidth;
        window.addEventListener('resize', () => {
            const currentWidth = window.innerWidth;
            if (Math.abs(currentWidth - baseWidth) > 10) {
                baseWidth = currentWidth;
                this.action.doAction('soft_reload')
                if (this.props.portal) {
                    this.addFieldsForSignRequest(this.iframe.el.contentDocument);
                }
            }
        });
        this.iframe.el.contentDocument.addEventListener("click", (ev) => {
            const zoomIds = ['zoomOut', 'zoomIn', 'scaleSelect'];
            if (zoomIds.includes(ev.target.id)) {
                this.action.doAction('soft_reload')
                if (this.props.portal) {
                    this.addFieldsForSignRequest(this.iframe.el.contentDocument);
                }
            }
        })
    }

    onAddDialog(ev) {
        const id = this.dialogId++
        this.lastId = id;
        const close = () => {
            if (this.dialogs[id]) {
                delete this.dialogs[id];
                if (ev.onClose) {
                    ev.onClose();
                }
            }
        }
        const dialog = {
            class: ev.dialog,
            props: Object.assign({}, ev.props, {
                close,
                id
            }),
            dialogData: {
                close,
            }
        };
        this.dialogs[id] = dialog;
    }

    goBack() {
        if (!this.state.isRequestModel) {
            this.action.doAction("cyllo_sign.action_view_templates", {
                clearBreadcrumbs: true,
            });
        } else {
            this.action.doAction({
                type: 'ir.actions.act_window',
                name: 'Sign Request',
                target: 'current',
                res_id: this.props.action.params.request_id,
                res_model: 'sign.request',
                views: [[false, 'form']],
            },
                { clearBreadcrumbs: true });
        }

    }

    async sendPdf() {
        try {
            const recordId = this.resId;
            const result = await this.orm.call("sign.template", "action_view_sign_generate", [recordId]);
            if (result.type === "ir.actions.act_window") {
                this.action.doAction(result);
            }
        } catch (error) {
            this.notification.add("You need to use dropped fields for sending documents!", {
                type: "warning",
            });
        }
    }
    get requesterIds() {
        return this.props.action?.params?.requester_ids || parseInt(this.props.requester_ids) || parseInt(this.props.requester_ids[1])
    }
    async savePdf() {
        const hasRequiredField = this.state.signDatas?.template_items?.find(
            (item) => item.required
        );
        if (hasRequiredField) {
            if (hasRequiredField.value == false) {
                alert("** You need to fill the required fields!.");
                return;
            }
        }
        try {
            const result = await jsonrpc('/web/dataset/call_kw/sign.requester/action_sign', {
                model: 'sign.requester', method: 'action_sign',
                args: [this.requesterIds],
                kwargs: { items: this.state.signDatas.template_items }
            }).then((data) => {
                if (!this.props.portal) {
                    this.action.doAction({
                        type: 'ir.actions.act_window',
                        name: 'Sign Request',
                        target: 'current',
                        res_id: parseInt(this.props.action?.params.request_id),
                        res_model: 'sign.request',
                        views: [[false, 'form']],
                    }, { clearBreadcrumbs: true });
                } else {
                    window.location.href = `/sign_request/details/${this.props.request_id}`;
                }
            })
        } catch (error) {
            console.error("Error downloading PDF:", error);
            this.notification.add("Failed to download PDF: " + error.message, {
                type: "danger"
            });
        }
    }
    async uploadSignature({ signatureImage }, fieldElement) {
        const file = signatureImage[1];
        const imgElement = document.createElement('img');
        imgElement.src = `data:image/png;base64,${file}`;
        imgElement.alt = 'Signature';
        imgElement.style.maxWidth = '100%';
        imgElement.style.maxHeight = '100%';
        imgElement.style.objectFit = 'contain';
        fieldElement.innerHTML = '';
        fieldElement.style.cursor = 'default';
        fieldElement.appendChild(imgElement);
        let itemToUpdate;
        const isSigningMode = this.state.isRequestModel || this.props.portal;
        if (isSigningMode) {
            itemToUpdate = parseInt(fieldElement.dataset.requestItemId);
            await this.orm.write("sign.request.item", [itemToUpdate], {
                signature: file,
                value: true,
            });
        } else {
            itemToUpdate = parseInt(fieldElement.dataset.templateItemId);
            await this.orm.write("sign.template.item", [itemToUpdate], {
                signature: file,
            });
        }
        const templateItems = this.state.signDatas.template_items || [];
        const updatedItems = templateItems.map(item => {
            if (isSigningMode && item.request_item_id === itemToUpdate) {
                return {
                    ...item,
                    signature: file,
                    value: true
                };
            } else if (!isSigningMode && item.id === itemToUpdate) {
                return {
                    ...item,
                    signature: file,
                };
            }
            return item;
        });
        this.state.signDatas = {
            ...this.state.signDatas,
            template_items: updatedItems,
        };
    }
    showModal(element) {
        const templateItemId = parseInt(element.dataset.templateItemId);
        const fieldItem = this.state.signDatas.template_items.find(
            item => item.id === templateItemId
        );
        if (fieldItem) {
            this.state.modalValues = {
                template_item_id: fieldItem.id,
                field_id: fieldItem.field_id[0],
                role_id: fieldItem.role_id[0],
                placeholder: fieldItem.placeholder || fieldItem.field_id[1],
                required: fieldItem.required,
            };
        } else {
            console.warn('Field item not found in state');
        }

        $(this.FieldEditModal.el).modal('show');
    }
    async ModalSaveField() {
        const updatedValues = {
            field_id: parseInt(this.state.modalValues.field_id),
            role_id: parseInt(this.state.modalValues.role_id),
            placeholder: this.state.modalValues.placeholder,
            required: this.state.modalValues.required,
        };
        try {
            await this.orm.call('sign.template.item', 'write',
                [[this.state.modalValues.template_item_id], updatedValues]
            );
            this.state.signDatas.template_items = this.state.signDatas.template_items.map(item => {
                if (item.id === this.state.modalValues.template_item_id) {
                    return {
                        ...item,
                        field_id: [updatedValues.field_id, item.field_id[1]],
                        role_id: [updatedValues.role_id, item.role_id[1]],
                        placeholder: updatedValues.placeholder,
                        required: updatedValues.required,
                    };
                }
                return item;
            });
            this.state.modalValues = {
                ...this.state.modalValues,
                ...updatedValues
            };
            const iframeDoc = this.iframe.el.contentDocument;
            const fieldElement = iframeDoc.querySelector(`[data-template-item-id="${this.state.modalValues.template_item_id}"]`);
            if (fieldElement) {
                const displayText = updatedValues.placeholder || fieldElement.textContent;
                $(fieldElement)[0].childNodes[0].textContent = displayText;
                const roleData = await this.orm.call('sign.role', 'read',
                    [[updatedValues.role_id]],
                    { fields: ['color'] }
                );
                const roleColor = roleData[0]?.color?.toString() || '1';
                fieldElement.style.background = this.fieldColor[roleColor];
                if (updatedValues.required) {
                    fieldElement.style.border = '2px solid red';
                } else {
                    fieldElement.style.border = '1px solid black';
                }
            }
            $(this.FieldEditModal.el).modal('hide');
            this.notification.add("Field updated successfully", {
                type: "success",
            });
        } catch (error) {
            console.error("Failed to update field:", error);
            this.notification.add("Failed to update field", {
                type: "danger",
            });
        }
    }
    updateModalValue(fieldName, fieldValue) {
        this.state.modalValues[fieldName] = fieldValue;
    }
    async DeleteItem(e) {
        try {
            const templateItemId = this.state.modalValues.template_item_id;
            if (!templateItemId) {
                console.error("No template item ID to delete.");
                return;
            }
            const res = await this.orm.call('sign.template.item', 'unlink', [[templateItemId]]);
            if (Array.isArray(this.state.signDatas.template_items)) {
                this.state.signDatas.template_items = this.state.signDatas.template_items.filter(item => item.id !== templateItemId);
            }
            const iframeDoc = this.iframe.el.contentDocument || this.iframe.el.contentWindow.document;
            const elementToRemove = iframeDoc.querySelector(`[data-template-item-id="${templateItemId}"]`);
            if (elementToRemove) {
                elementToRemove.parentNode.removeChild(elementToRemove);
            }
            $(this.FieldEditModal.el).modal('hide');
            this.notification.add("Field deleted successfully", {
                type: "success",
            });
        } catch (error) {
            console.error("Failed to delete the item:", error);
            this.notification.add("An error occurred while deleting the field.", {
                type: "danger",
            });
        }
    }
    makeDraggable(iframeDoc, element, dragHandle) {
        let isDragging = false;
        let offsetX, offsetY;
        var initialPosition = {
            left: element.style.left,
            top: element.style.top,
        };
        element.addEventListener('mousedown', (e) => {
            if (e.target !== dragHandle) return;
            isDragging = true;
            offsetX = e.clientX - element.getBoundingClientRect().left;
            offsetY = e.clientY - element.getBoundingClientRect().top;
            iframeDoc.addEventListener('mousemove', onDrag);
            iframeDoc.addEventListener('mouseup', stopDrag);
            e.stopPropagation();
            e.preventDefault();
        });
        const onDrag = (e) => {
            if (!isDragging) return;
            const pageElement = element.closest('.page');
            const pageRect = pageElement.getBoundingClientRect();
            let newX = e.clientX - offsetX - pageRect.left;
            let newY = e.clientY - offsetY - pageRect.top;
            const percentX = (newX / pageRect.width) * 100;
            const percentY = (newY / pageRect.height) * 100;
            const elementWidth = (parseInt(getComputedStyle(element).width, 10) / pageRect.width) * 100;
            const elementHeight = (parseInt(getComputedStyle(element).height, 10) / pageRect.height) * 100;
            const maxX = 100 - elementWidth;
            const maxY = 100 - elementHeight;
            const boundedX = Math.max(0, Math.min(maxX, percentX));
            const boundedY = Math.max(0, Math.min(maxY, percentY));
            element.style.left = `${boundedX}%`;
            element.style.top = `${boundedY}%`;
        };
        const stopDrag = () => {
            if (!isDragging) return;
            isDragging = false;
            iframeDoc.removeEventListener('mousemove', onDrag);
            iframeDoc.removeEventListener('mouseup', stopDrag);
            const pageElement = element.closest('.page');
            const templateItemId = parseInt(element.dataset.templateItemId);
            const currentX = parseFloat(element.style.left);
            const currentY = parseFloat(element.style.top);
            this.orm.call('sign.template.item', 'write',
                [[templateItemId], {
                    position_x: currentX,
                    position_y: currentY,
                }]
            );
        };
    }

    makeResizable(iframeDoc, element, resizeHandle) {
        let isResizing = false;
        let startX, startY, startWidth, startHeight;
        element.addEventListener('mousedown', (e) => {
            if (e.target !== resizeHandle) return;
            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;
            const pageElement = element.closest('.page');
            const pageRect = pageElement.getBoundingClientRect();
            startWidth = element.getBoundingClientRect().width;
            startHeight = element.getBoundingClientRect().height;
            iframeDoc.addEventListener('mousemove', resize);
            iframeDoc.addEventListener('mouseup', stopResize);
            e.preventDefault();
        });

        const resize = (e) => {
            if (!isResizing) return;
            const pageElement = element.closest('.page');
            const pageRect = pageElement.getBoundingClientRect();
            let newWidth = startWidth + (e.clientX - startX);
            let newHeight = startHeight + (e.clientY - startY);
            let widthPercent = (newWidth / pageRect.width) * 100;
            let heightPercent = (newHeight / pageRect.height) * 100;
            const minWidthPercent = (80 / pageRect.width) * 100;
            const minHeightPercent = (20 / pageRect.height) * 100;
            widthPercent = Math.max(widthPercent, minWidthPercent);
            heightPercent = Math.max(heightPercent, minHeightPercent);
            const currentLeft = parseFloat(element.style.left);
            const currentTop = parseFloat(element.style.top);
            if (currentLeft + widthPercent > 100) {
                widthPercent = 100 - currentLeft;
            }
            if (currentTop + heightPercent > 100) {
                heightPercent = 100 - currentTop;
            }
            element.style.width = `${widthPercent}%`;
            element.style.height = `${heightPercent}%`;
        };

        const stopResize = () => {
            if (!isResizing) return;
            isResizing = false;
            iframeDoc.removeEventListener('mousemove', resize);
            iframeDoc.removeEventListener('mouseup', stopResize);
            const templateItemId = parseInt(element.dataset.templateItemId);
            const finalWidth = parseFloat(element.style.width);
            const finalHeight = parseFloat(element.style.height);
            this.orm.call('sign.template.item', 'write',
                [[templateItemId], {
                    width: finalWidth,
                    height: finalHeight,
                }]
            );
        };
    }
}
SignConfigureAction.template = "cyllo_sign.SignConfigureAction";
SignConfigureAction.components = {
    DialogContainer
}
registry.category("actions").add("sign_configure", SignConfigureAction);
