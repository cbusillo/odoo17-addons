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
            console.log('Requesting camera access...');
            const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
            console.log('Camera access granted.');

            const videoElement = document.createElement('video');
            videoElement.srcObject = stream;
            videoElement.setAttribute('playsinline', 'true');
            videoElement.style.position = 'absolute';
            videoElement.style.top = '0';
            videoElement.style.left = '0';
            videoElement.style.width = '100vw';
            videoElement.style.height = '100vh';
            videoElement.style.zIndex = '1000'; // Ensure it is on top
            videoElement.style.background = 'black';

            document.body.appendChild(videoElement);
            console.log('Video element added to DOM.');

            await videoElement.play();
            console.log('Video element playing.');

            const qrScanner = new window.QrScanner(videoElement, result => this.onQRCodeScanned(result));
            qrScanner.start();
            console.log('QR Scanner started.');

            this.qrScanner = qrScanner;
            this.videoElement = videoElement;

        } catch (error) {
            console.error('Error accessing camera', error);
        }
    }

    onQRCodeScanned(result) {
        console.log('QR Code scanned:', result);
        this.inputRef.el.value = result;
        if (this.qrScanner) {
            this.qrScanner.stop();
        }
        if (this.videoElement) {
            this.videoElement.srcObject.getTracks().forEach(track => track.stop());
            document.body.removeChild(this.videoElement);
        }
    }
}

export const qrCodeWidget = {
    ...CharField,
    component: QRCodeWidget,
};

registry.category('fields').add('qr_scanner', qrCodeWidget);
