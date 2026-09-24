/** @odoo-module **/
import {Component, onMounted, useRef, useState} from "@odoo/owl";
import {useService} from '@web/core/utils/hooks';
import {useEmojiPicker} from "@web/core/emoji_picker/emoji_picker";
import {_t} from "@web/core/l10n/translation";

/* Create new WhatsappChatInput by extending WhatsappChatInput */
export class WhatsappChatInput extends Component {
    /* This function appears to initialize various properties and set up event listeners.*/
    async setup() {
        this.state = useState({
            recording: 0,
            mp3File: '',
            onMic: 0,
            blob: '',
            audioFileNumber: 1,
            audioTrack: '',
            audioRecorder: '',
            composer: 0,
            playing: false,
            progress: 0,
            currentTime: "0:00",
            duration: "0:00",
            recordingTimer: 0,
            formattedTime: "00:00",
        })
        this.notification = useService("notification")
        this.ui = useState(useService("ui"));
        this.notification = useService("notification");
        this.audioPlayer = useRef('audioPlayer');
        this.inputRef = useRef('textarea')
        this.imageInput = useRef('imageInput')
        this.fileInput = useRef('fileInput')
        this.orm = useService('orm')
        this.emojiRef = useRef('emoji-button')
        this.ffmpeg = null
        this.emojiPicker = useEmojiPicker(this.emojiRef, {onSelect: this.emojiSelect.bind(this)})

        onMounted(() => {
            window.MediaRecorder = OpusMediaRecorder;
            this.workerOptions = {
                OggOpusEncoderWasmPath: 'https://cdn.jsdelivr.net/npm/opus-media-recorder@latest/OggOpusEncoder.wasm',
                WebMOpusEncoderWasmPath: 'https://cdn.jsdelivr.net/npm/opus-media-recorder@latest/WebMOpusEncoder.wasm'
            };
        })
    }

    togglePlay() {
        const audio = this.audioPlayer.el;
        if (!audio) return;

        if (this.state.playing) {
            audio.pause();
        } else {
            audio.play();
        }
        this.state.playing = !this.state.playing;
    }

    seekAudio(ev) {
        const audio = this.audioPlayer.el;
        const rect = ev.target.getBoundingClientRect();
        const clickX = ev.clientX - rect.left;
        const percent = clickX / rect.width;
        audio.currentTime = percent * audio.duration;
    }

    _formatTime(seconds) {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60).toString().padStart(2, "0");
        return `${m}:${s}`;
    }


    /* Click function emoji*/
    emojiSelect(ev) {
        var inputText = this.inputRef.el.value
        var cursorPosition = this.inputRef.el.selectionStart;
        this.inputRef.el.value = inputText.substring(0, cursorPosition) + ev + inputText.substring(cursorPosition)
        this.state.composer = 1
    }

    /*
    Send button function :  it will create a new record in whatsapp.message model,
    clear input field , and trigger SEND_MESSAGE function using bus
    */
    async sendMessage() {
        this.state.composer = 0
        var messageValues = await this.prepareMessageValues()
        if (messageValues) {
            var currentMessage = await this.orm.call("whatsapp.message", "send_whatsapp_message", [
                messageValues
            ]);
            if (!currentMessage?.error) {
                this.env.bus.trigger('SEND_MESSAGE', {message: currentMessage})
                this.env.bus.trigger('UPDATE_COUNTER', {partner: this.props.channel})
            } else {
                this.notification.add(
                    _t("Can't connect to WhatsApp.\n Please ensure that you are connected with internet."),
                    {
                        title: _t("Check your Internet Connection!"),
                        type: "warning",
                        sticky: false
                    }
                );
            }
        }
    }

    async prepareMessageValues() {
        let imageValues = ''
        let videoValues = ''
        let attachment = ''
        let message = this.inputRef.el ? this.inputRef.el.value : ''
        if (this.props.image) {
            let file = this.imageInput.el.files[0];
            if (file.type.startsWith('video')) {
                videoValues = {
                    'videoContent': this.props.image,
                    'file_name': file.name,
                    'file_type': file.type
                }
            } else if (file.type.startsWith('image')) {
                imageValues = {
                    'imageContent': this.props.image,
                    'file_name': file.name,
                    'file_type': file.type
                }
            }
            this.imageInput.el.form.reset()
        } else if (this.props.document) {
            if (this.props.attachment) {
                attachment = this.props.attachment
            } else {
                attachment = await this.documentAttachment(this.props.document)
            }
        } else if (this.state.mp3File) {
            attachment = await this.documentAttachment(this.state.blob)
            this.state.mp3File = ''
        }
        let messageValues = {
            'channel': this.props.channel,
            'message': message,
            'image': imageValues,
            'video': videoValues,
            'attachment': attachment,
        }
        this.inputRef.el.form.reset()
        return messageValues
    }

    /** function for the enter key to send messages*/
    keyEnter(event) {
    }

    /**
     * Create an attachment record from a document file.
     *
     * @param {File} document - The document file to create an attachment from.
     * @returns {Promise} A promise that resolves to the created attachment record.
     */
    async documentAttachment(document) {
        const content = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.readAsDataURL(document);
            reader.onload = () => {
                resolve(reader.result);
            };
        });

        let base64content = content.split(',')
        let documentName = document.name


        if (document.type === 'audio/ogg; codecs=opus') {
            documentName = `AUD-WA-${Date.now()}.opus`
        }

        let AttachmentValues = {
            name: documentName,
            mimetype: document.type,
            datas: base64content[1],
        }
        return this.orm.create("ir.attachment", [AttachmentValues], {});
    }

    /** Trigger an event to request image preview **/
    async viewImagePreview() {
        this.state.composer = 1
        let image = this.imageInput.el.files[0];
        this.env.bus.trigger('PREVIEW_IMAGE', {imageFile: image})
    }

    /** Trigger an event to request document preview **/
    async viewFilePreview() {
        let file = this.fileInput.el.files[0];
        this.state.composer = 1
        this.env.bus.trigger('PREVIEW_DOCUMENT', {documentFile: file})
    }


    /** Click function of mic to record the voice **/
    async onClickVoice() {
        try {
        const audioStream = await navigator?.mediaDevices?.getUserMedia({audio: true});
        let chunks = []
        const audio = this.audioPlayer.el;
        this.state.recording = 1
        this.state.onMic = 1
        audio?.addEventListener("timeupdate", () => {
            this.state.progress = (audio.currentTime / audio.duration) * 100;
            this.state.currentTime = this._formatTime(audio.currentTime);
            this.state.duration = this._formatTime(audio.duration);
        });

        audio?.addEventListener("ended", () => {
            this.state.playing = false;
        });

        audio?.addEventListener("loadedmetadata", () => {
            this.state.duration = this._formatTime(audio.duration);
        });

        if (this.state.audioRecorder && this.state.audioRecorder.state === "recording") {
            this.stopTimer()
            this.state.audioRecorder.stop();
            this.state.onMic = 0
            this.state.audioTrack.getAudioTracks()[0].stop();
        } else {
            this.state.onMic = 1
            this.state.audioTrack = audioStream;
            const options = MediaRecorder?.isTypeSupported('audio/ogg; codecs=opus') ? { mimeType: "audio/ogg; codecs=opus" } : { mimeType: "audio/webm; codecs=opus" };
            this.state.audioRecorder = new MediaRecorder(audioStream, options, this.workerOptions);
            this.state.audioRecorder.start();
            this.startTimer()
        }
        this.state.audioRecorder.ondataavailable = (e) => {
            chunks.push(e.data);
        };
        this.state.audioRecorder.onstop = async () => {
            this.state.blob = await new Blob(chunks,
                {type: "audio/ogg; codecs=opus"})
            this.audioPlayer.el.src = URL.createObjectURL(this.state.blob);
        }

         } catch (e) {
                console.error(e)

             return  this.notification.add("Please Grant access to the microphone", { type: "warning"})
            }
    }

    startTimer() {
        this.state.secondsElapsed = 0;

        this.state.recordingTimer = setInterval(() => {
            this.state.secondsElapsed++;

            const minutes = String(Math.floor(this.state.secondsElapsed / 60)).padStart(2, "0");
            const seconds = String(this.state.secondsElapsed % 60).padStart(2, "0");

            this.state.formattedTime = `${minutes}:${seconds}`;
        }, 1000);
    }

    stopTimer() {
        clearInterval(this.state.recordingTimer);
        this.state.recordingTimer = null;
        this.state.secondsElapsed = 0;
        this.state.formattedTime = "00:00";
    }


    async sendVoiceMessage() {
        this.state.recording = 0
        this.state.onMic = 0
        this.state.mp3File = await new File(
            [this.state.blob],
            `AUD-WA-${Date.now()}.opus`,
            { type: this.state.blob.type });
        await this.sendMessage();
    }

    deleteAudio() {
        URL.revokeObjectURL(this.audioPlayer.el.src);
        this.audioPlayer.el.src = "";
        this.state.audioTrack.getAudioTracks()[0].stop();
        this.state.blob = null;
        this.state.progress = 0;
        this.state.currentTime = "0:00";
        this.state.duration = "0:00";
        this.state.onMic = 0
        this.state.recording = 0
    }

    get voiceInputProps() {
        return {
            deleteAudio: this.deleteAudio.bind(this),
            sendVoiceMessage: this.sendVoiceMessage.bind(this),
            onClickMic: this.onClickVoice.bind(this),
            onMic: this.state.onMic
        }
    }

    composeMessage(ev) {
        if (ev.key === "Enter") {
            const message = ev.currentTarget.value
            message && this.sendMessage()
            ev.preventDefault();
        }
    }

    checkInput(){
        const message = this.inputRef?.el?.value?.trim() || "";
        this.state.composer = message ? 1 : 0;
    }

}

/* Associate 'WhatsappChatInput' template with the WhatsappChatInput component.*/
WhatsappChatInput.template = 'WhatsappChatInput';