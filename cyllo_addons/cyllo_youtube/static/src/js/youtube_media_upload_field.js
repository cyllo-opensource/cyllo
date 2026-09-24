/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { many2ManyBinaryField } from "@web/views/fields/many2many_binary/many2many_binary_field";
import { MediaUploadField } from "@cyllo_social_media_marketing/js/media_upload_field";


export class YoutubeMediaUploadField extends MediaUploadField {
    setup() {
        super.setup();
        this.ui = useService("ui");
    }

    async onFileUploaded(files) {
        await super.onFileUploaded(files);
        if (!this.props.record.data.post_on_youtube) {
            return;
        }
        for (const file of files) {
            if (!file.error) {
                await this._uploadToYoutube(file);
            }
        }
    }

    async _uploadToYoutube(file) {
        const record = this.props.record;
        if (!record.resId) {
            this.notification.add(_t("Save the post before uploading a YouTube video."), { type: "warning" });
            return;
        }
        this.ui.block();
        try {
            const credential = await this.orm.call("social.media.post", "get_youtube_account", [[record.resId]]);
            const contentBlob = await (await fetch(`/web/content/${file.id}`)).blob();
            const initResponse = await fetch(
                "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status,contentDetails",
                {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${credential.key}`,
                        "Content-Type": "application/json; charset=UTF-8",
                        "X-Upload-Content-Length": contentBlob.size,
                        "X-Upload-Content-Type": contentBlob.type,
                    },
                    body: JSON.stringify({
                        status: { privacyStatus: "private" },
                        snippet: {
                            title: credential.details.name,
                            description: credential.details.description,
                        },
                    }),
                }
            );
            const location = initResponse.headers.get("Location");
            if (!location) {
                this.notification.add(_t("Exceeded Daily Upload Limit, Check Account"), { type: "warning" });
                return;
            }
            const uploadResponse = await fetch(location, {
                method: "PUT",
                headers: {
                    Authorization: `Bearer ${credential.key}`,
                    "Content-Length": contentBlob.size,
                    "Content-Type": contentBlob.type,
                },
                body: contentBlob,
            });
            const result = await uploadResponse.json();
            await record.update({ youtube_video_number: result.id, state: "queue" });
        } catch {
            this.notification.add(_t("Exceeded Daily Upload Limit, Check Account"), { type: "warning" });
        } finally {
            this.ui.unblock();
        }
    }
}

registry.category("fields").add("youtube_media_upload_field", {
    ...many2ManyBinaryField,
    component: YoutubeMediaUploadField,
});
