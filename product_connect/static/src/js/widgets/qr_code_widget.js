/** @odoo-module **/

import { CharField } from '@web/views/fields/char/char_field';
import { registry } from '@web/core/registry';
import { useRef } from '@odoo/owl';

const QrScanner = window.QrScanner;

class QRCodeWidget extends CharField {
    setup() {
        super.setup();
        this.inputRef = useRef("input");
        this.videoContainerRef = useRef("videoContainer");
    }

    scanQRCode() {
        const videoElement = document.createElement('video');
        videoElement.setAttribute('playsinline', 'true'); // Required to tell iOS Safari we don't want fullscreen
        videoElement.style.width = '100%';
        videoElement.style.height = 'auto';


        this.videoContainerRef.el.appendChild(videoElement);

        const qrScanner = new QrScanner(
            videoElement,
            result => {
                this.inputRef.el.value = result
                qrScanner.stop()
                this.videoContainerRef.el.innerHTML = '';
            })
        qrScanner.start()
    }
}

QRCodeWidget.template = 'product_connect.QRCodeWidget';

export const qrCodeWidget = {
    ...CharField,
    component: QRCodeWidget,
};

registry.category('fields').add('qr_scanner', qrCodeWidget);
