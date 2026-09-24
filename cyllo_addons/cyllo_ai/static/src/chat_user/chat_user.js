/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
export class ChatUser extends Component{
    static props = {
        text: { type: String, optional: true},
        html: { type: String, optional: true},
        userImage: { type: String, optional: true},
        // An opaque payload for a host-contributed chat-chart component (e.g. the
        // chart the user is asking about). Rendered via the "cyllo_ai.chat_chart"
        // registry slot, full-width above the message bubble.
        chart: { validate: (v) => v === null || typeof v === "object", optional: true },
    };
    setup(){
    super.setup(...arguments);

    }
    /** The chat-chart component a host module registered (or null). */
    get chartComponent() {
        return registry.category("cyllo_ai.chat_chart").get("component", null);
    }

    /**
     * A select-to-quote excerpt rides baked into the plain text (see
     * handleSend in chatbot.js — chatbot.history has no side channel for it):
     * "> collapsed one-line excerpt", a blank line, then the real message.
     * Parsed here so it renders as the same rounded quote-strip card the
     * composer shows while composing, instead of a raw ">" markdown line.
     * Returns null when the message doesn't start with one.
     */
    get quotedExcerpt() {
        const raw = String(this.props.text || "");
        const m = raw.match(/^> ([^\n]+)\n\n([\s\S]*)$/);
        return m ? { quote: m[1], rest: m[2] } : null;
    }

    /** The message text with any leading quote block (see quotedExcerpt)
     *  already stripped off — what every other render path should use. */
    get bodyText() {
        const q = this.quotedExcerpt;
        return q ? q.rest : String(this.props.text || "");
    }

    /**
     * @ mentions are real inline pill TOKENS in the live composer (see
     * insertPillAtPendingRange in chatbot.js), but chatbot.history only ever
     * stores plain text, and a pill's plain-text mirror is "@[Name]" /
     * "@[Name → Record]" wherever it sat in the sentence. Splitting the WHOLE
     * message on that pattern here — not just a leading line — turns each one
     * back into a pill for display, live or reloaded, in its original spot.
     * The brackets make the pattern unambiguous against a stray "@word" the
     * user typed themselves or an email address, neither of which has one.
     * Returns null (falls back to the plain bubble) when there's no match.
     */
    get mentionParts() {
        const raw = this.bodyText;
        const re = /@\[([^\]]+)\]/g;
        let last = 0;
        let m;
        const parts = [];
        while ((m = re.exec(raw))) {
            if (m.index > last) parts.push({ type: "text", value: raw.slice(last, m.index) });
            const [name, recordName] = m[1].split(" → ");
            parts.push({ type: "pill", name: (name || "").trim(), recordName: recordName ? recordName.trim() : null });
            last = re.lastIndex;
        }
        if (!parts.length) return null;
        if (last < raw.length) parts.push({ type: "text", value: raw.slice(last) });
        return parts;
    }
}
ChatUser.template = "ChatUser";
