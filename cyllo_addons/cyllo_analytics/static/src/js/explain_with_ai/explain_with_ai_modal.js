/** @odoo-module **/
import {Component, markup, onMounted, onWillStart, useRef, useState} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import {GraphTile} from "@cyllo_analytics/js/presentation/components/graph_tile";
import {ThemeMaker} from "../theme_maker";
import {SelectUser} from "./components/select_user";
import {useService} from "@web/core/utils/hooks";
import {chatHistory} from "./chatHistory";
import {ChatThread, scrollToView, setStringByLetter} from "./components/chatThread"
import { _t } from "@web/core/l10n/translation";

/**
 * Converts a data URL to a Blob.
 *
 * @param {string} data - The data URL to be converted.
 * @param {string} type - The MIME type of the data.
 * @returns {Blob} A Blob representing the converted data.
 */
function dataUrlToBlob(data, type) {
    const binData = window.atob(data);
    const uiArr = new Uint8Array(binData.length);
    uiArr.forEach((_, index) => (uiArr[index] = binData.charCodeAt(index)));
    return new Blob([uiArr], {type});
}

function htmlToText(html) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return doc.body.textContent || "";
}

function getPdfBlocks(html) {
    const doc = new DOMParser().parseFromString(html || "", "text/html");
    const blocks = [];
    const textOf = (node) => {
        if (node.nodeType === Node.TEXT_NODE) return node.nodeValue;
        if (node.nodeType !== Node.ELEMENT_NODE) return "";
        if (node.tagName === "A" && node.href) return `${node.textContent} (${node.href})`;
        return [...node.childNodes].map(textOf).join("");
    };
    const add = (node, type = "paragraph") => {
        const text = textOf(node).replace(/\s+/g, " ").trim();
        if (text) blocks.push({text, type});
    };
    const visit = (node) => {
        if (node.nodeType !== Node.ELEMENT_NODE) return;
        const tag = node.tagName.toLowerCase();
        if (/^h[1-6]$/.test(tag)) {
            add(node, `heading${tag[1]}`);
        } else if (tag === "p") {
            add(node);
        } else if (tag === "ul" || tag === "ol") {
            [...node.children].filter((child) => child.tagName.toLowerCase() === "li").forEach((item, index) => {
                const prefix = tag === "ol" ? `${index + 1}. ` : "• ";
                blocks.push({text: `${prefix}${textOf(item).replace(/\s+/g, " ").trim()}`, type: "list"});
            });
        } else if (tag === "pre") {
            add(node, "code");
        } else if (tag === "blockquote") {
            add(node, "quote");
        } else if (tag === "hr") {
            blocks.push({type: "separator"});
        } else if (tag === "table") {
            [...node.querySelectorAll("tr")].forEach((row) => {
                blocks.push({text: [...row.children].map((cell) => textOf(cell).trim()).join(" | "), type: "table"});
            });
        } else {
            [...node.children].forEach(visit);
        }
    };
    [...doc.body.children].forEach(visit);
    return blocks;
}

function addPdfText(pdf, blocks, margin, startY) {
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const bottom = pageHeight - margin - 8;
    let y = startY;
    const nextPageIfNeeded = (height) => {
        if (y + height > bottom) {
            pdf.addPage();
            y = margin;
        }
    };

    for (const block of blocks) {
        if (block.type === "separator") {
            nextPageIfNeeded(8);
            pdf.setDrawColor(220);
            pdf.line(margin, y + 2, pageWidth - margin, y + 2);
            y += 8;
            continue;
        }

        const heading = block.type.startsWith("heading");
        const headingLevel = heading ? Number(block.type.slice(-1)) : 0;
        const fontSize = heading ? Math.max(12, 20 - headingLevel * 1.5) : 10.5;
        const fontStyle = heading || block.type === "table" ? "bold" : "normal";
        const indent = block.type === "list" ? 5 : block.type === "quote" ? 4 : 0;
        const lineHeight = fontSize * 1.25 / 2.8346;
        const gapBefore = heading ? 3 : 1;
        const gapAfter = heading ? 2 : 3;
        pdf.setFont("helvetica", fontStyle);
        pdf.setFontSize(fontSize);
        const lines = pdf.splitTextToSize(block.text, pageWidth - margin * 2 - indent);
        y += gapBefore;
        for (const line of lines) {
            nextPageIfNeeded(lineHeight);
            pdf.text(line, margin + indent, y);
            y += lineHeight;
        }
        y += gapAfter;
    }
    return y;
}

/**
 * @class
 * @extends {Component}
 */
export class ExplainAIModal extends Component {
    setup() {
        this.dialogService = useService("dialog")
        this.actionService = useService("action")
        this.orm = useService("orm")
        this.rootRef = useRef("root")
        this.messageRef = useRef("message")
        this.threadService = useService("mail.thread");
        this.attachmentUploadService = useService("mail.attachment_upload");
        this.state = useState({
            imgSrc: "",
            name: "",
            explainByLetter: "",
            explanation: false,
            error: true,
            data: false,
            apiError: false,
            settingsAction: false,
            cut: 100,
            chatMode: false,
            chat: "",
            isResponding: false,
            downloading: false,
        })
        this.chatHistory = useState(new chatHistory())
        var theme_maker = new ThemeMaker(this.props.theme)
        theme_maker.getTheme()
        onWillStart(async () => {
            const {query} = this.props.options
            this.state.data = await this.orm.call("dashboard.config", "sql_execute", [query])
        })
        onMounted(async () => {
            this.state.explanation = await this.explainWithAi()
        })
    }
    goToSettings() {
        this.actionService.doAction(this.state.settingsAction)
        this.dismiss()
    }
    get chartProps() {
        const {options} = this.props
        return {
            data: this.state.data,
            name: options.name || '',
            measures: eval(options.measure),
            dimension: options.dimension,
            dimension_axis: options.dimension_axis,
            type: options.type,
            color_mappings: options.color_mappings || [],
            annotations: options.annotations || [],
        }
    }

    async _sendMessage(userId) {
        const thread = await this.threadService.getChat({userId})
        const postData = {...this.postData}
        const attachment = await this.uploadData(thread)
        if (attachment.id) {
            postData.attachments = [{...attachment}]
        }
        const text = htmlToText(this.explain);
        await this.threadService.post(thread, text, postData)
    }

    dismiss() {
        this.props.close();
    }

    getImageFile() {
        const name = this.state.name;
        const data = this.state.imgSrc.split(",")[1];
        const type = 'image/png'
        return new File([dataUrlToBlob(data, type)], name, {type});
    }

    async uploadData(thread) {
        return await this.attachmentUploadService.uploadFile({thread}, this.getImageFile())
    }

    async handleSendToUser(event) {
        const {currentValue} = event
        currentValue.map(async (user) => await this._sendMessage(user[0]))
    }

    get postData() {
        return {
            attachments: [],
            isNote: false,
            mentionedChannels: [],
            mentionedPartners: [],
            cannedResponseIds: [],
            parentId: null,
        }
    }

    setImage(imgSrc, name) {
        this.state.imgSrc = imgSrc;
        this.state.name = name;
    }

    get explain() {
        return this.state.explanation ? this.state.explanation : ""
    }

    shareToUser() {
        if (this.state.error) return;
        this.dialogService.add(SelectUser, {
            handleSendToUser: this.handleSendToUser.bind(this)
        })
    }

    parseExplain(explanation) {
        let parsedHTML = ""
        try{
            const md = window.markdownit();
            parsedHTML = md.render(explanation);
        }
        catch (e){
            console.error(e)
            parsedHTML = "<div>Oops!! No Internet Connection</div>"
        }
        return markup(parsedHTML);
    }

    async explainWithAi(retry = false) {
        const { color_mappings, annotations } = this.props.options;
        let promptData = [...this.state.data];
        
        let extraContext = {};
        if (color_mappings && color_mappings.length) {
            extraContext.color_mappings = color_mappings;
        }
        if (annotations && annotations.length) {
            extraContext.annotations = annotations;
        }
        if (Object.keys(extraContext).length > 0) {
            promptData.push({ chart_metadata: extraContext });
        }

        const requestId = this.chatHistory.addInitialMessage(promptData, 0)
        const chatId = this.chatHistory.addMessage({role: "assistant", content: ""}, 0)
        const {is_error, api_error, settings_action, cut, explanation, request_token, response_token} = await this.orm.call("dashboard.sheet", "explain_with_ai", [promptData, retry])
        this.chatHistory.updateToken(request_token, requestId)
        this.chatHistory.updateMessageNToken(explanation, response_token, chatId)
        this.state.error = is_error
        this.state.cut = Math.ceil(cut * 100)
        this.state.apiError = api_error
        this.state.settingsAction = settings_action || false
        this.state.explanation = ""
        this.state.explainByLetter = ""
        setStringByLetter(this.state, 'explainByLetter', explanation, '.explain-footer')
        return this.parseExplain(explanation)
    }
    openChatMode() {
        this.state.chatMode = true
    }

    async retry() {
        if (this.state.error) return;
        this.state.explanation = ""
        this.state.explainByLetter = ""
        this.state.explanation = await this.explainWithAi(true)
    }

    showActionMessage(message) {
        var messageContainer = this.messageRef.el.querySelector("#messageContainer");
        messageContainer.innerText = message;
        messageContainer.classList.add("show");
        setTimeout(function () {
            messageContainer.classList.remove("show");
        }, 1000);
    }

    async copyToClip() {
        if (this.state.error) return;
        const message = _t("Copied to Clipboard!")
        this.showActionMessage(message)
        var textArea = document.createElement("textarea");
        textArea.value = htmlToText(this.explain);
        document.body.appendChild(textArea);
        textArea.select();
        var successful = document.execCommand('copy');
        document.body.removeChild(textArea)
        return successful;
    }

    async download() {
        if (this.state.error || this.state.downloading) return;
        this.state.downloading = true;
        try {
            // Let Owl paint the blocking overlay before synchronous PDF layout starts.
            await new Promise((resolve) => requestAnimationFrame(resolve));

            const pdf = new jsPDF('p', 'mm', 'a4');
            const pageWidth = pdf.internal.pageSize.getWidth();
            const pageHeight = pdf.internal.pageSize.getHeight();
            const margin = 15;

            // Draw the report heading as vector shapes and selectable PDF text.
            const themeColor = this.props.theme.theme_color_ids?.[0] || '#6a0dad';
            pdf.setFillColor(themeColor);
            pdf.rect(0, 0, pageWidth, 30, 'F');
            pdf.setTextColor('#ffffff');
            pdf.setFont('helvetica', 'bold');
            pdf.setFontSize(17);
            pdf.text('AI Insights', margin, 13);
            pdf.setFont('helvetica', 'normal');
            pdf.setFontSize(10);
            pdf.text(this.state.name || 'AI Insight', margin, 22);
            pdf.setTextColor('#222222');

            let y = 38;
            if (this.state.imgSrc) {
                const chart = new Image();
                chart.src = this.state.imgSrc;
                await chart.decode();
                const maxChartWidth = pageWidth - margin * 2;
                const maxChartHeight = 105;
                const chartScale = Math.min(
                    1,
                    maxChartHeight / (maxChartWidth * chart.naturalHeight / chart.naturalWidth)
                );
                const chartWidth = maxChartWidth * chartScale;
                const chartHeight = maxChartWidth * chart.naturalHeight / chart.naturalWidth * chartScale;
                if (y + chartHeight > pageHeight - margin - 8) {
                    pdf.addPage();
                    y = margin;
                }
                pdf.addImage(this.state.imgSrc, 'PNG', (pageWidth - chartWidth) / 2, y, chartWidth, chartHeight);
                y += chartHeight + 8;
            }

            const explanationHtml = this.rootRef.el.querySelector('.explain-text-container .text')?.innerHTML || '';
            const blocks = getPdfBlocks(explanationHtml);
            addPdfText(pdf, blocks, margin, y);

            const pageCount = pdf.internal.getNumberOfPages();
            for (let page = 1; page <= pageCount; page++) {
                pdf.setPage(page);
                pdf.setFont('helvetica', 'normal');
                pdf.setFontSize(8);
                pdf.setTextColor(130);
                pdf.text(`Page ${page} of ${pageCount}`, pageWidth - margin, pageHeight - 7, {align: 'right'});
            }

            pdf.save(`${this.state.name || 'AI Insight'}.pdf`);
            this.showActionMessage("Downloaded");
        } catch (error) {
            console.error("Failed to export AI insight PDF:", error);
            this.showActionMessage("PDF download failed. Please try again.");
        } finally {
            this.state.downloading = false;
        }
    }


    async handleChatKeydown(ev) {
        if(!this.state.isResponding && !ev.shiftKey && ev.key === "Enter" && this.state.chat.trim()) {
            ev.preventDefault()
            await this.makeResponse()
        }
    }

    async makeResponse() {
        const chat = this.state.chat
        this.state.chat = ""
        this.state.isResponding = true
        await this.getResponse(chat)
    }

    async getResponse(chat) {
        const requestId = this.chatHistory.addMessage({role: "user", content: chat}, 0)
        const chatId = this.chatHistory.addMessage({role: "assistant", content: ""}, 0)
        setTimeout(() => scrollToView('.proxy-bottom'), 200)
        const {is_error, api_error, cut, explanation, request_token, response_token} = await this.orm.call("dashboard.sheet", "chat_with_ai", [chat, this.chatHistory.conversationHistory])
        this.chatHistory.updateToken(request_token, requestId)
        this.chatHistory.updateMessageNToken(explanation, response_token, chatId)
        this.state.isResponding = false
    }

    get style() {
        return {
            height: `40vh;`,
            width: `100%;`,
        }
    }

    static props = {
        close: {type: Function, optional: false},
        currentTheme: {type: String, optional: true},
        options: {type: Object, optional: false},
        theme: {type: Object, optional: false},
        isDarkMode: {type: Boolean, optional: true},
    }
    static defaultProps = {
        isDarkMode: false
    }
}

ExplainAIModal.template = "ExplainAIModal";
ExplainAIModal.components = {
    Dialog, GraphTile, ChatThread
}
