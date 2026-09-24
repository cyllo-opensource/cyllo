/** @odoo-module **/
import { Component, markup, useState, onMounted, useRef} from "@odoo/owl";
import { useService } from '@web/core/utils/hooks';
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { ChatOption } from './chat_option'
import { VoiceNote } from "./voice_note";

/* Create new WhatsappChatHistory by extending Component */
export class WhatsappChatHistory extends Component {
    async setup() {
        this.store = useService("mail.store");
        this.fileViewerInstance = new useFileViewer();
        this.search = useRef("search");
        this.player = useRef("player");
        this.playBtn = useRef("playBtn");
        this.seekBar = useRef("seekBar");
        this.orm = useService('orm')
            this.state = useState({
            message_loaded: true,
            searchResults:false
        })
        onMounted(() => {
            const player = this.player.el;
            const seekBar = this.seekBar.el;

            player?.addEventListener("timeupdate", () => {
                seekBar.value = (player.currentTime / player.duration) * 100;
            });

            seekBar?.addEventListener("input", () => {
                player.currentTime = (seekBar.value / 100) * player.duration;
            });
        });
    }

    getMarkup(text) {
        return markup(text)
    }

    LoadMoreChat(){
        this.state.message_loaded=false
        this.env.bus.trigger('All_MESSAGE')
    }

    togglePlay() {
        const player = this.player.el;
        const playBtn = this.playBtn.el;

        if (player.paused) {
            player.play();
            playBtn.textContent = "⏸ Pause";
        } else {
            player.pause();
            playBtn.textContent = "▶ Play";
        }
    }

    async viewDocument(attachment) {
        let mimetype;
        let type = attachment[1].split('.').pop()
        if (type === 'pdf') {
            mimetype = 'application/pdf';
        } else if (type === 'png') {
            mimetype = 'image/png';
        } else if (type === 'jpeg') {
            mimetype = 'image/jpeg';
        } else if (type === 'jpg') {
            mimetype = 'image/jpeg';
        } else if (type === 'mp4') {
            mimetype = 'video/mp4';
        }
        const preview = this.store.Attachment.insert({
            id: attachment[0],
            filename: attachment[1],
            name: attachment[1],
            mimetype: mimetype
        });
        this.fileViewerInstance.open(preview);
    }

    getFileExtension(attachmentName) {
        let extension = attachmentName.split('.').pop()
        let fileType = {
            'docx': 'docx.png',
            'doc': 'doc.png',
            'pdf': 'pdf.png',
            'txt': 'txt.png',
            'ppt': 'ppt.png',
            'xls': 'xls.png',
            'xlsx': 'xlsx.png',
            'png': 'png.png',
            'jpg': 'jpeg.png',
            'jpeg': 'jpeg.png',
            'mp3': 'mp3.png',
            'mp4': 'mp4.png',
            'zip': 'zip.png'
        }
        return fileType[extension] || 'doc.png';
    }

    MessageSearch() {
        const prevElement = document.getElementById(this.state.selectedResultId);
        if (prevElement) {
            prevElement.classList.remove('highlight');
        }
        const searchValue = this.search.el.value.toLowerCase();
        if(this.search.el.value==''){
            this.state.searchResults = [];
            this.state.selectedResultId = null;
            this.currentResultIndex = 0;
        }
        const searchResults = this.props.history.filter(r =>
            r.message && typeof r.message === 'string' &&
            r.message.toLowerCase().includes(searchValue.toLowerCase())
        );
        if (searchResults.length > 0) {
            this.currentResultIndex = 0;
            this.scrollToResult(searchResults[this.currentResultIndex].id);
            this.state.searchResults = searchResults;
        }
    }

    scrollToResult(resultId) {
    // Remove the highlight from the previously selected result
        if (this.state.selectedResultId) {
            const prevElement = document.getElementById(this.state.selectedResultId);
            if (prevElement) {
                prevElement.classList.remove('highlight');
            }
        }
        const resultElement = document.getElementById(resultId);
        if (resultElement) {
            resultElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            resultElement.classList.add('highlight');
            this.state.selectedResultId = resultId;
        }
    }

    nextResult() {
        if (this.currentResultIndex < this.state.searchResults.length - 1) {
            this.currentResultIndex++;
            this.scrollToResult(this.state.searchResults[this.currentResultIndex].id);
        }
    }

    previousResult() {
        if (this.currentResultIndex > 0) {
            this.currentResultIndex--;
            this.scrollToResult(this.state.searchResults[this.currentResultIndex].id);
        }
    }

    clearSearch() {
        this.search.el.value = '';
        this.state.searchResults = [];
        this.state.selectedResultId = null;
        this.currentResultIndex = 0;
        const highlightedElement = document.querySelector('.highlight');
        if (highlightedElement) {
            highlightedElement.classList.remove('highlight');
        }
    }

    async generateThumbnail(file) {
        return new Promise((resolve, reject) => {
            const video = document.createElement("video");
            video.src = URL.createObjectURL(file);
            video.crossOrigin = "anonymous";
            video.muted = true;
            video.playsInline = true;

            video.addEventListener("loadeddata", () => {
                // Seek to 1 second (skip black intro frames)
                video.currentTime = Math.min(1, video.duration / 2);
            });

            video.addEventListener("seeked", () => {
                const canvas = document.createElement("canvas");
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;

                const ctx = canvas.getContext("2d");
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

                canvas.toBlob((blob) => {
                    resolve(blob); // Thumbnail as Blob (PNG by default)
                    URL.revokeObjectURL(video.src);
                }, "image/jpeg", 0.8); // you can use "image/webp"
            });

            video.addEventListener("error", (err) => reject(err));
        });
    }


    get randomStatusGradient() {
        const palette = ["#4EB8C4", "#96CBFC", "#C2E1FC", "#FFC2D9", "#FF99BE"];
        const c1 = palette[Math.floor(Math.random() * palette.length)];
        let c2 = palette[Math.floor(Math.random() * palette.length)];

        while (c1 === c2) {
            c2 = palette[Math.floor(Math.random() * palette.length)];
        }

        return `linear-gradient(45deg, ${c1}, ${c2})`;
    }

}
WhatsappChatHistory.template = 'WhatsappChatHistory';

WhatsappChatHistory.components = {
    ChatOption,
    VoiceNote
}