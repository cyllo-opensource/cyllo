/** @odoo-module */
let id = 1
export class chatHistory {
    constructor() {
        this.chatHistory = [
            // {id: 1, role: "user", content: prompt},
            // {id:2, role: "assistant", content: prompt},
        ];
        this.tokenLimit = 16385;
        this.activeTokens = [];
        this.allChatHistory = [{id: 1, role: "user", content: "Please Explain this chart for me...", show: true}]
    }

    get activeChats() {
        return this.allChatHistory.filter(item => item.show)
    }

    get conversationHistory() {
        return this.chatHistory.map(({ role, content }) => ({role, content}));
    }

    makeInitialMessage(promptData) {
        promptData = JSON.stringify(promptData)
        return `Generate an explanation using AI for the given graph data. Graph data ${promptData}. The AI should provide a comprehensive and insightful short explanation of the data presented in the graph, including key trends, anomalies, and any significant insights. The explanation should be suitable for inclusion in a BI dashboard's 'Explain with AI' feature, and it should be clear and understandable to a non-technical audience. Please provide a detailed explanation of the data in the graph, highlighting any critical data points, changes over time, and any correlations or patterns that might be of significance to the viewer. Feel free to use natural language and provide context that enhances the user's understanding of the data. Also, highlight only the important parts (words) with two asterisks at the beginning and at the end. Make sure it is in Markdown language.`;
    }

    addInitialMessage(promptData, token) {
        const initialMessage = {
            id: id++,
            role: "user",
            content: this.makeInitialMessage(promptData),
        };
        return this.addMessage(initialMessage, token, false);
    }

    updateMessage(message, recId) {
        this.allChatHistory.find(item => item.id === recId).content = message
        this.chatHistory.find(item => item.id === recId).content = message
    }

    updateToken(token, recId) {
        this.activeTokens.find(item => item.id === recId).token = token
    }

    updateMessageNToken(message, token, recId) {
        this.updateMessage(message, recId);
        this.updateToken(token, recId)
    }

    addMessage(message, token, show= true) {
        const updatedMsg = {...message, show, id: id++}
        this.chatHistory.push(updatedMsg);
        this.activeTokens.push({id: updatedMsg.id, token});
        this.allChatHistory.push(updatedMsg)
        this.trimHistory(); // Ensure history doesn't exceed token limit
        return updatedMsg.id
    }

    getTotalTokens() {
        return this.activeTokens.reduce((acc, current) => acc + current.token, 0);
    }

    trimHistory() {
        while (this.getTotalTokens() > this.tokenLimit) {
            if (this.chatHistory.length > 0) {
                this.chatHistory.shift(); // Remove the oldest message
                this.activeTokens.shift();
            } else {
                break;
            }
        }
    }
}