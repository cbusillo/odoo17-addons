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
            // Get access to the camera
            const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });

            // Create a video element to display the camera feed
            const videoElement = document.createElement('video');
            videoElement.srcObject = stream;
            videoElement.setAttribute('playsinline', 'true'); // Required to tell iOS Safari we don't want fullscreen
            videoElement.style.width = "100%"; // Ensure the video element is visible
            videoElement.style.height = "auto"; // Ensure the video element is visible

            document.body.appendChild(videoElement);
            await videoElement.play(); // Ensure the video is played

            // Initialize QrScanner with the video element
            const qrScanner = new window.QrScanner(videoElement, result => this.onQRCodeScanned(result));
            qrScanner.start();

            // Store the scanner and video element to stop them later
            this.qrScanner = qrScanner;
            this.videoElement = videoElement;

        } catch (error) {
            console.error('Error accessing camera', error);
        }
    }

    onQRCodeScanned(result) {
        this.inputRef.el.value = result;
        // Stop the scanner and video when a code is scanned
        if (this.qrScanner) {
            this.qrScanner.stop();
        }
        if (this.videoElement) {
            this.videoElement.srcObject.getTracks().forEach(track => track.stop());
            document.body.removeChild(this.videoElement);
        }
    }
}

QRCodeWidget.template = 'product_connect.QRCodeWidget';

export const qrCodeWidget = {
    ...CharField,
    component: QRCodeWidget,
};

registry.category('fields').add('qr_scanner', qrCodeWidget);
