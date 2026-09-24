/** @odoo-module **/
import { Component, useState, onWillStart, onMounted, useRef, useSubEnv } from "@odoo/owl";
import { useBus, useService } from '@web/core/utils/hooks';

let zoomLevel = 1;

/* Create new WhatsappWelcome by extending Component */
export class WhatsappImagePreview extends Component {
    setup() {
        this.imagePreview = useRef('imagePreview')
    }

    /* To zoom image at the WhatsappImagePreview view*/
    zoomInImage() {
        zoomLevel += 0.2; // Increase zoom level
        this.imagePreview.el.style.transform = `scale(${zoomLevel})`;
    }

    /* To zoom out image at the WhatsappImagePreview view*/
    zoomOutImage() {
        zoomLevel -= 0.2; // Decrease zoom level
        if (zoomLevel < 0.5) {
            zoomLevel = 0.5; // Ensure zoom level doesn't go below 1
        }
        this.imagePreview.el.style.transform = `scale(${zoomLevel})`;
    }

    /**
     * Get the corresponding image file type icon for a given file extension.
     * @returns {string} The filename of the icon for the file type, or an empty string if the type is not recognized.
     **/
    get fileType() {
        let inputFile = this.props.inputFile.name
        let type = inputFile.split('.').pop()
        let fileType = {
            'docx': 'docx.png',
            'doc': 'doc.png',
            'pdf': 'pdf.png',
            'txt': 'txt.png',
            'ppt': 'ppt.png',
            'xls': 'xls.png',
            'xlsx': 'xlsx.png',
            'png': 'png.png',
            'jpeg': 'jpeg.png',
            'jpg': 'jpeg.png',
            'mp3': 'mp3.png',
            'mp4': 'mp4.png',
            'zip': 'zip.png'
        }
        return fileType[type] || '';
    }
}

/* Associate 'WhatsappWelcome' template with the WhatsappWelcome component.*/
WhatsappImagePreview.template = 'WhatsappImagePreview';