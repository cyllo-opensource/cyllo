/** @odoo-module **/
import {Component, onMounted, useRef, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class VoiceNote extends Component {
    setup() {
        this.player = useRef("player");
        this.playBtn = useRef("playBtn");
        this.seekBar = useRef("seekBar");
        this.orm = useService('orm')

        this.state = useState({
            elapsed: "0:00",
            total: "--:--",
            showElapsed: false,
            partner: this.props.partner,
            msgState: this.props.state
        });

        onMounted(async () => {
            const player = this.player.el;
            const seekBar = this.seekBar.el;

            // Get total duration once metadata is loaded
            player.addEventListener("loadedmetadata", () => {
                this.state.total = this.formatTime(player.duration);
            });

            // Update elapsed time while playing
            player.addEventListener("timeupdate", () => {
                if (!isNaN(player.duration)) {
                    const value = (player.currentTime / player.duration) * 100;
                    seekBar.value = value
                    this.state.elapsed = this.formatTime(player.currentTime);
                    seekBar.style.setProperty("--range-progress", value + "%");
                }
            });

            // Reset to total when finished
            player.addEventListener("ended", () => {
                this.playBtn.el.innerHTML = "<i class='ri-play-fill'></i>";
                this.state.showElapsed = false;
            });

            seekBar.addEventListener("input", () => {
                // Jump audio to that position
                player.currentTime = (seekBar.value / 100) * player.duration;
                seekBar.style.setProperty("--range-progress", seekBar.value + "%");
            });
        });
    }

    togglePlay() {
        const player = this.player.el;
        const playBtn = this.playBtn.el;

        if (player.paused) {
            // Pause all other audios
            document.querySelectorAll("audio").forEach(audio => {
                if (audio !== player) {
                    audio.pause();
                    const btn = audio.closest(".voice-message")?.querySelector("button");
                    if (btn) btn.innerHTML = "<i class='ri-play-fill'></i>";
                    const cmp = owl.Component.current?.parent; // in case we track others
                }
            });

            player.play();
            playBtn.innerHTML = "<i class='ri-pause-line'></i>";
            this.state.showElapsed = true;   // show elapsed while playing
        } else {
            player.pause();
            playBtn.innerHTML = "<i class='ri-play-fill'></i>";
            this.state.showElapsed = false;  // back to total when paused
        }
    }

    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, "0")}`;
    }
}

VoiceNote.template = "VoiceNote";
