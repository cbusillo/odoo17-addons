/** @odoo-module **/
import { onMounted, onWillUnmount, useRef, useState } from '@odoo/owl';
import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { CharField, charField } from '@web/views/fields/char/char_field';
import { registry } from '@web/core/registry';

class QRCodeWidget extends CharField {
    static template = 'product_connect.QRCodeWidget';
    static props = {
        ...CharField.props,
    }

    setup() {
        super.setup();
        this.state = useState({
            scanEnabled: true,
            buttonLabel: 'Stop',
        })
        this.qrReaderRef = useRef('qrReader');


        this.onScanSuccess = this.onScanSuccess.bind(this);
        onMounted(() => {
            // noinspection JSUnresolvedReference
            this.htmlQrCode = new window.Html5Qrcode("qrReader");
            this.startScanner();
        })

        onWillUnmount(() => {
            this.htmlQrCode.stop();
        })
    }

    onScanSuccess(decodedText) {
        try {
            if (decodedText === this.state.barcode) {
                return;
            }
            this.stopScanner()
            this.props.record.update({ [this.props.name]: decodedText })
                .catch((error) => {
                    this.env.services.dialog.add(ConfirmationDialog, {
                        title: 'Error',
                        body: error.data.message,
                        confirm: () => {
                            this.startScanner();
                        },
                    });
                })
        } catch (error) {
            console.error('An error occurred:', error)
        }
    }

    startScanner() {
        this.qrReaderRef.el.classList.remove('d-none');
        const currentState = this.htmlQrCode.getState()
        if (currentState === Html5QrcodeScannerState.PAUSED) {
            this.htmlQrCode.resume()
        } else {
            this.htmlQrCode.start(
                { facingMode: "environment" },
                {
                    fps: 60,
                },
                this.onScanSuccess
            )
            // const scannerCapabilities = this.htmlQrCode.getRunningTrackCapabilities();
            // const zoomCapability = scannerCapabilities.zoom > 2 ? 2.0 : scannerCapabilities.zoom;
            //
            // const constraints = {
            //     // Set a higher height then default to get a better resolution
            //     width: { ideal: 2000 },
            //     height: { ideal: 2000 },
            //
            //     // Set the ideal frame rate based on the capabilities
            //     frameRate: { ideal: scannerCapabilities.frameRate?.max || 30 },
            //
            //     advanced: [
            //         // conditionally add the zoom capability if it is supported
            //         ...(scannerCapabilities.zoom ? [{ zoom: zoomCapability }] : []),
            //
            //         // conditionally add the focus distance capability if it is supported
            //         ...(scannerCapabilities.focusDistance ? [{ focusDistance: 1 }] : []),
            //     ],
            // };
            //
            //
            // await this.htmlQrCode.applyVideoConstraints(constraints);
        }
        this.state.buttonLabel = 'Stop'
    }

    stopScanner() {
        this.qrReaderRef.el.classList.add('d-none');
        this.htmlQrCode?.pause(true)
        this.state.buttonLabel = 'Scan'
    }

    toggleScan() {
        if (this.state.scanEnabled) {
            const currentState = this.htmlQrCode.getState();
            // noinspection JSUnresolvedReference
            if (currentState === Html5QrcodeScannerState.SCANNING) {
                this.stopScanner()
            }
        } else {
            this.startScanner().catch((error) => {
                console.error('An error occurred:', error)
            })
        }
        this.state.scanEnabled = !this.state.scanEnabled;
    }

    onInputFocus() {
        this.startScanner()
    }
}

export const qrCodeWidget = {
    ...charField,
    component: QRCodeWidget,
};

registry.category('fields').add('qr_scanner', qrCodeWidget);
