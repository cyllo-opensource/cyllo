/** @odoo-module */
const {Component, useState, onWillStart, onMounted, onWillUnmount, useRef} = owl
import {useService} from "@web/core/utils/hooks";

export class WorkPager extends Component {
    setup() {
        super.setup()
        this.actionService = useService("action")
        this.state = useState({
            currentValue: 1,
            recordList: [],
            isEdit: false
        })
        this.inputRef = useRef("currentRecordNumber");
        onWillStart(async () => {
            this.state.recordList = [...new Set(this.props.recordList)];
            this.state.currentValue = this.state.recordList.indexOf(this.props.currentRecord) + 1;

        });
        onMounted(() => {
            document.addEventListener('click', this.handleClickOutside);
        });

        onWillUnmount(() => {
            document.removeEventListener('click', this.handleClickOutside);
        });
    }

    static template = "WorkPager"
    static props = {
        recordList: {type: Array, default: []},
        currentRecord: {type: Number, default: 1},
        update:{type: Function, optional: true},
    };

    handleClickOutside = (event) => {
        if (this.inputRef.el && !this.inputRef.el.contains(event.target)) {
            if (this.inputRef.el.value !== this.state.currentValue && 1 <= this.inputRef.el.value <= this.state.recordList.length) {
                this.navigate(false, this.inputRef.el.value)
            }
            if(this.inputRef.el.value > this.state.recordList.length) {
                this.navigate(false, this.state.recordList.length)
            }
        }
    }

    currentClick() {
        this.state.isEdit = true
    }

    get recordLength() {
        return this.state.recordList.length
    }

    get currentRecordNumber() {
        return this.state.currentValue;
    }

    navigate(n, dynamic = false) {
        if (dynamic) {
            const nextID = this.state.recordList[dynamic - 1]
            this.actionService.doAction({
                type: "ir.actions.client",
                tag: "automation_view",
                context: {
                    id: nextID
                }
            });
        } else {
            let nextID = this.state.recordList[this.state.currentValue - 1 + n]
            if (this.state.currentValue === this.state.recordList.length && n === 1) {
                nextID = this.state.recordList[0]
            }
            if (this.state.currentValue === 1 && n === -1) {
                nextID = this.state.recordList[this.state.recordList.length - 1]
            }
            this.props.update(nextID)
        }
    }
}
