/** @odoo-module */
import { ImageField } from "@web/views/fields/image/image_field";
import { patch } from "@web/core/utils/patch";
import { useRef, useState, onPatched } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/**
* patch the 'ImageField' component to adding the actions for the new button
*/
patch(ImageField.prototype, {
    setup() {
        super.setup(...arguments);
        this.ref = useRef('CylloImageCaptureRoot')
        this.state = useState({
            isValid: true,
            image: 'image'
        })
        /**
        * Calling the corresponding actions when the state is changed
        */
         onPatched(() => {
            if (this.state.image == 'camera') {
                this.OpenCamera()
            }else if( this.state.image == 'capture') {
                this.OnClickCaptureImage()
            }
        });
    },
    /**
    * onClick event for the open camera button,
    * for opening the camera for capture the image
    */
    async OpenCamera(){
        this.player = this.ref.el.querySelector('#player')
        try {
            this.player.srcObject  = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
       } catch (err) {
            this.state.image = 'image'
            this.notification.add(_t("Please Grant access to the camera", { type: "danger", sticky: true, }))
       }
    },
    /**
    * onClick event for the open camera button,
    * for  Capture the image from webcam and close the webcam
    */
    OnClickCaptureImage() {
        let snapshot = this.ref.el.querySelector('#snapshot')
        var context = snapshot.getContext('2d');
        context.drawImage(this.player, 0, 0, 320, 240);
        this.ref.el.querySelector('#image').value = context.canvas.toDataURL();
        this.url = context.canvas.toDataURL()
    },
    /**
    * onClick event for the close camera button,
    * for discard the changes
    */
    onClickCloseCam(){
        this.state.image = 'image'
        if (this.player.srcObject) {
          this.player.srcObject.getVideoTracks().forEach(track => track.stop());
        }
    },
    /**
    * onClick event for the open camera button,
    * for Saving the image to that field
    */
    OnClickSaveImage(){
        this.state.image = 'image'
        var image = this.url.split(',');
        this.props.value = image[1]
        var data = {
            data:  image[1],
            name : "ImageFile.png",
            objectUrl: null,
            size : 106252,
            type: "image/png"
        }
        if (this.player.srcObject) {
          this.player.srcObject.getVideoTracks().forEach(track => track.stop());
        }
        this.onFileUploaded(data)
    }
});
