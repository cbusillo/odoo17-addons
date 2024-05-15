/** @odoo-module **/
import { useRef } from '@odoo/owl';
import { CharField } from '@web/views/fields/char/char_field';
import { registry } from '@web/core/registry';

const QrScanner = window.QrScanner;

class QRCodeWidget extends CharField {
    setup() {
        super.setup();
        this.inputRef = useRef("input");
        this.videoContainerRef = useRef("videoContainer");


    }

    async scanQRCode() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.error('Camera API is not supported in this browser.');
            alert('Your browser does not support the Camera API. Please use a compatible browser.');
            return;
        }
        try {
            // Request camera access
            console.log('Requesting camera access...');
            const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
            console.log('Camera access granted.');

            // Create a video element to display the camera feed
            const videoElement = document.createElement('video');
            videoElement.srcObject = stream;
            videoElement.setAttribute('playsinline', 'true'); // Required to tell iOS Safari we don't want fullscreen
            videoElement.style.width = '100%';
            videoElement.style.height = 'auto';

            this.videoContainerRef.el.appendChild(videoElement);

            await videoElement.play();
            console.log('Video element playing.');

            const qrScanner = new QrScanner(
                videoElement,
                result => {
                    console.log('QR code detected:', result);
                    this.inputRef.el.value = result;
                    qrScanner.stop();
                    this.videoContainerRef.el.innerHTML = '';
                },
                {
                    returnDetailedScanResult: true
                }
            );

            await qrScanner.start();
            console.log('QR Scanner started.');
        } catch (error) {
            console.error('Error accessing camera or starting QR scanner', error);
        }
    }
}

QRCodeWidget.template = 'product_connect.QRCodeWidget';

export const qrCodeWidget = {
    ...CharField,
    component: QRCodeWidget,
};

registry.category('fields').add('qr_scanner', qrCodeWidget);
