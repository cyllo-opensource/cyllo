/** @odoo-module **/
/**
 * Patch the Odoo ViewButton component to enable Studio editing functionality.
 *
 * Features:
 * - Tracks editing state for normal buttons, smart buttons, new buttons, and Studio edits.
 * - Handles click events to trigger Studio property panels.
 * - Extracts button properties like label, icon, xpath, visibility, groups, and function details.
 * - Communicates changes via the Odoo event bus.
 * - Provides optional striped style for buttons.
 *
 * Uses Owl hooks (useState) and Odoo services (rpc, orm, effect, notification).
 */
import {
    ViewButton
} from "@web/views/view_button/view_button";
import {
    patch
} from "@web/core/utils/patch";
import {
    useService
} from "@web/core/utils/hooks";
import {
    _t
} from "@web/core/l10n/translation";
import {
    useState,
} from "@odoo/owl";
import {
    validateEdit
} from "@cyllo_studio/js/root/studio_wrapper";


patch(ViewButton.prototype, {
    async setup() {
        super.setup();
        this.state = useState({
            ...this.state,
            labelReadOnly: false,
            isEditingButton: false,
            isEditingSmartButton: false,
            isStudioEdit : false,
            isEditingNewButton :false,
        });

        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.notification = useService('effect')
        this.env.bus.addEventListener("BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingButton = detail.isEditingButton
        })
        this.env.bus.addEventListener("SMART_BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingSmartButton = detail.isEditingSmartButton
        })
        this.env.bus.addEventListener("STUDIO_EDIT_STARTED", ({ detail }) => {
            this.state.isStudioEdit = detail.isStudioEdit
        })
        this.env.bus.addEventListener("NEW_BUTTON_EDIT_STARTED", ({ detail }) => {
            this.state.isEditingNewButton = detail.isEditingNewButton
        })


    },
    isStriped() {
        return this.props.attrs?.striped || this.props.striped ? 'cy-studio-striped' : ''
    },


    async onClick(ev) {
        const notification = this.notification || useService("notification");

        if (
            !validateEdit(this.state, notification, "isEditingSmartButton", "Smart Button")
        ) {
            return;
        }
        this.state.isEditingButton = true;
        this.env.bus.trigger('BUTTON_EDIT_STARTED',{
             isEditingButton : this.state.isEditingButton
        });
        this.state.isEditingNewButton = true;
        this.env.bus.trigger('NEW_BUTTON_EDIT_STARTED',{
             isEditingNewButton : this.state.isEditingNewButton
        });

        const buttonEl = ev.target.closest('.cy-listBtn');
        const fallbackString = buttonEl?.querySelector('span')?.textContent?.trim() || '';
        const statBtn = ev.target.closest('.oe_stat_button');
        const rawStatText = statBtn?.querySelector('.o_stat_text')?.textContent?.trim()
            || statBtn?.querySelector('[string]')?.getAttribute('string')
            || '';
        // Reject "0", "1", etc. – those are counts, not labels.
        const nullString = rawStatText && !/^\d+$/.test(rawStatText) ? rawStatText : '';

        // Filter classList to only icon-prefix classes, stripping transient studio classes
        // (e.g. cy-studio-kanban-border) that may be present on the element at click time.
        const getCleanIconClass = (el) => {
            if (!el) return "";
            return [...el.classList]
                .filter(c => c.startsWith("fa") || c.startsWith("ri-"))
                .join(" ");
        };
        const rawIcon = this.props.icon
            || getCleanIconClass(buttonEl?.children[0]?.children[0])
            || getCleanIconClass(buttonEl?.children[0])
            || "";
        const icon = rawIcon?.trim().startsWith("fa") || rawIcon?.trim().startsWith("ri-") ? rawIcon : "";
        let buttonXPath = this.props.attrs["cy-xpath"] || this.props.cyXpath;

        // Resolve the display label: prefer the explicit string prop (if it is
        // not a bare number), then the DOM-derived stat text, then the fallback.
        const propsString = this.props.string || '';
        const resolvedString = (propsString && !/^\d+$/.test(propsString))
            ? propsString
            : (nullString || fallbackString);

        const buttonProperties = {
            string: resolvedString,
            function_type: this.props.clickParams.type,
            function_name: this.props.clickParams.name,
            class: this.props.className,
            groupIds: [],
            invisible: this.props.attrs['invisible'],
            icon: icon,
            element: ev.target,
            path: buttonXPath,
            stringPath: this.props.attrs["stringPath"],
            StatusLabelPath: this.props.attrs["StatusLabelPath"],
            nullString: nullString,
            spanxpath: null,
        };

        //added to get path
        let path = null;
        function findMatchingElement(element) {
          if (!element) return;
          if (
            element.getAttribute('cy-xpath')?.includes('/i') &&
            !element.className.includes('o_button_icon')
          ) {
            path = element.getAttribute('cy-xpath');
            return;  // Exit as we found the match
          }
        }
        findMatchingElement(ev.target);
        if (path) {
            buttonProperties.path = path;
        }
        if (buttonXPath) {
            let spanEl = null;
            const buttonEl = document.querySelector(`[cy-xpath="${buttonXPath}"]`);
            spanEl = buttonEl?.querySelector("span");
            if (spanEl) {
                buttonProperties.spanxpath = spanEl.getAttribute('cy-xpath');
            }
        }

        if (this.props.attrs.groups) {
            buttonProperties.groupIds = await this.rpc(
                "cyllo_studio/find/groups", {
                    groups: this.props.attrs.groups ? this.props.attrs.groups : null,
                }
            );
        }

        if (this.props.className.includes("oe_stat_button")) {

            this.env.bus.trigger("SMART_BUTTON_DETAILS", {
                type: "SmartButtonProperties",
                properties: buttonProperties,
                new_button: false,
            });
        } else {
            this.env.bus.trigger("BUTTON_DETAILS", {
                type: "ButtonProperties",
                create : false,
                newButton: false,
                ...buttonProperties,

            });
        }
    },
});
ViewButton.props = [...ViewButton.props, "cyXpath?", "striped?"];