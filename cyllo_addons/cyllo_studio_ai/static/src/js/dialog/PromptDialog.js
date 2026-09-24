/** @odoo-module **/
import {
    Component,
    useState,
    onWillUnmount
} from "@odoo/owl";
import {
    useService,
    useBus
} from "@web/core/utils/hooks";
import {
    browser
} from "@web/core/browser/browser";
import {
    registry
} from "@web/core/registry";
import {
    _t
} from "@web/core/l10n/translation";

export class PromptDialog extends Component {
    setup() {
        this.user = useService("user");
        const {
            origin
        } = browser.location;
        const {
            userId
        } = this.user;
        this.state = useState({
            prompt: "",
            updates: [], // Holds chat history
            user_image: `${origin}/web/image?model=res.users&field=avatar_128&id=${userId}`,
            savedConversations: [], // Holds all saved conversation summaries
            selectedConversationId: null,
            showSuggestions: false,
            showSecondSuggestions: false,
            loading: false,
            isSidebarOpen: true,
            suggestedPrompts: [
                "Build a module for ",
                "Create a module for",
                "Create an app for"
            ]
        });
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.notificationService = useService('effect')
        this.rpc = useService("rpc");
        this.menuService = useService("menu");
        this.loadSavedConversations();
        this.env.bus.trigger('TOGGLE_MENU_SIDEBAR', {
            hideMenu: true
        })
        onWillUnmount(() => {
            this.env.bus.trigger('TOGGLE_MENU_SIDEBAR', {
                hideMenu: false
            });
        });
    }
    //Function to load previous history
    async loadSavedConversations() {
        try {
            const savedConversations = await this.orm.call(
                "conversation.history",
                "search_read",
                [], {
                    fields: ["id", "name", "prompts", "responses"],
                    limit: 10,
                    order: "create_date desc"
                }
            );
            this.state.savedConversations = savedConversations
                .filter((conv) => {
                    const prompts = JSON.parse(conv.prompts || "[]");
                    const responses = JSON.parse(conv.responses || "[]");
                    return prompts.length > 0 || responses.length > 0;
                })
                .map((conv) => ({
                    id: conv.id,
                    summary: conv.name,
                }));
        } catch (error) {
            console.error("Error loading saved conversations:", error);
            this.notification.add("Failed to load saved conversations.", {
                type: "danger"
            });
        }
    }
    handleKeyDown(event) {
        if (event.key === "Enter") {
            this.onSendPrompt();
        }
    }
    showSecondSuggestions() {
        this.state.showSecondSuggestions = true;
    }
    showSuggestions() {
        this.state.showSuggestions = true;
    }
    onInput() {
        // Hide suggestions when user starts typing
        if (this.state.prompt) {
            this.state.showSuggestions = false;
        }
        const sendIcon = document.querySelector('.cy-ai_send-icon');
        sendIcon.classList.remove('d-none');

    }
    selectPrompt(prompt) {
        this.state.prompt = prompt;
        this.state.showSuggestions = false;
    }
    async onSendPrompt() {
        const prompt = this.state.prompt.trim();
        if (!prompt) {
            this.notification.add("Please enter a prompt.", {
                type: "warning"
            });
            return;
        }
        // Prepare the last response
        const lastResponse =
            this.state.updates.length > 0 ?
            this.state.updates[this.state.updates.length - 1].description :
            null;
        // Temporary placeholder for the response, not added to state yet
        const tempUpdate = {
            prompt: prompt,
            description: {
                module_name: "Processing...",
                model_name: "",
                fields: []
            },
        };
        try {
            this.state.loading = true;
            const response = await this.rpc("/cyllo_studio/analyze/prompt", {
                prompt: prompt,
                previous_response: lastResponse,
            });
            if (response.error) {
                this.notification.add(response.error, {
                    type: "danger"
                });
                return;
            }
            // Parse and update the response
            const parsedContent =
                typeof response.content === "string" ? JSON.parse(response.content) : response.content;

            this.state.updates.push({
                prompt: prompt,
                description: parsedContent || {},
            });
            await this.saveConversation();
            this.state.prompt = "";
        } catch (error) {
            console.error("Error fetching module description:", error);
            this.notification.add("Invalid Prompt. Please try again.", {
                type: "danger"
            });
        } finally {
            this.state.loading = false;
        }
    }
    //Function to create the module
    async createModule() {
        let module_details = this.state.updates;
        try {
            this.state.loading = true
            // Get the last element from the updates array
            const lastUpdate = module_details[module_details.length - 1];
            const response = await this.rpc("/cyllo_studio/create/module", {
                module_details: [lastUpdate],
            });
            if (response.redirect_url) {
                if (this.state.selectedConversationId) {
                    try {
                        await this.orm.call(
                            "conversation.history",
                            "unlink",
                            [
                                [this.state.selectedConversationId]
                            ]
                        );
                        // Update the local state to remove the conversation
                        this.state.savedConversations = this.state.savedConversations.filter(
                            conv => conv.id !== this.state.selectedConversationId
                        );
                        // Reset the selected conversation ID
                        this.state.selectedConversationId = null;
                    } catch (error) {
                        console.error("Error deleting conversation:", error);
                        this.notification.add("Failed to remove conversation from history.", {
                            type: "warning"
                        });
                    }
                }
                localStorage.setItem("cy_selected_app", response.AppMenu || false)
                localStorage.setItem("selectedAppName", response.AppName || false)
                window.location.href = response.redirect_url;
                window.location.reload()
            } else if (response.error) {
                this.state.loading = false;
                this.notificationService.add({
                    title: _t("Module Already Exists"),
                    message: response.error,
                    description: "",
                    type: "notification_panel",
                    notificationType: "warning",
                });
            } else {
                alert('Module created successfully.');
            }
        } catch (error) {
            console.error("Error saving conversation:", error);
            this.notification.add("Failed to save conversation.", {
                type: "danger"
            });
        }
    }
    //To load conversation on clicking the history
    async loadConversation(conversationId) {
        try {
            const conversation = await this.orm.call("conversation.history", "read", [
                [conversationId],
                ["prompts", "responses"]
            ]);
            if (conversation.length > 0) {
                const {
                    prompts,
                    responses
                } = conversation[0];
                this.state.updates = JSON.parse(prompts).map((prompt, index) => ({
                    prompt,
                    description: JSON.parse(responses)[index],
                }));
                this.state.selectedConversationId = conversationId;
            }
        } catch (error) {
            console.error("Error loading conversation:", error);
            this.notification.add("Failed to load conversation.", {
                type: "danger"
            });
        }
    }
    //To start new chat and clear the chat area
    startNewChat() {
        this.state.updates = [];
        this.state.prompt = "";
        this.state.loading = false;
        this.state.showSuggestions = false;
        this.state.selectedConversationId = null;
        const chatContainer = document.querySelector(".main-chat-section");
        if (chatContainer) {
            chatContainer.scrollTop = 0;
        }
    }
    //  Function to  Hide side bar
    hideSidebar() {
        const sidebar = document.getElementById("sidebar");
        if (!sidebar) return; // Exit if sidebar not found
        sidebar.classList.add("hidden");
        // Only manipulate other elements if they exist
        const modalContent = document.querySelector(".cy-modal_content_ai");
        if (modalContent) {
            modalContent.classList.add("full-width");
        }
        const sidebarToggleBtn = document.querySelector(".cy-sidebar_toggle-btn");
        if (sidebarToggleBtn) {
            sidebarToggleBtn.classList.add("visible");
        }
    }
    //  Function to  Show side bar
    showSidebar() {
        const sidebar = document.getElementById("sidebar");
        if (!sidebar) return;
        sidebar.classList.remove("hidden");
        const modalContent = document.querySelector(".cy-modal_content_ai");
        if (modalContent) {
            modalContent.classList.remove("full-width");
        }
        const sidebarToggleBtn = document.querySelector(".cy-sidebar_toggle-btn");
        if (sidebarToggleBtn) {
            sidebarToggleBtn.classList.remove("visible");
        }
    }
    //Exit function
    async exitToHome() {
        this.env.services.ui.block();
        try {
            const ExistingStudioPage = localStorage.getItem('ExistingStudioPage');
            const data = ExistingStudioPage ? ExistingStudioPage.split(",") : null;

            if (data) {
                localStorage.setItem("cy_selected_menu", data[1] || false);
                window.location.href = data[0];
            }
            localStorage.removeItem('ExistingStudioPage');
        } finally {
            window.location.reload()
            setTimeout(() => {
                this.env.services.ui.unblock();
            }, 800);
        }

    }
    async saveConversation() {
        try {
            if (this.state.selectedConversationId) {
                // Update the existing conversation
                await this.orm.call("conversation.history", "write", [
                    [this.state.selectedConversationId],
                    {
                        prompts: JSON.stringify(this.state.updates.map((upd) => upd.prompt)),
                        responses: JSON.stringify(this.state.updates.map((upd) => upd.description)),
                    },
                ]);
            } else if (this.state.updates && this.state.updates.length > 0) {
                // Create a new conversation only if no conversation is currently selected
                const response = await this.orm.call("conversation.history", "create", [{
                    name: this.state.updates[0]?.prompt || "New Conversation",
                    prompts: JSON.stringify(this.state.updates.map((upd) => upd.prompt)),
                    responses: JSON.stringify(this.state.updates.map((upd) => upd.description)),
                }, ]);
                const newId = Array.isArray(response) ? response[0] : response;
                this.state.selectedConversationId = newId;
            }
        } catch (error) {
            console.error("Error saving conversation:", error);
            this.notification.add("Failed to save conversation.", {
                type: "danger"
            });
        }
    }
    async deleteConversation(conversationId) {
        await this.orm.call("conversation.history", "unlink", [
            [conversationId]
        ]);
        this.state.savedConversations = this.state.savedConversations.filter(
            (conversation) => conversation.id !== conversationId
        );
        this.render();
    }
}
PromptDialog.template = 'cyllo_studio_ai.PromptDialog';
registry.category('actions').add('PromptDialog', PromptDialog);