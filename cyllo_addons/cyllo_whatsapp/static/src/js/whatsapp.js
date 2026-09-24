/** @odoo-module */

import {registry} from '@web/core/registry';

const actionRegistry = registry.category("actions");
import {useState, Component, onWillStart, onMounted, useRef, useSubEnv, onWillDestroy, useEffect} from "@odoo/owl";
import {useFileViewer} from "@web/core/file_viewer/file_viewer_hook";
import {session} from "@web/session";
import {useBus, useService} from '@web/core/utils/hooks';
import {_t} from "@web/core/l10n/translation";
import {WhatsappSidebar} from './whatsapp_sidebar'
import {WhatsappChatTop} from './whatsapp_chat_top'
import {WhatsappChatInput} from './whatsapp_chat_input'
import {WhatsappWelcome} from './whatsapp_welcome'
import {WhatsappChatHistory} from './whatsapp_chat_history'
import {WhatsappImagePreview} from './whatsapp_image_preview'
import {useSaveContext} from './useSaveContext'


let rotationDegrees = 0;

/* Create new Whatsapp by extending Component */
export class Whatsapp extends Component {
    /* This function appears to initialize various properties and set up event listeners.*/
    setup() {
        this.store = useService("mail.store");
        this.fileViewerInstance = new useFileViewer();
        this.notification = useService("notification");
        this.state = useState({
            channel: [],
            imagePreview: false,
            chatHistory: [],
            imageLoaded: 0,
            offset: 14,
            imageStyle: ' ',
            inputFile: 0,
            attachment: 0,
            id: false,
            activeChannel: false
        });
        const {
            id: chatId,
            saveManually,
            removeManually
        } = useSaveContext()
        this.saveManually = saveManually;
        this.removeManually = removeManually;
        if (chatId) {
            this.state.id = chatId;
        }
        onWillDestroy(removeManually)
        useEffect(() => {
            this.state.id && this.renderChatHistory()
        }, () => [this.state.id])
        this.root = useRef('root')
        this.orm = useService('orm')
        this.dateSplit = []

        onWillStart(async () => {
            await this.fetchChannel();
        });

        useSubEnv({
            session: session,
        })

        useBus(this.env.bus, 'CLICK_PARTNER', async (channel) => {
            const {partner} = channel.detail
            await this.getMessagingPartner(partner)
            await this.fetchChannel();
            await this.renderChatHistory()
        });
        useBus(this.env.bus, 'SEND_MESSAGE', (data) => this.currentMessageUpdate(data.detail.message));
        useBus(this.env.bus, 'All_MESSAGE', () => this.loadMore());
        useBus(this.env.bus, 'PREVIEW_IMAGE', (data) => this.viewPreviewImage(data));
        useBus(this.env.bus, 'PREVIEW_DOCUMENT', (data) => this.viewPreviewDocument(data));
        useBus(this.env.bus, 'SEARCH_PARTNER', (data) => this.addChattingPartner(data.detail.partner));
        this.busService = this.env.services.bus_service
        this.channel = "WHATSAPP-CHANNEL"
        this.busService.addChannel(this.channel)
        this.busService.subscribe("notification", this.onMessage.bind(this))
        this.busService.subscribe("STATE-UPDATE", this.onStateUpdate.bind(this))
    }

    async onMessage(response) {
        try {
            const msg = response?.message?.[0];
            if (!msg) return;

            if (session?.uid) {
                this.state.channel = await this.orm.searchRead(
                    "whatsapp.channel",
                    [["user_id", "=", session.uid]],
                    []
                );
            }

            if (this.state.id === msg.channel_id?.[0]) {
                await this.renderChatHistory();
            }

            this.notification.add(
                _t(msg.message || "Media file"),
                {
                    title: `${msg.channel_id?.[1]} ${_t('messaged you')}`,
                    type: "whatsapp",
                }
            );
        } catch (e) {}
    }


    async onStateUpdate(response) {
        if (this.state.id) {
            await this.renderChatHistory()
        }
    }

    /* asynchronous function that fetches a list of chat partners or contacts. */
    async fetchChannel() {
        this.state.channel = await this.orm.searchRead("whatsapp.channel", [
            ['user_id', '=', session.uid]
        ], []);
    }

    /* adding a chatting partner to a list of partners on global search */
    async addChattingPartner(data) {
        let ChannelValues = ''
        await this.fetchChannel();
        const channelIds = this.state.channel.map(item => item.partner_id[0])
        if (channelIds.includes(data.id)) {
            var live_channel = this.state.channel.filter(r => r.partner_id[0] == data.id)
            await this.getMessagingPartner(live_channel[0])
            return
        }
        ChannelValues = {
            'name': data.name,
            'partner_id': data.id,
            'user_id': session.uid
        }
        let channel = await this.orm.create("whatsapp.channel", [ChannelValues], {});
        let currentChannel = await this.orm.searchRead("whatsapp.channel", [
            ['id', '=', channel[0]]
        ], []);
        await this.fetchChannel();
        await this.getMessagingPartner(currentChannel[0])
    }

    /* Chat history */
    async renderChatHistory() {
        try {
            let channel = await this.orm.read("whatsapp.channel", [this.state.id], []);
            await this.orm.call("whatsapp.message", "get_chat_history", [this.state.id, 25]).then(result => {
                if (result) {
                    result.forEach((chat) => {
                        this.dateSplit = chat['create_date'].split(' ')
                        chat['date'] = this.dateSplit[0]
                        chat['time'] = this.dateSplit[1].split(':').slice(0, 2).join(':');
                    });
                    this.state.chatHistory = result;
                }
            });
            this.state.activeChannel = channel[0];
        } catch (error) {}
    }

    async loadMore() {
        let result = await this.orm.call("whatsapp.message", "get_chat_history", [this.state.id, false]);
        if (result) {
            result.forEach((chat) => {
                this.dateSplit = chat['create_date'].split(' ');
                chat['date'] = this.dateSplit[0];
                chat['time'] = this.dateSplit[1].split(':').slice(0, 2).join(':');
            });
            this.state.chatHistory = result;
        }
    }

    /* Click function of chatting partner at the whatsapp side bar */
    async getMessagingPartner(channel) {
        this.state.id = channel.id
        await this.renderChatHistory();
    }

    get sideBarProps() {
        /*
         Returns all partners.
        */
        return {
            channels: this.state.channel
        }
    }

    get currentChatProps() {
        /*
         Returns activeChannel partner.
        */
        return {
            channel: this.state.activeChannel,
            preview: this.state.imagePreview,
            image: this.state.imageLoaded,
            document: this.state.inputFile,
            attachment: this.state.attachment
        }
    }

    get whatsappChatHistory() {
        /*
        Return active partner messaging history
        */
        let now = new Date();
        let year = now.getFullYear();
        let month = String(now.getMonth() + 1).padStart(2, '0'); // Adding 1 because months are zero-based
        let day = String(now.getDate()).padStart(2, '0');

        // Create the formatted date string
        let formattedDate = `${year}-${month}-${day}`;

        return {
            history: this.state.chatHistory,
            today: formattedDate,
            partner: this.state.activeChannel
        }
    }

    /*
    Set imagePreview as false when closing image preview
    */
    async closePreview() {
        this.state.imagePreview = false
        this.state.imageLoaded = 0
        this.state.inputFile = 0
        if (this.state.attachment) {
            await this.orm.unlink("ir.attachment", [this.state.attachment[0]]);
        }
    }

    /*
    Rotate image preview in clock-wise direction
    */
    rotateImage(operator, imagePreview) {
        rotationDegrees = operator === '-' ? rotationDegrees -= 90 : rotationDegrees += 90
        this.root.el.querySelector('.whatsapp_image_preview').style.transform = 'rotate(' + rotationDegrees + 'deg)';
        this.state.imageStyle = imagePreview.el.style.transform

    }

    /* To open file using file viewer hook */
    async viewDocument() {
        const content = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.readAsDataURL(this.state.inputFile);
            reader.onload = () => {
                resolve(reader.result);
            };
        });
        let base64content = content.split(',')
        let AttachmentValues = {
            name: this.state.inputFile.name,
            mimetype: this.state.inputFile.type,
            datas: base64content[1],
        }
        this.state.attachment = await this.orm.create("ir.attachment", [AttachmentValues], {});
        const preview = this.store.Attachment.insert({
            id: this.state.attachment,
            filename: this.state.inputFile.name,
            name: this.state.inputFile.data,
            mimetype: this.state.inputFile.type,
        });
        this.fileViewerInstance.open(preview);
    };

    /*
    Returns props to WhatsappImagePreview component
    */
    get whatsappImagePreviewProps() {
        return {
            closePreview: this.closePreview.bind(this),
            image: this.state.imageLoaded,
            rotateImage: this.rotateImage.bind(this),
            inputFile: this.state.inputFile,
            viewDocument: this.viewDocument.bind(this)
        }
    }

    /* To update current sent message to chat history*/
    currentMessageUpdate(data) {
        this.state.imagePreview = false
        this.state.imageLoaded = 0
        this.state.inputFile = 0
        this.dateSplit = data[0].create_date.split(' ')
        data[0]['date'] = this.dateSplit[0]
        data[0]['time'] = this.dateSplit[1].split(':').slice(0, 2).join(':');
        if (this.state.id === data[0]["channel_id"][0]) {
            this.state.chatHistory.push(data[0])
        }
    }

    /* To view the selected image */
    viewPreviewImage(data) {
        this.state.imagePreview = true
        this.state.inputFile = data.detail.imageFile
        const reader = new FileReader();
        reader.readAsDataURL(data.detail.imageFile);
        reader.onload = () => {
            this.state.imageLoaded = reader.result;
        };
    }

    viewPreviewDocument(data) {
        this.state.imagePreview = true
        this.state.inputFile = data.detail.documentFile
    }
}

/* Associate 'Whatsapp' template with the Whatsapp component.*/
Whatsapp.template = 'Whatsapp';
//Child components are added to the `components` of `AppComponent`.
Whatsapp.components = {
    WhatsappSidebar,
    WhatsappChatTop,
    WhatsappChatInput,
    WhatsappWelcome,
    WhatsappChatHistory,
    WhatsappImagePreview,
}
// The `whatsapp_tags` tag is added to the action category.
actionRegistry.add('whatsapp_tags', Whatsapp);