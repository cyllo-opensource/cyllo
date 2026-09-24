/** @odoo-module **/
import {
    Component,
    useState,
    useRef,
    onWillStart,
    onWillUpdateProps
} from "@odoo/owl";
import {
    useService,
    useOwnedDialogs
} from "@web/core/utils/hooks";
import {
    MultiSelectDropDown
} from "@cyllo_studio/js/view_editor/dropdown/multi_select_dropdown/multi_select_dropdown";
import {
    CylloStudioDropdown
} from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import {
    IconPicker
} from "@cyllo_studio/js/view_editor/dropdown/icon_picker/icon_picker";
import {
    ExpressionEditorDialog
} from "@web/core/expression_editor_dialog/expression_editor_dialog";
import {
    ModelFieldSelector
} from "@web/core/model_field_selector/model_field_selector";
import {
    DomainSelectorDialog
} from "@web/core/domain_selector_dialog/domain_selector_dialog";
const ICONCLASS = ["fa-500px", "fa-address-book", "fa-address-book-o", "fa-address-card", "fa-address-card-o", "fa-adjust", "fa-adn", "fa-align-center", "fa-align-justify", "fa-align-left", "fa-align-right", "fa-amazon", "fa-ambulance", "fa-american-sign-language-interpreting", "fa-anchor", "fa-android", "fa-angellist", "fa-angle-double-down", "fa-angle-double-left", "fa-angle-double-right", "fa-angle-double-up", "fa-angle-down", "fa-angle-left", "fa-angle-right", "fa-angle-up", "fa-apple", "fa-archive", "fa-area-chart", "fa-arrow-circle-down", "fa-arrow-circle-left", "fa-arrow-circle-o-down", "fa-arrow-circle-o-left", "fa-arrow-circle-o-right", "fa-arrow-circle-o-up", "fa-arrow-circle-right", "fa-arrow-circle-up", "fa-arrow-down", "fa-arrow-left", "fa-arrow-right", "fa-arrow-up", "fa-arrows", "fa-arrows-alt", "fa-arrows-h", "fa-arrows-v", "fa-asl-interpreting", "fa-assistive-listening-systems", "fa-asterisk", "fa-at", "fa-audio-description", "fa-automobile", "fa-backward", "fa-balance-scale", "fa-ban", "fa-bandcamp", "fa-bank", "fa-bar-chart", "fa-bar-chart-o", "fa-barcode", "fa-bars", "fa-bath", "fa-bathtub", "fa-battery", "fa-battery-0", "fa-battery-1", "fa-battery-2", "fa-battery-3", "fa-battery-4", "fa-battery-empty", "fa-battery-full", "fa-battery-half", "fa-battery-quarter", "fa-battery-three-quarters", "fa-bed", "fa-beer", "fa-behance", "fa-behance-square", "fa-bell", "fa-bell-o", "fa-bell-slash", "fa-bell-slash-o", "fa-bicycle", "fa-binoculars", "fa-birthday-cake", "fa-bitbucket", "fa-bitbucket-square", "fa-bitcoin", "fa-black-tie", "fa-blind", "fa-bluetooth", "fa-bluetooth-b", "fa-bold", "fa-bolt", "fa-bomb", "fa-book", "fa-bookmark", "fa-bookmark-o", "fa-braille", "fa-briefcase", "fa-btc", "fa-bug", "fa-building", "fa-building-o", "fa-bullhorn", "fa-bullseye", "fa-bus", "fa-buysellads", "fa-cab", "fa-calculator", "fa-calendar", "fa-calendar-check-o", "fa-calendar-minus-o", "fa-calendar-o", "fa-calendar-plus-o", "fa-calendar-times-o", "fa-camera", "fa-camera-retro", "fa-car", "fa-caret-down", "fa-caret-left", "fa-caret-right", "fa-caret-square-o-down", "fa-caret-square-o-left", "fa-caret-square-o-right", "fa-caret-square-o-up", "fa-caret-up", "fa-cart-arrow-down", "fa-cart-plus", "fa-cc", "fa-cc-amex", "fa-cc-diners-club", "fa-cc-discover", "fa-cc-jcb", "fa-cc-mastercard", "fa-cc-paypal", "fa-cc-stripe", "fa-cc-visa", "fa-certificate", "fa-chain", "fa-chain-broken", "fa-check", "fa-check-circle", "fa-check-circle-o", "fa-check-square", "fa-check-square-o", "fa-chevron-circle-down", "fa-chevron-circle-left", "fa-chevron-circle-right", "fa-chevron-circle-up", "fa-chevron-down", "fa-chevron-left", "fa-chevron-right", "fa-chevron-up", "fa-child", "fa-chrome", "fa-circle", "fa-circle-o", "fa-circle-o-notch", "fa-circle-thin", "fa-clipboard", "fa-clock-o", "fa-clone", "fa-close", "fa-cloud", "fa-cloud-download", "fa-cloud-upload", "fa-cny", "fa-code", "fa-code-fork", "fa-codepen", "fa-codiepie", "fa-coffee", "fa-cog", "fa-cogs", "fa-columns", "fa-comment", "fa-comment-o", "fa-commenting", "fa-commenting-o", "fa-comments", "fa-comments-o", "fa-compass", "fa-compress", "fa-connectdevelop", "fa-contao", "fa-copy", "fa-copyright", "fa-creative-commons", "fa-credit-card", "fa-credit-card-alt", "fa-crop", "fa-crosshairs", "fa-css3", "fa-cube", "fa-cubes", "fa-cut", "fa-cutlery", "fa-dashboard", "fa-dashcube", "fa-database", "fa-deaf", "fa-deafness", "fa-dedent", "fa-delicious", "fa-desktop", "fa-deviantart", "fa-diamond", "fa-digg", "fa-dollar", "fa-dot-circle-o", "fa-download", "fa-dribbble", "fa-drivers-license", "fa-drivers-license-o", "fa-dropbox", "fa-drupal", "fa-edge", "fa-edit", "fa-eercast", "fa-eject", "fa-ellipsis-h", "fa-ellipsis-v", "fa-empire", "fa-envelope", "fa-envelope-o", "fa-envelope-open", "fa-envelope-open-o", "fa-envelope-square", "fa-envira", "fa-eraser", "fa-etsy", "fa-eur", "fa-euro", "fa-exchange", "fa-exclamation", "fa-exclamation-circle", "fa-exclamation-triangle", "fa-expand", "fa-expeditedssl", "fa-external-link", "fa-external-link-square", "fa-eye", "fa-eye-slash", "fa-eyedropper", "fa-fa", "fa-facebook", "fa-facebook-f", "fa-facebook-official", "fa-facebook-square", "fa-fast-backward", "fa-fast-forward", "fa-fax", "fa-feed", "fa-female", "fa-fighter-jet", "fa-file", "fa-file-archive-o", "fa-file-audio-o", "fa-file-code-o", "fa-file-excel-o", "fa-file-image-o", "fa-file-movie-o", "fa-file-o", "fa-file-pdf-o", "fa-file-photo-o", "fa-file-picture-o", "fa-file-powerpoint-o", "fa-file-sound-o", "fa-file-text", "fa-file-text-o", "fa-file-video-o", "fa-file-word-o", "fa-file-zip-o", "fa-files-o", "fa-film", "fa-filter", "fa-fire", "fa-fire-extinguisher", "fa-firefox", "fa-first-order", "fa-flag", "fa-flag-checkered", "fa-flag-o", "fa-flash", "fa-flask", "fa-flickr", "fa-floppy-o", "fa-folder", "fa-folder-o", "fa-folder-open", "fa-folder-open-o", "fa-font", "fa-font-awesome", "fa-fonticons", "fa-fort-awesome", "fa-forumbee", "fa-forward", "fa-foursquare", "fa-free-code-camp", "fa-frown-o", "fa-futbol-o", "fa-gamepad", "fa-gavel", "fa-gbp", "fa-ge", "fa-gear", "fa-gears", "fa-genderless", "fa-get-pocket", "fa-gg", "fa-gg-circle", "fa-gift", "fa-git", "fa-git-square", "fa-github", "fa-github-alt", "fa-github-square", "fa-gitlab", "fa-gittip", "fa-glass", "fa-glide", "fa-glide-g", "fa-globe", "fa-google", "fa-google-plus", "fa-google-plus-circle", "fa-google-plus-official", "fa-google-plus-square", "fa-google-wallet", "fa-graduation-cap", "fa-gratipay", "fa-grav", "fa-group", "fa-h-square", "fa-hacker-news", "fa-hand-grab-o", "fa-hand-lizard-o", "fa-hand-o"]

export class SmartButtonProperties extends Component {
    setup() {
        this.rpc = useService('rpc');
        this.action = useService('action');
        this.dialogService = useService("dialog");
        this.addDialog = useOwnedDialogs();
        this.iconRef = useRef('IconRef')
        this._autoSaving = false;
        this._autoSavePending = false;
        this.state = useState({
            string: this.props.string || "",
            label: this.props.properties?.string || this.props.properties?.nullString || '',
            icon: this.props.properties?.icon || 'fa-file-text-o',
            path: this.props.path,
            related_model: '',
            related_field: '',
            domain: '[]',
            group_ids: this.props.properties.groupIds || [],
            fieldDetails: '',
            invisible: this.props.properties.invisible || 'false',
            isNewButton: this.props.properties.new_button || false,
            cyPath: this.props.properties.path,
            stringPath: this.props.properties.stringPath || "",
            StatusLabelPath: this.props.properties.StatusLabelPath == 'false' ? false : this.props.properties.StatusLabelPath,
            iconToggle : false,
            allGroups: {},
        })
       onWillStart(async () =>{
            if(this.props.properties.string === ''){
                const smart_button_class = this.props.properties.class
                const btnClass = smart_button_class.split(" ").find(className => className.includes("btn-"));
            }
            this.state.oldicon = this.state.icon
            await this.loadAllGroups();
        });

        onWillUpdateProps( async(nextProps)=> {
            this.state.icon = nextProps.properties?.icon || 'fa-file-text-o'
            this.state.readOnly = ''
            this.state.invisible = nextProps.properties?.invisible || 'false'
            this.state.label = nextProps.properties?.string || nextProps.properties?.nullString ||''
            this.state.isNewButton = nextProps.properties.new_button || false
            this.state.viewId = nextProps.viewId
            this.state.group_ids = nextProps.properties.groupIds || []
            this.cyPath = nextProps.properties.path
            this.stringPath = nextProps.properties.stringPath || ""
            if(nextProps.properties?.new_button){
                this.state.cyPath = ''
                this.state.stringPath = ''
                this.state.group_ids = []
            } else {
            this.state.cyPath = nextProps.properties?.path
            this.state.stringPath = nextProps.properties?.stringPath
            }
        })

    }
    async loadAllGroups() {
        const groups = await this.rpc("/web/dataset/call_kw/res.groups/search_read", {
            model: "res.groups",
            method: "search_read",
            args: [[], ["id", "full_name"]],
            kwargs: { limit: 0 },
        });
        this.state.allGroups = Object.fromEntries(groups.map(g => [String(g.id), g.full_name]));
    }

    get groupsAllValues() {
        return this.state.allGroups || {};
    }

    get groupsSelectedValues() {
        return (this.state.group_ids || []).map(id => String(id));
    }

    autoSave() {
        if (this._autoSaving) { this._autoSavePending = true; return; }
        this._autoSaving = true;
        const save = this.state.isNewButton ? this.addSmartButton() : this.updateSmartButton();
        save.finally(() => {
            this._autoSaving = false;
            if (this._autoSavePending) { this._autoSavePending = false; this.autoSave(); }
        });
    }

    updateGroupIds(selectedStrings) {
        this.state.group_ids = selectedStrings.map(s => parseInt(s, 10));
        this.autoSave();
    }

    async findGroupIds(groups) {
        if (groups) {
            this.state.group_ids = await this.rpc("cyllo_studio/find/groups", {
                groups: groups
            })
        } else {
            this.state.group_ids = []
        }
    }

    iconToggle() {
        this.iconRef.el?.classList.toggle("d-none")
    }
    onCloseIcon() {
        this.iconRef.el.classList.toggle("d-none")
    }
    selectIcon(icon) {
        this.state.icon = icon;
        this.state.iconToggle = false;
    }
    get IconClass() {
        return ICONCLASS
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

    fieldDomain() {
        this.dialogService.add(DomainSelectorDialog, {
            resModel: this.state.fieldDetails.fieldDef.relation,
            domain: this.state.domain,
            onConfirm: (domain) => this.state.domain = domain,
            title: ("Domain"),
        });
    }
    updateFieldType(path, field) {
        this.state.fieldDetails = field;
        this.state.related_field = path;
        this.state.domain = '[]';
        this.autoSave();
    }
    handleInvisibleChange(event) {
        this.state.invisible = event.target.checked ? "true" : "false";
        this.autoSave();
    }

    async attrDomain(ev) {
        const filteredObj = Object.keys(this.props.allFields).filter(key => key in this.props.activeFields)
         .reduce((acc, key) => {
            acc[key] = this.props.allFields[key];
            return acc;
        }, {});
        const resModel = this.props.viewDetails.model
         this.addDialog(ExpressionEditorDialog, {
            resModel,
            fields: filteredObj,
            expression: this.state.invisible || 'false',
            onConfirm: (domain) => { this.state.invisible = domain; this.autoSave(); }
         })
    }

    modifier(expression, attribute) {
        this.attribute = attribute
        if (attribute == 'invisible') {
            this.state.fieldInvisible = expression
        }
        if (attribute == 'readonly') {
            this.state.fieldReadonly = expression
        }
        if (attribute == 'required') {
            this.state.fieldRequired = expression
        }
    }

    async addSmartButton() {
        if (this.state.related_field && this.state.label) {
            this.env.services.ui.block();
            try {
                const response = await this.rpc("cyllo_studio/add/smart_button", {
                    kwargs: {
                        model: this.props.viewDetails.model,
                        label: this.state.label,
                        field: this.state.related_field,
                        field_model: this.state.fieldDetails.fieldDef.relation,
                        icon: this.state.icon,
                        domain: this.state.domain,
                        invisible: this.state.invisible,
                        groups: this.state.group_ids,
                        view_id: this.props.viewDetails.viewId,
                        addButtonBox: this.props.addButtonBox || false,
                        path: this.props.path,
                    }
                })
                if (response) {
                    let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                    let cleanedStr = response.replace(/\s+/g, ' ').trim();
                    storedArray.push(cleanedStr)
                    sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                    sessionStorage.setItem('ReDO', JSON.stringify([]));
                }
            }
            finally{
                 this.env.services.ui.unblock();
                 this.env.bus.trigger("CLEAR-MENU");
                 this.action.doAction('studio_reload')
            }
        } else {
            this.action.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Related field and Label Name is required',
                    'type': 'warning',
                    'sticky': false,
                }
            })
        }
    }
    async updateSmartButton() {
        if (this.state.label) {
            this.env.services.ui.block();
            try {
                const response = await this.rpc("cyllo_studio/update/smart_button", {
                    kwargs: {
                        model: this.props.viewDetails.model,
                        label: this.state.label,
                        icon: this.state.oldicon !== this.state.icon ? this.state.icon : this.state.oldicon,
                        invisible: this.state.invisible || '',
                        groups: this.state.group_ids || '',
                        path: this.state.cyPath,
                        string_path: this.state.stringPath || '',
                        status_label_path: this.state.StatusLabelPath || false,
                        view_id: this.props.viewDetails.viewId,
                    }
                })
                if (response) {
                    let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                    let cleanedStr = response.replace(/\s+/g, ' ').trim();
                    storedArray.push(cleanedStr)
                    sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                    sessionStorage.setItem('ReDO', JSON.stringify([]));
                }
            } finally {
                this.env.services.ui.unblock();
                this.env.bus.trigger("CLEAR-MENU");
                this.action.doAction('studio_reload')
            }
            this.env.bus.trigger('resetProperties');

        } else {
            this.action.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Label is required',
                    'type': 'warning',
                    'sticky': false,
                }
            })
        }

    }

    async removeSmartButton(){
        if (this.state.cyPath){
             this.env.services.ui.block();
             try {
                const response = await this.rpc("cyllo_studio/remove/smart_button", {
                    kwargs: {
                        model: this.props.viewDetails.model,
                        view_id: this.props.viewDetails.viewId,
                        path: this.state.cyPath,
                    }
                })
               if(response){
                    let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                    let cleanedStr = response.replace(/\s+/g, ' ').trim();
                    storedArray.push(cleanedStr)
                    sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                    sessionStorage.setItem('ReDO', JSON.stringify([]));
                }
             }
             finally {
                this.env.services.ui.unblock();
             }
         }
        this.action.doAction('studio_reload')
        this.env.bus.trigger('CLEAR-MENU',{ fromClose: true });
    }

    handleLabelChange({ target }) {
            const value = target.value;
            this.state.string = value;
            this.state.label = value;

            const smartbutton = document.querySelector('#SmartButtonLabel');

            if (smartbutton) {
                smartbutton.textContent = value;
            }
        }
}

SmartButtonProperties.components = {
    MultiSelectDropDown,
    CylloStudioDropdown,
    IconPicker,
    ModelFieldSelector
}

SmartButtonProperties.template = 'cyllo_studio.SmartButtonProperties'