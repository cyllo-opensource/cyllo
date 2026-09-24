/** @odoo-module **/
import {
    Component,
    useState,
    onWillStart,
    onWillUpdateProps,
    onWillUnmount
} from "@odoo/owl";
import {
    CustomSelection
} from "@cyllo_studio/js/navbar/custom_selection/custom_selection";
import {
    CylloStudioDropdown
} from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import {
    IconPicker
} from "@cyllo_studio/js/view_editor/dropdown/icon_picker/icon_picker";
import {
    useService,
    useOwnedDialogs
} from "@web/core/utils/hooks";

import {
    MultiSelectDropDown
} from "@cyllo_studio/js/view_editor/dropdown/multi_select_dropdown/multi_select_dropdown";
import {
    _t
} from "@web/core/l10n/translation";
import {
    CylloExpressionEditorDialog
} from "@cyllo_studio/js/view_editor/components/expression_editor_dialog/expression_editor_dialog";
import { evaluateExpr } from "@web/core/py_js/py";



const ICONCLASS = [
    "fa-500px",
    "fa-address-book",
    "fa-address-book-o",
    "fa-address-card",
    "fa-address-card-o",
    "fa-adjust",
    "fa-adn",
    "fa-align-center",
    "fa-align-justify",
    "fa-align-left",
    "fa-align-right",
    "fa-amazon",
    "fa-ambulance",
    "fa-american-sign-language-interpreting",
    "fa-anchor",
    "fa-android",
    "fa-angellist",
    "fa-angle-double-down",
    "fa-angle-double-left",
    "fa-angle-double-right",
    "fa-angle-double-up",
    "fa-angle-down",
    "fa-angle-left",
    "fa-angle-right",
    "fa-angle-up",
    "fa-apple",
    "fa-archive",
    "fa-area-chart",
    "fa-arrow-circle-down",
    "fa-arrow-circle-left",
    "fa-arrow-circle-o-down",
    "fa-arrow-circle-o-left",
    "fa-arrow-circle-o-right",
    "fa-arrow-circle-o-up",
    "fa-arrow-circle-right",
    "fa-arrow-circle-up",
    "fa-arrow-down",
    "fa-arrow-left",
    "fa-arrow-right",
    "fa-arrow-up",
    "fa-arrows",
    "fa-arrows-alt",
    "fa-arrows-h",
    "fa-arrows-v",
    "fa-asl-interpreting",
    "fa-assistive-listening-systems",
    "fa-asterisk",
    "fa-at",
    "fa-audio-description",
    "fa-automobile",
    "fa-backward",
    "fa-balance-scale",
    "fa-ban",
    "fa-bandcamp",
    "fa-bank",
    "fa-bar-chart",
    "fa-bar-chart-o",
    "fa-barcode",
    "fa-bars",
    "fa-bath",
    "fa-bathtub",
    "fa-battery",
    "fa-battery-0",
    "fa-battery-1",
    "fa-battery-2",
    "fa-battery-3",
    "fa-battery-4",
    "fa-battery-empty",
    "fa-battery-full",
    "fa-battery-half",
    "fa-battery-quarter",
    "fa-battery-three-quarters",
    "fa-bed",
    "fa-beer",
    "fa-behance",
    "fa-behance-square",
    "fa-bell",
    "fa-bell-o",
    "fa-bell-slash",
    "fa-bell-slash-o",
    "fa-bicycle",
    "fa-binoculars",
    "fa-birthday-cake",
    "fa-bitbucket",
    "fa-bitbucket-square",
    "fa-bitcoin",
    "fa-black-tie",
    "fa-blind",
    "fa-bluetooth",
    "fa-bluetooth-b",
    "fa-bold",
    "fa-bolt",
    "fa-bomb",
    "fa-book",
    "fa-bookmark",
    "fa-bookmark-o",
    "fa-braille",
    "fa-briefcase",
    "fa-btc",
    "fa-bug",
    "fa-building",
    "fa-building-o",
    "fa-bullhorn",
    "fa-bullseye",
    "fa-bus",
    "fa-buysellads",
    "fa-cab",
    "fa-calculator",
    "fa-calendar",
    "fa-calendar-check-o",
    "fa-calendar-minus-o",
    "fa-calendar-o",
    "fa-calendar-plus-o",
    "fa-calendar-times-o",
    "fa-camera",
    "fa-camera-retro",
    "fa-car",
    "fa-caret-down",
    "fa-caret-left",
    "fa-caret-right",
    "fa-caret-square-o-down",
    "fa-caret-square-o-left",
    "fa-caret-square-o-right",
    "fa-caret-square-o-up",
    "fa-caret-up",
    "fa-cart-arrow-down",
    "fa-cart-plus",
    "fa-cc",
    "fa-cc-amex",
    "fa-cc-diners-club",
    "fa-cc-discover",
    "fa-cc-jcb",
    "fa-cc-mastercard",
    "fa-cc-paypal",
    "fa-cc-stripe",
    "fa-cc-visa",
    "fa-certificate",
    "fa-chain",
    "fa-chain-broken",
    "fa-check",
    "fa-check-circle",
    "fa-check-circle-o",
    "fa-check-square",
    "fa-check-square-o",
    "fa-chevron-circle-down",
    "fa-chevron-circle-left",
    "fa-chevron-circle-right",
    "fa-chevron-circle-up",
    "fa-chevron-down",
    "fa-chevron-left",
    "fa-chevron-right",
    "fa-chevron-up",
    "fa-child",
    "fa-chrome",
    "fa-circle",
    "fa-circle-o",
    "fa-circle-o-notch",
    "fa-circle-thin",
    "fa-clipboard",
    "fa-clock-o",
    "fa-clone",
    "fa-close",
    "fa-cloud",
    "fa-cloud-download",
    "fa-cloud-upload",
    "fa-cny",
    "fa-code",
    "fa-code-fork",
    "fa-codepen",
    "fa-codiepie",
    "fa-coffee",
    "fa-cog",
    "fa-cogs",
    "fa-columns",
    "fa-comment",
    "fa-comment-o",
    "fa-commenting",
    "fa-commenting-o",
    "fa-comments",
    "fa-comments-o",
    "fa-compass",
    "fa-compress",
    "fa-connectdevelop",
    "fa-contao",
    "fa-copy",
    "fa-copyright",
    "fa-creative-commons",
    "fa-credit-card",
    "fa-credit-card-alt",
    "fa-crop",
    "fa-crosshairs",
    "fa-css3",
    "fa-cube",
    "fa-cubes",
    "fa-cut",
    "fa-cutlery",
    "fa-dashboard",
    "fa-dashcube",
    "fa-database",
    "fa-deaf",
    "fa-deafness",
    "fa-dedent",
    "fa-delicious",
    "fa-desktop",
    "fa-deviantart",
    "fa-diamond",
    "fa-digg",
    "fa-dollar",
    "fa-dot-circle-o",
    "fa-download",
    "fa-dribbble",
    "fa-drivers-license",
    "fa-drivers-license-o",
    "fa-dropbox",
    "fa-drupal",
    "fa-edge",
    "fa-edit",
    "fa-eercast",
    "fa-eject",
    "fa-ellipsis-h",
    "fa-ellipsis-v",
    "fa-empire",
    "fa-envelope",
    "fa-envelope-o",
    "fa-envelope-open",
    "fa-envelope-open-o",
    "fa-envelope-square",
    "fa-envira",
    "fa-eraser",
    "fa-etsy",
    "fa-eur",
    "fa-euro",
    "fa-exchange",
    "fa-exclamation",
    "fa-exclamation-circle",
    "fa-exclamation-triangle",
    "fa-expand",
    "fa-expeditedssl",
    "fa-external-link",
    "fa-external-link-square",
    "fa-eye",
    "fa-eye-slash",
    "fa-eyedropper",
    "fa-fa",
    "fa-facebook",
    "fa-facebook-f",
    "fa-facebook-official",
    "fa-facebook-square",
    "fa-fast-backward",
    "fa-fast-forward",
    "fa-fax",
    "fa-feed",
    "fa-female",
    "fa-fighter-jet",
    "fa-file",
    "fa-file-archive-o",
    "fa-file-audio-o",
    "fa-file-code-o",
    "fa-file-excel-o",
    "fa-file-image-o",
    "fa-file-movie-o",
    "fa-file-o",
    "fa-file-pdf-o",
    "fa-file-photo-o",
    "fa-file-picture-o",
    "fa-file-powerpoint-o",
    "fa-file-sound-o",
    "fa-file-text",
    "fa-file-text-o",
    "fa-file-video-o",
    "fa-file-word-o",
    "fa-file-zip-o",
    "fa-files-o",
    "fa-film",
    "fa-filter",
    "fa-fire",
    "fa-fire-extinguisher",
    "fa-firefox",
    "fa-first-order",
    "fa-flag",
    "fa-flag-checkered",
    "fa-flag-o",
    "fa-flash",
    "fa-flask",
    "fa-flickr",
    "fa-floppy-o",
    "fa-folder",
    "fa-folder-o",
    "fa-folder-open",
    "fa-folder-open-o",
    "fa-font",
    "fa-font-awesome",
    "fa-fonticons",
    "fa-fort-awesome",
    "fa-forumbee",
    "fa-forward",
    "fa-foursquare",
    "fa-free-code-camp",
    "fa-frown-o",
    "fa-futbol-o",
    "fa-gamepad",
    "fa-gavel",
    "fa-gbp",
    "fa-ge",
    "fa-gear",
    "fa-gears",
    "fa-genderless",
    "fa-get-pocket",
    "fa-gg",
    "fa-gg-circle",
    "fa-gift",
    "fa-git",
    "fa-git-square",
    "fa-github",
    "fa-github-alt",
    "fa-github-square",
    "fa-gitlab",
    "fa-gittip",
    "fa-glass",
    "fa-glide",
    "fa-glide-g",
    "fa-globe",
    "fa-google",
    "fa-google-plus",
    "fa-google-plus-circle",
    "fa-google-plus-official",
    "fa-google-plus-square",
    "fa-google-wallet",
    "fa-graduation-cap",
    "fa-gratipay",
    "fa-grav",
    "fa-group",
    "fa-h-square",
    "fa-hacker-news",
    "fa-hand-grab-o",
    "fa-hand-lizard-o",
    "fa-hand-o",
];

const CLASSNAMES = ["primary", "secondary", "info", "warning", "danger"];

export class ButtonProperties extends Component {
    static template = "cyllo_studio.ButtonProperties";
    async setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.action = useService("action");
        this.addDialog = useOwnedDialogs();
        this.notification = useService("effect");
        // actionOptions is populated in onWillStart; [] guards against a crash
        // if a render fires before the fetch resolves.
        this.actionOptions = [];
        this.state = useState({
            viewDetails: this.props.viewDetails || "",
            iconToggle: false,
            style: "button",
            validation: true,
            newButton: this.props.newButton || false,
            elementInfo: this.props.elementInfo || {},
            allGroups: {},
        });
        this.buttonProperties = useState({
            string: this.props.string || "",
            type: this.props.function_type || "object",
            class: this.props.class_name || "",
            name: this.props.function_type !== "action"
                ? this.props.function_name
                : parseInt(this.props.function_name, 10),
            groupIds: [], //this.props.groupIds ||
            invisible: this.props.invisible || "false",
            icon: this.props.icon || "",
            newButton: this.props.newButton || false,
            hotKey: false,
            sibling: this.props.sibling || false,
            field_info: this.props.field_info || {},
            item_type: this.props.item_type || "",
            spanxpath: this.props.spanxpath || "",
            path: this.props.path,
        });

        this._autoSaving = false;
        this._autoSavePending = false;

        onWillUpdateProps(async (nextProps) => {
            this.state.elementInfo = nextProps.elementInfo;
            this.state.newButton = this.props.newButton || false,
                this.buttonProperties.string = nextProps.string
            this.buttonProperties.type = nextProps.function_type || "object"
            this.buttonProperties.class = nextProps.class_name || "btn-secondary"

            this.buttonProperties.icon = nextProps.icon
            this.buttonProperties.invisible = nextProps.invisible || "false"
            if (nextProps.function_type == 'action') {
                this.buttonProperties.name = parseInt(nextProps.function_name, 10);
            }
            else {
                this.buttonProperties.name = nextProps.function_name
            }
            if (nextProps.class_name?.startsWith('btn-')) {
                this.state.style = 'button'
            }
            else if (nextProps.class_name?.startsWith('text-')) {
                this.state.style = 'link'
            }
            this.buttonProperties.groupIds = (nextProps.groupIds && nextProps.groupIds.length > 0)
                ? nextProps.groupIds : [];
        });

        onWillStart(async () => {
            if (this.state.viewDetails.viewType === "form") {
                sessionStorage.removeItem("CyStudioRelationModel");
            }
            if (this.props.groupIds && this.props.groupIds.length > 0) {
                this.buttonProperties.groupIds = this.props.groupIds
            } else {
                this.buttonProperties.groupIds = [];
            }
            if (this.buttonProperties.class?.startsWith('btn-')) {
                this.state.style = 'button'
            }
            else if (this.buttonProperties.class?.startsWith('text-')) {
                this.state.style = 'link'
            }
            this.modelName = await this.getCorrectModel();
            this.functions = await this.rpc("cyllo_studio/find/functions", {
                model_name: this.modelName,
            });
            // Load ir.actions.actions once at mount — actions are model-independent
            // so no need to re-fetch on prop updates.
            this.actionOptions = await this._loadActionOptions();
            await this.loadAllGroups();
        });
    }

    async loadAllGroups() {
        const groups = await this.orm.searchRead("res.groups", [], ["id", "full_name"], { limit: 0 });
        this.state.allGroups = Object.fromEntries(groups.map(g => [String(g.id), g.full_name]));
    }

    get groupsAllValues() {
        return this.state.allGroups || {};
    }

    get groupsSelectedValues() {
        return (this.buttonProperties.groupIds || []).map(id => String(id));
    }

    updateGroupIds(selectedStrings) {
        this.buttonProperties.groupIds = selectedStrings.map(s => parseInt(s, 10));
        this.autoSave();
    }

    /**
     * Fetch all available actions from ir.actions.actions.
     * Returns a CylloStudioDropdown-compatible options array: [{value: id, label: name}, ...].
     * Returns [] on any error so a failed fetch can't crash the dropdown.
     * ir.actions.actions is model-independent — no getCorrectModel() filtering.
     */
async _loadActionOptions() {
    try {
        const records = await this.orm.searchRead(
            "ir.actions.actions",
            [],
            ["id", "name", "type"],
        );

        // Scope resolution only applies to act_window — that's where
        // this collision lives, and res_model is useless here since
        // it's identical (mail.activity.type) across all of them.
        // The real distinguisher is which app's context/domain scopes
        // the window to.
        const actWindowIds = records.filter(r => r.type === "ir.actions.act_window").map(r => r.id);
        const scopeById = {};
        if (actWindowIds.length) {
            const actWindowRecords = await this.orm.searchRead(
                "ir.actions.act_window",
                [["id", "in", actWindowIds]],
                ["id", "context", "domain"],
            );
            for (const awr of actWindowRecords) {
                let scope = null;
                try {
                    const ctx = evaluateExpr(awr.context || "{}");
                    if (ctx.default_res_model) scope = ctx.default_res_model;
                } catch { /* dynamic/malformed context — leave unscoped */ }
                if (!scope && awr.domain) {
                    try {
                        const dom = evaluateExpr(awr.domain);
                        const clause = dom.find(
                            (d) => Array.isArray(d) && d[0] === "res_model" && d[1] === "=" && d[2]
                        );
                        if (clause) scope = clause[2];
                    } catch { /* dynamic/malformed domain — leave unscoped */ }
                }
                scopeById[awr.id] = scope; // stays null for the generic/unscoped entry (id 110)
            }
        }

        const seen = new Map();
        return records.map((r) => {
            const scope = scopeById[r.id];
            let label = scope ? `${r.name} ( ${r.type} · ${scope} )` : `${r.name} ( ${r.type} )`;

            const n = seen.get(label) ?? 0;
            seen.set(label, n + 1);
            if (n > 0) label = `${label} #${r.id}`;

            return { value: r.id, label };
        });
    } catch (e) {
        console.error("[ButtonProperties] Failed to load action options:", e);
        return [];
    }
}
    /**
     * Handle action selection from the CylloStudioDropdown.
     * Mirrors handleButtonFunctionChange in naming/structure.
     * @param {number} value - The selected ir.actions.actions id
     */
    handleActionChange(value) {
        this.buttonProperties.name = parseInt(value, 10);
        this.autoSave();
    }
    get onStyleChange() {
        return [{
            value: "button",
            label: "Button"
        },
        {
            value: "link",
            label: "Link"
        },
        ];
    }
    get IconClass() {
        return ICONCLASS;
    }
    setIcon(icons) {
        this.buttonProperties.icon = icons;
        this.state.iconToggle = false;
    }

    get iconOptions() {
        return [
            { value: "", label: "None" },
            ...ICONCLASS.map(cls => ({
                value: cls,
                label: cls.replace(/^fa-/, "").replace(/-/g, " "),
            })),
        ];
    }
    handleClassChange(val) {
        this.buttonProperties.class = val;
        this.autoSave();
    }
    handleOnStyleChange(value) {
        this.buttonProperties.class = this.buttonProperties.class.split(' ').map((className) => {
            if (value === 'button' && className !== 'btn-link') {
                if (className.startsWith('text-') && CLASSNAMES.includes(className.split('-')[1])) {
                    return 'btn-' + className.split('-')[1]
                }
                return className
            } else if (value === 'link') {
                if (className.startsWith('btn-') && CLASSNAMES.includes(className.split('-')[1])) {
                    return 'text-' + className.split('-')[1]
                }
            }
        }).join(' ')
        this.state.style = value
        this.autoSave();
    }
    handleOnTypeChange(value) {
        this.buttonProperties.type = value;
        if (value === 'workflow') {
            const label = this.buttonProperties.string || 'button';
            this.buttonProperties.name = `studio_wf_${label.toLowerCase().replace(/\s+/g, '_')}`;
        } else {
            this.buttonProperties.name = false;
        }
        this.autoSave();
    }
    get getActionName() {
        const id = parseInt(this.buttonProperties.name);
        return isNaN(id) ? false : id;
    }
    get onTypeChange() {
        return [{
            value: "object",
            label: "Object"
        },
        {
            value: "action",
            label: "Action"
        },
        {
            value: "workflow",
            label: "Workflow"
        },

        ];
    }

    async getCorrectModel() {
        const viewType = this.state.viewDetails?.viewType || "";
        const currentModel = this.props.model || this.state.viewDetails.model;

        // 1. If we have field_info with a relation, and we are on a One2Many field, use the relation
        if (this.buttonProperties.field_info?.relation && this.props.path) {
            return this.buttonProperties.field_info.relation;
        }

        // 2. If sessionStorage has CyStudioRelationModel (set when navigating One2Many), and we are inside a One2Many click
        const relationModel = sessionStorage.getItem('CyStudioRelationModel');
        if (relationModel && relationModel !== 'null' && relationModel !== 'undefined') {
            return relationModel;
        }

        // 3. If PrevForm has RelationModel (set when clicking One2Many)
        const prevFormData = sessionStorage.getItem('PrevForm');
        if (prevFormData) {
            try {
                const parsedData = JSON.parse(prevFormData);
                if (parsedData.RelationModel) {
                    return parsedData.RelationModel;
                }
            } catch (e) {
                console.error("Error parsing PrevForm:", e);
            }
        }
        return currentModel;
    }

    async RemoveButton() {
        this.state.isEditingButton = false;
        if (!this.state.newButton && this.props.path) {
            const response = await this.rpc("cyllo_studio/delete/button", {
                method: 'delete_button',
                kwargs: {
                    path: this.props.path,
                    model: this.modelName, // USE CORRECT MODEL
                    view_id: this.state.viewDetails.viewId,
                    viewType: this.state.viewDetails.viewType,
                }
            })

            if (response) {
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr)
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            }

            this.env.bus.trigger('CLEAR-MENU', { fromClose: true });
        } else {
            this.env.bus.trigger('REMOVE_BUTTON_PROPERTIES');
            this.env.bus.trigger('CLEAR-MENU', { fromClose: true });
        }
        this.action.doAction('studio_reload')
    }
    autoSave() {
        if (this._autoSaving) { this._autoSavePending = true; return; }
        this._autoSaving = true;
        this.addButton().finally(() => {
            this._autoSaving = false;
            if (this._autoSavePending) { this._autoSavePending = false; this.autoSave(); }
        });
    }

    handleButtonFunctionChange(value) {
        const functionInfo = document.querySelector(".functionInfo");
        if (functionInfo) {
            functionInfo.classList.remove("d-none");
        }
        this.buttonProperties.name = value;
        this.autoSave();
    }

    ButtonFunctionChange(array) {
        const result = array.map((item) => ({
            value: item,
            label: item
        }));
        return result;
    }

    onDomainRadioClick({
        target
    }) {
        this.buttonProperties[target.name] = ["false", "undefined"].includes(this.buttonProperties[target.name]) ? "true" : "false";
        this.autoSave();
    }

    onDomainClick({ target }) {
        this.state.validation = false
        let button = target.closest(".cy-basedOn");
        let attribute = button.getAttribute("data-attribute");
        this.addDialog(CylloExpressionEditorDialog, {
            resModel: this.state.viewDetails.model,
            fields: this.state.viewDetails.allFields,
            expression: this.buttonProperties[attribute] ? this.buttonProperties[attribute] : 'true',
            setValidation: () => {
                this.state.validation = true
            },
            onConfirm: (expression) => {
                this.buttonProperties[attribute] = expression;
                this.autoSave();
            }
        });
    }

    async addButton() {
        this.state.isEditingButton = false;

        const validations = [{
            field: 'name',
            message: "Please provide a function name for the button.",
        },
        {
            field: 'string',
            message: "Please provide a label for the button.",
        },
        {
            field: 'type',
            message: "Please provide a valid button type.",
        },
        ];
        for (const { field, message } of validations) {
            if (field === 'name' && this.buttonProperties.type === 'workflow') {
                continue;
            }
            if (!this.buttonProperties[field]) {
                this.warningCount += 1;
                return this.notification.add({
                    title: _t("Validation Error"),
                    message: "Unable to save the button.",
                    description: message,
                    type: "notification_panel",
                    notificationType: "warning",
                });
            }
        }
        let button_properties = {
            string: this.buttonProperties.string,
            type: this.buttonProperties.type,
            name: this.buttonProperties.name,
            class: this.buttonProperties.class,
            invisible: this.buttonProperties.invisible,
            icon: this.buttonProperties.icon,
            hotKey: this.buttonProperties.hotKey,
        };
        if (!this.buttonProperties.path) {
            let cyxpath = this.el?.getAttribute("cyxpath");
            if (!cyxpath) {
                const parentButton = document.querySelector("button[cyxpath]");
                if (parentButton) {
                    cyxpath = parentButton.getAttribute("cyxpath");
                }
            }

            if (cyxpath) {
                this.buttonProperties.path = cyxpath;
            }
        }
        try {
            if (this.buttonProperties.newButton) {
                const x2many = sessionStorage.getItem("CyX2ManyPath");
                const result = await this.rpc("/cyllo_studio/add/button_item", {
                    kwargs: {
                        newHeader: this.props.newHeader,
                        path: this.props.path || this.props.properties.elementInfo?.path,
                        position: this.props.position || this.props.properties?.elementInfo?.position,
                        groupIds: this.buttonProperties.groupIds,
                        model: await this.getCorrectModel(),
                        viewId: this.state.viewDetails.viewId,
                        viewType: this.state.viewDetails.viewType,
                        item_type: this.buttonProperties.item_type || "",
                        sibling: this.buttonProperties.sibling || false,
                        field_info: this.buttonProperties.field_info || {},
                        spanxpath: this.buttonProperties.spanxpath || "",
                    },
                    button_properties,
                });
                // If the result is successful, handle undo/redo storage
                if (result) {
                    let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                    let cleanedStr = result.replace(/\s+/g, ' ').trim();
                    storedArray.push(cleanedStr);
                    sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                    sessionStorage.setItem('ReDO', JSON.stringify([]));
                }
            } else {
                const result = await this.rpc("/cyllo_studio/update/button_item", {
                    kwargs: {
                        path: this.props?.path || this.props.properties?.elementInfo.path || this.buttonProperties?.path,
                        groupIds: this.buttonProperties.groupIds,
                        model: this.state.viewDetails.model,
                        viewId: this.state.viewDetails.viewId,
                        viewType: this.state.viewDetails.viewType,
                        spanxpath: this.buttonProperties.spanxpath || "",
                    },
                    button_properties,
                });
                // If the result is successful, handle undo/redo storage
                if (result) {
                    let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                    let cleanedStr = result.replace(/\s+/g, ' ').trim();
                    storedArray.push(cleanedStr);
                    sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                    sessionStorage.setItem('ReDO', JSON.stringify([]));
                }
            }

        } finally {
            this.action.doAction("studio_reload");
        }
    }

    async RemoveButton() {
        this.state.isEditingButton = false;
        if (!this.state.newButton && this.props.path) {
            const response = await this.rpc("cyllo_studio/delete/button", {
                method: 'delete_button',
                kwargs: {
                    path: this.props.path,
                    model: this.state.viewDetails.model,
                    view_id: this.state.viewDetails.viewId,
                    viewType: this.state.viewDetails.viewType,
                }
            })
            if (response) {
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr)
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            }
            this.env.bus.trigger('CLEAR-MENU', {
                fromClose: true
            });
        } else {
            this.env.bus.trigger('REMOVE_BUTTON_PROPERTIES');
            this.env.bus.trigger('CLEAR-MENU', {
                fromClose: true
            });
        }
        this.action.doAction('studio_reload')
    }
    handleLabelChange({ target }) {
        const value = target.value;
        this.buttonProperties.string = value;
        this.state.string = value;
        if (this.buttonProperties.type === 'workflow') {
            this.buttonProperties.name = `studio_wf_${value.toLowerCase().replace(/\s+/g, '_')}`;
        }

        const newButtons = document.querySelectorAll('#newButtonLabel');
        newButtons.forEach(btn => {
            if (!btn.closest('.cy-kanban-component-container') && this.state.viewDetails.viewType !== 'tree' && this.state.viewDetails.viewType !== 'list') {
                btn.textContent = value;
            }
        });
    }
}
ButtonProperties.components = {
    CustomSelection,
    CylloStudioDropdown,
    MultiSelectDropDown,
    IconPicker,
};