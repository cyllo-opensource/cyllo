/** @odoo-module **/
const { Component, onMounted, useRef, onWillUpdateProps } = owl

/**
 * @description This is an SQL editor component.
 * It provides a CodeMirror-based SQL editor with configurable options.
 *
 * @class
 * @extends {Component}
 */
export class SQLEditor extends Component {
    setup(){
        this.ref = useRef('editor')
        onMounted(() => {
            this.code = CodeMirror(this.ref.el, {
              lineNumbers: this.props.lineNumbers || true,
              lineWrapping: this.props.lineWrapping || true,
              mode: 'sql',
              value: this.props.value,
              theme: this.props.theme,
              readOnly: this.props.readonly,
            })
            this.code.on('blur', this.onBlur.bind(this))
            this.code.setSize('100%', '50%')
        })
        onWillUpdateProps((nextProps) => {
            this.code.doc.setValue(nextProps.value)
        })
    }
    onBlur(){
        const query = this.code.doc.getValue()
        if(query === this.props.value) return
        this.props.onBlur(query)
    }
}
SQLEditor.template = "SQLEditor"