/** @odoo-module **/
const {Component, useState, useEffect, xml} = owl

export class Number extends Component {
    static defaultProps = {
        negative: true,
        decimal: true,
        setValue: () => {
        },
        value: 0,
        className: ''
    }

    setup() {
        this.state = useState({
            value: this.props.value
        })
        useEffect(() => {
            this.state.value = this.props.value
        }, () => [this.props.value])
        useEffect(() => {
            if (/^-?\d+(\.\d+)?(e-?\d+)?$/.test(this.state.value)) {
                this.state.value = parseInt(this.state.value); // Convert string to number if needed
            } else {
                this.state.value = 0;
            }
        }, () => [this.state.value])
    }

    setFormattedValue() {
        var formatted_val = this.state.value
        if (!this.props.negative) {
            formatted_val = this.state.value >= 0 ? this.state.value : 0
        }
        if (!this.props.decimal) {
            formatted_val = parseInt(formatted_val)
        }
        this.props.setValue(formatted_val)
        this.state.value = formatted_val
    }
}

Number.template = "Number"