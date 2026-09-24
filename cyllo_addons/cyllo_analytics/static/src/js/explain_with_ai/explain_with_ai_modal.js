/** @odoo-module **/
import {Component, markup, onMounted, onWillStart, useRef, useState} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import {GraphTile} from "@cyllo_analytics/js/presentation/components/graph_tile";
import {ThemeMaker} from "../theme_maker";
import {SelectUser} from "./components/select_user";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {chatHistory} from "./chatHistory";
import {ChatThread, scrollToView, setStringByLetter} from "./components/chatThread"

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
            cut: 100,
            chatMode: false,
            chat: "",
            isResponding: false,
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
        this.actionService.doAction({
            name: _t("Settings"),
            type: "ir.actions.act_window",
            res_model: "res.config.settings",
            views: [[false, "form"]],
            view_mode: "form",
            target: "main",
            context: {
                module: 'cyllo_analytics_settings'
            },
        })
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
        const {is_error, api_error, cut, explanation, request_token, response_token} = await this.orm.call("dashboard.sheet", "explain_with_ai", [promptData, retry])
        this.chatHistory.updateToken(request_token, requestId)
        this.chatHistory.updateMessageNToken(explanation, response_token, chatId)
        this.state.error = is_error
        this.state.cut = Math.ceil(cut * 100)
        this.state.apiError = api_error
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
        const message = "Copied to Clipboard!"
        this.showActionMessage(message)
        var textArea = document.createElement("textarea");
        textArea.value = htmlToText(this.explain);
        document.body.appendChild(textArea);
        textArea.select();
        var successful = document.execCommand('copy');
        document.body.removeChild(textArea)
        return successful;
    }

    download() {
        if (this.state.error) return;

        // 1. Create the global print wrapper
        var printDiv = document.createElement('div');
        printDiv.style.position = 'absolute';
        printDiv.style.left = '-9999px';
        printDiv.style.top = '0';
        printDiv.style.width = '1000px';
        printDiv.style.backgroundColor = '#ffffff';
        printDiv.style.color = '#333';
        printDiv.style.fontFamily = 'Arial, sans-serif';

        // 2. Build the Purple Header (Matches your image exactly)
       var header = document.createElement('div');
        // Fetch the primary theme color from the dashboard's current theme properties
        header.style.backgroundColor = this.props.theme.theme_color_ids ? this.props.theme.theme_color_ids[0] : '#6a0dad';
        header.style.color = 'white';
        header.style.padding = '20px 40px';
        header.style.display = 'flex';
        header.style.justifyContent = 'space-between';
        header.style.alignItems = 'center';

        var leftHeader = document.createElement('div');
        leftHeader.innerHTML = '<span style="font-size:20px; margin-right:8px;">❖</span><b style="font-size: 20px; letter-spacing: 2px;">AI Insights</b>';

        var rightHeader = document.createElement('div');
        rightHeader.innerText = this.state.name || 'AI Insight';
        rightHeader.style.fontSize = '14px';

        header.appendChild(leftHeader);
        header.appendChild(rightHeader);
        printDiv.appendChild(header);

        // 3. Create a wrapper for the body content purely for padding
        var contentWrapper = document.createElement('div');
        contentWrapper.style.padding = '10px 40px 40px 40px';
        printDiv.appendChild(contentWrapper);

        // 4. Insert the Chart Image cleanly at the top
        if (this.state.imgSrc) {
            var img = document.createElement('img');
            img.src = this.state.imgSrc;
            img.style.width = '100%';
            img.style.height = 'auto';
            img.style.display = 'block';
            img.style.marginBottom = '20px';
            contentWrapper.appendChild(img);
        }

        // 5. Add the Horizontal Separator Line below the chart
        var hr = document.createElement('hr');
        hr.style.border = 'none';
        hr.style.borderTop = '2px solid #e0e0e0'; // Light grey line
        hr.style.marginBottom = '30px';
        contentWrapper.appendChild(hr);

        // 6. Clone the styled AI Explanation Text below the line
        var textContainer = this.rootRef.el.querySelector('.explain-text-container');
        if (textContainer) {
            var clonedText = textContainer.cloneNode(true);

            // Remove the interactive button tools
            var footerTools = clonedText.querySelector('.explain-footer');
            if (footerTools) footerTools.remove();

            // Ensure no scrollbars cut off bullets
            clonedText.style.height = 'max-content';
            clonedText.style.overflow = 'visible';
            clonedText.style.fontSize = '15px';
            clonedText.style.lineHeight = '1.8';
            clonedText.style.color = '#000000';
            clonedText.querySelectorAll('*').forEach(el => {el.style.color = '#000000';});
            contentWrapper.appendChild(clonedText);
        }

        document.body.appendChild(printDiv);

        // 7. Capture the assembled beauty with html2canvas
        html2canvas(printDiv, { scale: 2 }).then(async (canvas) => {

            document.body.removeChild(printDiv);

            var imgData = canvas.toDataURL('image/png');
            var pdf = new jsPDF('p', 'mm', 'a4');

            var pageWidth = pdf.internal.pageSize.getWidth();
            var pageHeight = pdf.internal.pageSize.getHeight();

            var imgWidth = pageWidth;
            var imgHeight = (canvas.height * imgWidth) / canvas.width;

            // Calculate exact total pages realistically for the footer
            var totalPages = Math.ceil(imgHeight / pageHeight);
            var currentPage = 1;

            var heightLeft = imgHeight;
            var position = 0;

            // Stamp Page 1
            pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);

            // Add native "Page 1 of X" text to the absolute bottom of PDF Page 1
            pdf.setFontSize(9);
            pdf.setTextColor(150); // Muted grey
            pdf.text(`Page ${currentPage} of ${totalPages}`, pageWidth / 2, pageHeight - 8, { align: 'center' });

            heightLeft -= pageHeight;

            // Mathematically slice remaining pages in loop
            while (heightLeft > 0) {
                position = heightLeft - imgHeight;
                pdf.addPage();

                currentPage++;

                pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);

                // Add "Page X of Y" to subsequent pages
                pdf.text(`Page ${currentPage} of ${totalPages}`, pageWidth / 2, pageHeight - 8, { align: 'center' });

                heightLeft -= pageHeight;
            }

            pdf.save(`${this.state.name || 'AI Insight'}.pdf`);
            this.showActionMessage("Downloaded");
        });
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
            height: `55vh;`,
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