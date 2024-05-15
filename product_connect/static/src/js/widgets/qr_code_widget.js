/** @odoo-module **/

import { CharField } from '@web/views/fields/char/char_field';
import { registry } from '@web/core/registry';
import { useRef } from '@odoo/owl';

class QRCodeWidget extends CharField {
    setup() {
        super.setup();
        this.inputRef = useRef("input");
    }

    async scanQRCode() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
            const videoElement = document.createElement('video');
            videoElement.srcObject = stream;
            videoElement.setAttribute('playsinline', 'true'); // Required to tell iOS Safari we don't want fullscreen
            document.body.appendChild(videoElement);
            await videoElement.play();

            const qrScanner = new window.QrScanner(videoElement, result => this.onQRCodeScanned(result));
            qrScanner.start();
        } catch (error) {
            console.error('Error accessing camera', error);
        }
    }

    onQRCodeScanned(result) {
        this.inputRef.el.value = result;
    }
}

QRCodeWidget.template = 'product_connect.QRCodeWidget';

export const qrCodeWidget = {
    ...CharField,
    component: QRCodeWidget,
};

registry.category('fields').add('qr_scanner', qrCodeWidget);
