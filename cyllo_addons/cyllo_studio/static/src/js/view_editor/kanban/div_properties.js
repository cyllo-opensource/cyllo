/** @odoo-module **/

/**
 * DivProperties Component
 * Provides a UI editor for modifying div element properties such as
 * margin, padding, flex settings, alignment, wrapping, and gap.
 *
 * Features:
 * - Dynamically applies CSS margin/padding via inline styles.
 * - Toggles flexbox properties (direction, alignment, wrapping, gap).
 * - Automatically saves changes via RPC calls with undo/redo support.
 * - Synchronizes DOM classList and styles with internal state.
 */
const { Component, useState, useRef, useEffect, onMounted, onWillUnmount, onWillUpdateProps } = owl;
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { shallowEqual } from "@web/core/utils/objects";
import {_t} from "@web/core/l10n/translation";


const marginPaddingKeys = [
    'marginTop',
    'marginRight',
    'marginLeft',
    'marginBottom',
    'paddingTop',
    'paddingRight',
    'paddingLeft',
    'paddingBottom'
];

// Define the mappings
const flexMap = {
    'flex-column': 'flex-column',
    'flex-row': 'flex-row',
};

const justifyContentMap = {
    'justify-content-start': 'justify-content-start',
    'justify-content-end': 'justify-content-end',
    'justify-content-center': 'justify-content-center',
    'justify-content-between': 'justify-content-between',
    'justify-content-around': 'justify-content-around',
};

const alignItemsMap = {
    'align-items-start': 'align-items-start',
    'align-items-end': 'align-items-end',
    'align-items-center': 'align-items-center',
    'align-items-baseline': 'align-items-baseline',
    'align-items-stretch': 'align-items-stretch',
};

const wrapMap = {
    'flex-nowrap': 'flex-nowrap',
    'flex-wrap': 'flex-wrap',
    'flex-wrap-reverse': 'flex-wrap-reverse',
}

const gapMap = {
    'gap-0': 'gap-0',
    'gap-1': 'gap-1',
    'gap-2': 'gap-2',
    'gap-3': 'gap-3',
    'gap-4': 'gap-4',
    'gap-5': 'gap-5',
};

// Helper function to check classes and set state
function setStateFromClass(classList, states, classesMap, stateKey) {
    let classFound = false;
    for (const [key, value] of Object.entries(classesMap)) {
        if (classList.includes(key)) {
            for (const state of states) {
                state[stateKey] = value;
                classFound = true
            }
            break;
        }
    }

    if (!classFound) {
        for (const state of states) {
            state[stateKey] = '';
        }
    }
}

export class DivProperties extends Component {
    static template='cyllo_studio.DivProperties'
    setup(){
        this.action = useService('action')
        this.rpc = useService('rpc')
        this.notification = useService('effect')
        this.divRef = useRef('divRef')
        this.saveHandled = false
        this._autoSaving = false
        this._autoSavePending = false

        this.state = useState({
            div: this.props.div,
            isFlex: false
        })
        this.properties = useState({
              marginTop: 0,
              marginRight: 0,
              marginBottom: 0,
              marginLeft: 0,
              paddingTop: 0,
              paddingRight: 0,
              paddingBottom: 0,
              paddingLeft: 0,
              flex: "",
              justifyContent: "",
              alignItems: "",
              wrap: "",
              gap: "",
        })
        this.oldProperties = useState({...this.properties})

         onMounted(() => {
            this.menu = document.getElementById("cy-studio-menu")
            this.viewMenu = document.getElementById("pills-home-tab")
            this.menuClose = document.getElementById("cy-studio-menu-close")
            this.setProperties(this.props)
        });
        onWillUpdateProps((nextProps)=>this.setProperties(nextProps))

        useEffect(()=>{

           for (const [key, value] of Object.entries(this.properties)) {
                if(marginPaddingKeys.includes(key)){
                    const cssKey = key.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();
                    this.state.div.style.setProperty(cssKey, `${value}px`, 'important');
                }
            }
        }, ()=>[this.properties.marginTop, this.properties.marginRight,
            this.properties.marginBottom, this.properties.marginLeft,
            this.properties.paddingTop, this.properties.paddingRight,
            this.properties.paddingBottom, this.properties.paddingLeft
        ])

        useEffect(()=>{
            if(this.properties.flex && this.state.isFlex){
                // Define the list of mapping objects to remove classes from
                const mappingObjects = [flexMap, justifyContentMap, alignItemsMap, wrapMap, gapMap];

                // Remove existing classes in the same mapping objects
                for (const map of mappingObjects) {
                    for (const key of Object.keys(map)) {
                        this.state.div.classList.remove(key);
                    }
                }
                //Add selected classes
                for (const [key, value] of Object.entries(this.properties)) {
                    if(!marginPaddingKeys.includes(key) && value){
                        this.state.div.classList.add(value)
                    }
                }
            }

        }, ()=> [this.properties.flex, this.properties.justifyContent,
            this.properties.alignItems, this.properties.wrap, this.properties.gap])
    }

       /**
     * Extracts and applies current CSS and class properties of the div.
     * Used when component mounts or props change.
     */

    async setProperties(props){
        const classList = [...props.div.classList]
        this.oldClassList =   classList.filter(className =>
            !className.includes('border-class') && !className.includes('cy-studio-kanban-border')
        );

        const computedStyles = window.getComputedStyle(props.div);
        this.state.isFlex = computedStyles.display === 'flex'

        // Update properties state based on classList
        setStateFromClass(classList, [this.properties, this.oldProperties], flexMap, 'flex');
        setStateFromClass(classList,[this.properties, this.oldProperties], justifyContentMap, 'justifyContent');
        setStateFromClass(classList, [this.properties, this.oldProperties], alignItemsMap, 'alignItems');
        setStateFromClass(classList, [this.properties, this.oldProperties], wrapMap, 'wrap');
        setStateFromClass(classList, [this.properties, this.oldProperties], gapMap, 'gap');


        // Handle specific case for flex
        if (computedStyles.display === 'flex') {
            if(computedStyles.flexDirection === 'row'){
                this.properties.flex = "flex-row";
                this.oldProperties.flex = "flex-row";
                this.oldClassList.push("flex-row")
            } else if(computedStyles.flexDirection === 'column'){
                this.properties.flex = "flex-column";
                this.oldProperties.flex = "flex-column";
                this.oldClassList.push("flex-column")
            }

        }

        this.state.div = props.div


        this.properties.marginTop = parseInt(computedStyles.marginTop, 10);
        this.properties.marginRight = parseInt(computedStyles.marginTop, 10);
        this.properties.marginBottom = parseInt(computedStyles.marginBottom, 10);
        this.properties.marginLeft = parseInt(computedStyles.marginLeft, 10);

        this.properties.paddingTop = parseInt(computedStyles.paddingTop, 10);
        this.properties.paddingRight = parseInt(computedStyles.paddingRight, 10);
        this.properties.paddingBottom = parseInt(computedStyles.paddingBottom, 10);
        this.properties.paddingLeft = parseInt(computedStyles.paddingLeft, 10);

        this.oldStyle = {}
        for (const [key, value] of Object.entries(this.properties)) {
            if(marginPaddingKeys.includes(key)){
                this.oldStyle[key] = value
            }
        }


    }

     setProperty(propertyKey, value){
        if (this.oldProperties[propertyKey] === value){
            this.properties[propertyKey] = ''
            this.oldProperties[propertyKey] = ''
        }
        else{
            this.properties[propertyKey] = value
            this.oldProperties[propertyKey] = value
        }
        this.autoSave()
    }

    handleFlex({target}){
        this.state.isFlex = target.checked
        if(target.checked){
            this.state.div.classList.add('d-flex');
            this.setProperty('flex', 'flex-row')
        } else {
            const mappingObjects = [flexMap, justifyContentMap, alignItemsMap, wrapMap, gapMap];
             for (const map of mappingObjects) {
                for (const key of Object.keys(map)) {
                    this.state.div.classList.remove(key);
                }
            }
            const computedStyles = window.getComputedStyle(this.state.div);
            this.state.div.classList.remove('d-flex');
            if(computedStyles.display === 'flex'){
                this.state.div.style.display = 'block';
            }
            this.setProperty('justifyContent', '')
            this.setProperty('alignItems', '')
            this.setProperty('wrap', '')
            this.setProperty('gap', '')
            this.autoSave()
        }
    }


    onEnter(propertyKey, value){
        this.properties[propertyKey] = value
    }

    onLeave(propertyKey){
        this.properties[propertyKey] = this.oldProperties[propertyKey]
    }

    async removeHighlighting(div) {
      div.classList.remove('highlight-padding');

      const wrapper = div.parentNode;
      if (wrapper && wrapper.classList.contains('highlight-margin')) {
        const parent = wrapper.parentNode;
        parent.insertBefore(div, wrapper);
        parent.removeChild(wrapper);
      }
    }

    arraysHaveSameStrings(arr1, arr2) {
        const set1 = new Set(arr1);
        const set2 = new Set(arr2);
        return set1.size === set2.size && [...set1].every(value => set2.has(value));
    }

    autoSave() {
        if (this._autoSaving) { this._autoSavePending = true; return; }
        this._autoSaving = true;
        this.doSave().finally(() => {
            this._autoSaving = false;
            if (this._autoSavePending) { this._autoSavePending = false; this.autoSave(); }
        });
    }

    async doSave() {
        this.env.services.ui.block();
        try {
            const classList = [...this.state.div.classList].filter(className =>
                !className.includes('border-class') && !className.includes('cy-studio-kanban-border')
            );
            this.state.div.classList.remove('border-class');

            let style = {};
            for (const [key, value] of Object.entries(this.properties)) {
                if (marginPaddingKeys.includes(key)) {
                    style[key] = value;
                }
            }

            const isSameStyle = shallowEqual(this.oldStyle, style);
            const isSameClass = this.arraysHaveSameStrings(this.oldClassList, classList);
            if (isSameClass && isSameStyle) {
                return;
            }
            const response = await this.rpc("cyllo_studio/kanban/update/div", {
                model: this.props.model,
                view_type: this.props.viewType,
                view_id: this.props.viewId,
                path: this.props.path,
                properties: {
                    class_list: classList,
                    is_class: !isSameClass,
                    is_style: !isSameStyle,
                    style,
                }
            });
            if (response) {
                let storedArray = JSON.parse(sessionStorage.getItem('UndoRedo')) || [];
                let cleanedStr = response.replace(/\s+/g, ' ').trim();
                storedArray.push(cleanedStr);
                sessionStorage.setItem('UndoRedo', JSON.stringify(storedArray));
                sessionStorage.setItem('ReDO', JSON.stringify([]));
            }
            this.notification.add({
                title: _t("Success"),
                message: "Div properties have been saved.",
                type: "notification_panel",
                notificationType: "success",
            });
        } finally {
            this.env.services.ui.unblock();
        }
        this.action.doAction("studio_reload");
    }
    async closeDivSidebar() {
        this.env.bus.trigger('CLEAR-MENU', {
            fromClose: true
        });
    }

}