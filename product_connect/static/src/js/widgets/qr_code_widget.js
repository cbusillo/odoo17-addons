/** @odoo-module **/
import { onMounted, onWillUnmount, useRef, useState } from '@odoo/owl';
import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { isMobileOS } from "@web/core/browser/feature_detection";
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
            flashlightLabel: undefined,
        })
        this.qrReaderRef = useRef('qrReader');

        this.onScanSuccess = this.onScanSuccess.bind(this);
        onMounted(async () => {
            // noinspection JSUnresolvedReference
            this.qrScanner = new window.QrScanner(
                this.qrReaderRef.el,
                this.onScanSuccess,
                { returnDetailedScanResult: true }
            );

            await this.startScanner()
            if (isMobileOS()) {
                this.state.flashlightLabel = "Flash on"
            }
        })

        onWillUnmount(() => {
            this.qrScanner.destroy()
        })
    }

    onScanSuccess(result) {
        try {
            if (result.data === this.state.barcode) {
                return;
            }
            this.stopScanner();
            this.props.record.update({ [this.props.name]: result.data })
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

    //
    startScanner() {
        this.qrScanner.start();
        this.state.buttonLabel = 'Stop'
        this.state.scanEnabled = true;
        this.qrReaderRef.el.classList.remove('d-none');

        //     const currentState = this.htmlQrCode.getState()
        //     if (currentState === Html5QrcodeScannerState.PAUSED) {
        //         this.htmlQrCode.resume()
        //     } else {
        //         this.htmlQrCode.start(
        //             { facingMode: "environment" },
        //             {
        //                 fps: 60,
        //             },
        //             this.onScanSuccess
        //         )
        //     }
    }

    //
    stopScanner() {
        this.qrScanner.stop();
        this.state.buttonLabel = 'Scan'
        this.state.scanEnabled = false;
        this.qrReaderRef.el.classList.add('d-none');
        //     this.htmlQrCode?.pause(true)
    }

    toggleScan() {
        if (this.state.scanEnabled) {
            this.stopScanner()
            //     const currentState = this.htmlQrCode.getState();
            //     // noinspection JSUnresolvedReference
            //     if (currentState === Html5QrcodeScannerState.SCANNING) {
            //         this.stopScanner()
            //     }
        } else {
            this.startScanner()
            //     this.startScanner().catch((error) => {
            //         console.error('An error occurred:', error)
            //     })
        }
        // this.state.scanEnabled = !this.state.scanEnabled;
    }

    toggleFlashlight() {
        if (this.state.flashlightLabel === 'Flash On') {
            this.qrScanner.turnFlashOn();
            this.state.flashlightLabel = 'Flash Off';
        } else {
            this.qrScanner.turnFlashOff();
            this.state.flashlightLabel = 'Flash On';
        }
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
