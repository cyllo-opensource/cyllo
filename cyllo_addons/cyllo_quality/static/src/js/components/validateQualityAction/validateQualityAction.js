/** @odoo-module */
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState, Component, markup, xml, useRef, onMounted, status } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

export class ValidateQualityAction extends Component {
    static components = { Dialog }
    static defaultProps = {
        handleModalClose: () => { },
    };
    setup() {

        this.orm = useService("orm");
        this.action = useService("action")
        this.qcInstruction = useRef('qcInstruction')
        this.notification = useService("notification");
        this.state = useState({
            addNote: false,
            qualityCheckNote: false,
            qcStatus: false,
            qcValue: false,
            checkValue: false,
            imageSrc: false,
            isBlocked: false,
            blockerName: '',
        })

        onWillStart(async () => {
            const qcAction = this.props.quality_check_action;
            const qcActionData = Array.isArray(qcAction) ? qcAction[0] : qcAction;
            this.props.quality_check_action = qcActionData;

            const quality_check = this.props.quality_check;
            this.props.quality_check = Array.isArray(quality_check) ? quality_check[0] : quality_check;

            if (this.props.quality_check_action.blocked_by_id) {
                const results = await this.orm.searchRead("quality.check.line", [
                    ["quality_check_id", "=", this.props.quality_check_action.quality_check_id[0]],
                    ["quality_inspection_id", "=", this.props.quality_check_action.blocked_by_id[0]]
                ], ["is_checked", "inspection_action_id"]);
                if (results.length > 0 && !results[0].is_checked) {
                    this.state.isBlocked = true;
                    this.state.blockerName = results[0].inspection_action_id[1];
                }
            }
        });

        onMounted(() => {
            if (this.props.quality_check_action.instruction) {
                this.qcInstruction.el.addEventListener("click", (ev) => {
                    this.action.doAction({
                        type: 'ir.actions.client',
                        tag: 'quality_instruction_action',
                        target: 'new',
                        params: {
                            instruction: this.props.quality_check_action.instruction,
                        }
                    });
                });
            }
        })
    }

    addNote() {
        this.state.addNote = true
    }

    onImageChange(event) {
        const file = event.target.files[0];
        if (file) {
            const validImageTypes = ['image/jpeg', 'image/png', 'image/gif'];
            if (validImageTypes.includes(file.type)) {
                const reader = new FileReader();

                // Set the image preview once the file is read
                reader.onload = (e) => {
                    this.state.imageSrc = e.target.result;
                    this.state.qcValue = e.target.result; // Store image data in qcValue for validation
                };

                // Read the image file as a data URL
                reader.readAsDataURL(file);
            } else {
                alert('Please upload a valid image file.');
            }
        } else {
            alert('No file selected.');
        }
    }

    get getInstruction() {
        return markup(this.props.quality_check_action.instruction.replace(/<img/g, '<img class="instruction-img"'))
    }

    passCheck() {
        this.state.checkValue = 'pass'
        this.validateQualityCheck()
    }

    failCheck() {
        this.state.checkValue = 'fail'
        this.validateQualityCheck()
    }

    async validateQualityCheck() {
        const type = this.props.quality_check_action.inspection_type_id[1];
        const isValueEmpty = this.state.qcValue === false ||
            this.state.qcValue === null ||
            this.state.qcValue === undefined ||
            String(this.state.qcValue).trim() === '';

        if (['Take a picture', 'Measure'].includes(type) && isValueEmpty) {
            this.notification.add(_t(`The value for the inspection action ${this.props.quality_check_action.inspection_action_id[1]} is required.`), {
                type: "danger",
            });
            return;
        }

        let finalValue = this.state.qcValue;
        if (type === 'Take a picture') {
            finalValue = `${this.state.checkValue}|${this.state.qcValue}`;
        } else if (!['Measure'].includes(type)) {
            finalValue = this.state.checkValue;
        }
        this.state.qcStatus = await this.orm.call("quality.check.line", "validate_quality_actions", [this.props.quality_check_action.id, finalValue, this.state.qualityCheckNote])
        if (status(this) !== "destroyed") {
            this.env.bus.trigger("RELOAD_QC_DATA")
            this.handleModalClose()
        }
    }

    handleModalClose() {
        this.props.close()
        this.props.handleModalClose({
            status: this.state.qcStatus
        })
    }
}
ValidateQualityAction.template = 'ValidateQualityAction';
registry.category("actions").add("validate_quality_action", ValidateQualityAction);