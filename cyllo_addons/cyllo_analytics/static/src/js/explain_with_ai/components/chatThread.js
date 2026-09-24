/** @odoo-module */
import {Component, useState, onWillUpdateProps, markup, useEffect, useRef} from "@odoo/owl";

export const scrollToView = (selector, args = {}) => {
    const element = document.querySelector(selector);
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start' ,
            ...args
        });
    } else {
        console.error(`Element with class ${selector} not found.`);
    }
}

export const setStringByLetter = (stateRef, key, text, footer= ".proxy-bottom") => {
    const words = text.split(" ");
    let index = 0;

    let intervalId = setInterval(() => {
        if (index < words.length) {
            stateRef[key] += words[index] + " ";
            index++;
        } else {
            clearInterval(intervalId);
        }
        scrollToView(footer)
    }, 50);
}

export class ChatThread extends Component {
    static template = "ChatThread";
    setup() {
        this.root = useRef("root")
        this.state = useState({
            explain: this.chat.content || "",
            copied: false,
        })
        let isFirstTime = true
        useEffect((content) => {
            if (!isFirstTime) {
                setStringByLetter(this.state, 'explain', content)
            }
            isFirstTime = false
        }, () => [this.props.chat.content])
    }

    get chat() {
        return this.props.chat;
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

    copyToClip() {
        this.state.copied = true
        const text = this.root.el.querySelector(".text").innerText
        const tempInput = document.createElement('textarea');
        tempInput.value = text;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);
        setTimeout(() => this.state.copied = false, 1000)
    }
}