/** @odoo-module **/

/**
 * SearchPanelValueDialog
 * ----------------------
 * Dialog for adding or editing a search panel value in Cyllo Studio.
 * Supports icon selection, type switching (Category/Filter), and field selection.
 * Tracks changes to send only modified properties via RPC and maintains Undo/Redo.
 */
import {Component, onWillStart, useState} from "@odoo/owl";
import {useOwnedDialogs, useService} from "@web/core/utils/hooks";
import {ExpressionEditorDialog} from "@web/core/expression_editor_dialog/expression_editor_dialog";
import {MultiRecordSelector} from "@web/core/record_selectors/multi_record_selector";
import {Dialog} from "@web/core/dialog/dialog";
import { CylloStudioDropdown } from "@cyllo_studio/js/view_editor/dropdown/CylloStudioDropdown";
import { _t } from "@web/core/l10n/translation";


const ICONCLASS = ["fa-500px","fa-address-book","fa-address-book-o","fa-address-card","fa-address-card-o","fa-adjust","fa-adn","fa-align-center","fa-align-justify","fa-align-left","fa-align-right","fa-amazon","fa-ambulance","fa-american-sign-language-interpreting","fa-anchor","fa-android","fa-angellist","fa-angle-double-down","fa-angle-double-left","fa-angle-double-right","fa-angle-double-up","fa-angle-down","fa-angle-left","fa-angle-right","fa-angle-up","fa-apple","fa-archive","fa-area-chart","fa-arrow-circle-down","fa-arrow-circle-left","fa-arrow-circle-o-down","fa-arrow-circle-o-left","fa-arrow-circle-o-right","fa-arrow-circle-o-up","fa-arrow-circle-right","fa-arrow-circle-up","fa-arrow-down","fa-arrow-left","fa-arrow-right","fa-arrow-up","fa-arrows","fa-arrows-alt","fa-arrows-h","fa-arrows-v","fa-asl-interpreting","fa-assistive-listening-systems","fa-asterisk","fa-at","fa-audio-description","fa-automobile","fa-backward","fa-balance-scale","fa-ban","fa-bandcamp","fa-bank","fa-bar-chart","fa-bar-chart-o","fa-barcode","fa-bars","fa-bath","fa-bathtub","fa-battery","fa-battery-0","fa-battery-1","fa-battery-2","fa-battery-3","fa-battery-4","fa-battery-empty","fa-battery-full","fa-battery-half","fa-battery-quarter","fa-battery-three-quarters","fa-bed","fa-beer","fa-behance","fa-behance-square","fa-bell","fa-bell-o","fa-bell-slash","fa-bell-slash-o","fa-bicycle","fa-binoculars","fa-birthday-cake","fa-bitbucket","fa-bitbucket-square","fa-bitcoin","fa-black-tie","fa-blind","fa-bluetooth","fa-bluetooth-b","fa-bold","fa-bolt","fa-bomb","fa-book","fa-bookmark","fa-bookmark-o","fa-braille","fa-briefcase","fa-btc","fa-bug","fa-building","fa-building-o","fa-bullhorn","fa-bullseye","fa-bus","fa-buysellads","fa-cab","fa-calculator","fa-calendar","fa-calendar-check-o","fa-calendar-minus-o","fa-calendar-o","fa-calendar-plus-o","fa-calendar-times-o","fa-camera","fa-camera-retro","fa-car","fa-caret-down","fa-caret-left","fa-caret-right","fa-caret-square-o-down","fa-caret-square-o-left","fa-caret-square-o-right","fa-caret-square-o-up","fa-caret-up","fa-cart-arrow-down","fa-cart-plus","fa-cc","fa-cc-amex","fa-cc-diners-club","fa-cc-discover","fa-cc-jcb","fa-cc-mastercard","fa-cc-paypal","fa-cc-stripe","fa-cc-visa","fa-certificate","fa-chain","fa-chain-broken","fa-check","fa-check-circle","fa-check-circle-o","fa-check-square","fa-check-square-o","fa-chevron-circle-down","fa-chevron-circle-left","fa-chevron-circle-right","fa-chevron-circle-up","fa-chevron-down","fa-chevron-left","fa-chevron-right","fa-chevron-up","fa-child","fa-chrome","fa-circle","fa-circle-o","fa-circle-o-notch","fa-circle-thin","fa-clipboard","fa-clock-o","fa-clone","fa-close","fa-cloud","fa-cloud-download","fa-cloud-upload","fa-cny","fa-code","fa-code-fork","fa-codepen","fa-codiepie","fa-coffee","fa-cog","fa-cogs","fa-columns","fa-comment","fa-comment-o","fa-commenting","fa-commenting-o","fa-comments","fa-comments-o","fa-compass","fa-compress","fa-connectdevelop","fa-contao","fa-copy","fa-copyright","fa-creative-commons","fa-credit-card","fa-credit-card-alt","fa-crop","fa-crosshairs","fa-css3","fa-cube","fa-cubes","fa-cut","fa-cutlery","fa-dashboard","fa-dashcube","fa-database","fa-deaf","fa-deafness","fa-dedent","fa-delicious","fa-desktop","fa-deviantart","fa-diamond","fa-digg","fa-dollar","fa-dot-circle-o","fa-download","fa-dribbble","fa-drivers-license","fa-drivers-license-o","fa-dropbox","fa-drupal","fa-edge","fa-edit","fa-eercast","fa-eject","fa-ellipsis-h","fa-ellipsis-v","fa-empire","fa-envelope","fa-envelope-o","fa-envelope-open","fa-envelope-open-o","fa-envelope-square","fa-envira","fa-eraser","fa-etsy","fa-eur","fa-euro","fa-exchange","fa-exclamation","fa-exclamation-circle","fa-exclamation-triangle","fa-expand","fa-expeditedssl","fa-external-link","fa-external-link-square","fa-eye","fa-eye-slash","fa-eyedropper","fa-fa","fa-facebook","fa-facebook-f","fa-facebook-official","fa-facebook-square","fa-fast-backward","fa-fast-forward","fa-fax","fa-feed","fa-female","fa-fighter-jet","fa-file","fa-file-archive-o","fa-file-audio-o","fa-file-code-o","fa-file-excel-o","fa-file-image-o","fa-file-movie-o","fa-file-o","fa-file-pdf-o","fa-file-photo-o","fa-file-picture-o","fa-file-powerpoint-o","fa-file-sound-o","fa-file-text","fa-file-text-o","fa-file-video-o","fa-file-word-o","fa-file-zip-o","fa-files-o","fa-film","fa-filter","fa-fire","fa-fire-extinguisher","fa-firefox","fa-first-order","fa-flag","fa-flag-checkered","fa-flag-o","fa-flash","fa-flask","fa-flickr","fa-floppy-o","fa-folder","fa-folder-o","fa-folder-open","fa-folder-open-o","fa-font","fa-font-awesome","fa-fonticons","fa-fort-awesome","fa-forumbee","fa-forward","fa-foursquare","fa-free-code-camp","fa-frown-o","fa-futbol-o","fa-gamepad","fa-gavel","fa-gbp","fa-ge","fa-gear","fa-gears","fa-genderless","fa-get-pocket","fa-gg","fa-gg-circle","fa-gift","fa-git","fa-git-square","fa-github","fa-github-alt","fa-github-square","fa-gitlab","fa-gittip","fa-glass","fa-glide","fa-glide-g","fa-globe","fa-google","fa-google-plus","fa-google-plus-circle","fa-google-plus-official","fa-google-plus-square","fa-google-wallet","fa-graduation-cap","fa-gratipay","fa-grav","fa-group","fa-h-square","fa-hacker-news","fa-hand-grab-o","fa-hand-lizard-o","fa-hand-o"]

export class SearchPanelValueDialog extends Component {
  static template = "cyllo_studio.SearchPanelValueDialog";
  static components = {
    Dialog,
    MultiRecordSelector,
    CylloStudioDropdown,
  };
  setup() {
    this.rpc = useService("rpc");
    this.action = useService("action");
    this.notification = useService('effect')
    this.addDialog = useOwnedDialogs();
    this.supportedFields = {
        one: ['many2one', 'selection'],
        multi: ['many2one', 'many2many', 'selection'],
    }
    this.state = useState({
      properties: null,
      iconToggle: false,
    });

    onWillStart(() => {
      if (this.props.properties) {
        this.state.properties = {...this.props.properties}
      } else {
        this.state.properties = {
          string: "",
          field: "",
          icon: "",
          color: "#7e8600",
          hierarchize: true,
          enable_counters: false,
          expand: false,
          limit: 200,
          select: 'one',
          invisible: "False",
          groupIds: [],
        }
      }
    });
  }


  // FontAwesome icon list
  get IconClass(){
        return ICONCLASS
   }

   onSelectIcon(icon){
    this.state.properties.icon = icon
     this.state.iconToggle = false
   }

   handleOnChangeType(value){
        this.state.properties.select = value
        if(!this.supportedFields[value].includes(this.props.allFields[this.state.properties.field]?.type)){
            this.state.properties.field = ''
        }
   }
     // Determines if limit input should be shown for the selected field
   get isLimit(){
      return ['many2one', 'many2many'].includes(this.props.allFields[this.state.properties.field]?.type)
   }

  onDomainRadioClick() {
    this.state.properties.invisible = ["False", '0'].includes(this.state.properties.invisible) ? "True" : "False";
  }

  onDomainClick() {
    this.addDialog(ExpressionEditorDialog, {
      resModel: this.props.model,
      fields: this.props.allFields,
      expression: this.state.invisible,
      onConfirm: (expression) => (this.state.invisible = expression),
    });
  }

  // Compare two arrays for equality regardless of order
  arraysEqual(arr1, arr2) {
    // Check if lengths are different
    if (arr1.length !== arr2.length) {
        return false;
    }

    // Create a frequency map for arr1
    const freq1 = {};
    for (let num of arr1) {
        freq1[num] = (freq1[num] || 0) + 1;
    }

    // Check if all elements in arr2 have the same frequency in freq1
    for (let num of arr2) {
        if (!freq1[num]) {
            return false;
        }
        freq1[num]--;
    }

    return true;
}
    // Filter available fields based on type and selection mode
    get fields(){
        const fields = []
        const supportedFields = this.supportedFields[this.state.properties.select]
        Object.values(this.props.fields).forEach((field)=>{
            if(supportedFields.includes(field.type)){
                if(!['create_uid', 'write_uid','user_id'].includes(field.name)){
                    fields.push({value: field.name, label: field.string})
                }
            }
        })
        return fields
    }

     handleFieldChange(value) {
        this.state.properties.field = value
    }

    get Type() {
        return [{value:'one',label:'Category'}, {value:'multi',label:'Filter'}]
    }

  // Confirm dialog and send updates via RPC
  async onConfirm() {
    if (!this.state.properties.field) {
        this.notification.add({
            title: _t("Warning"),
            message: "Please select a field.",
            type: "notification_panel",
            notificationType: "warning",
        });
      return;
    }

    let rpcUrl = "cyllo_studio/search/add/search_panel_value";

    let properties = {
        ...this.state.properties
    };

    if (this.props.properties) {
      rpcUrl = "cyllo_studio/search/update/search_panel_value";
      properties = Object.keys(properties).reduce((acc, key) => {
        if(Array.isArray(properties[key])){
                if(!this.arraysEqual(properties[key], this.props.properties[key])){
              acc[key] = properties[key];
            }
        } else {
            if (properties[key] != this.props.properties[key]) {
              acc[key] = properties[key];
            }
        }
        return acc;
      }, {});
      if ('field' in properties) {
          properties.name = properties.field;
          delete properties.field;
      }
    }
    if(Object.keys(properties).length){
        this.env.services.ui.block();
        try {
         const response =  await this.rpc(rpcUrl, {
            path: this.props.path,
            view_id: this.props.viewId,
            model: this.props.model,
            properties,
          });
           if(response){
                    let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                    let cleanedStr = response.replace(/\s+/g, ' ').trim();
                    storedArray.push(cleanedStr);
                    sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                    sessionStorage.setItem('ReDO', JSON.stringify([]));
                }
        } finally {
          this.env.services.ui.unblock();
        }
//--------------------changed-------------
        this.action.doAction("studio_reload");
        window.location.reload()
//-------------------------------------
    }

    this.props.close();
  }
  onDiscard() {
    this.props.close();
  }
}
