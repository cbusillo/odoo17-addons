/** @odoo-module **/
import { onMounted, onWillUnmount, useState } from '@odoo/owl';
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

        this.onScanSuccess = this.onScanSuccess.bind(this);
        onMounted(() => {
            // noinspection JSUnresolvedReference
            this.htmlQrCode = new window.Html5Qrcode("reader");
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
                });
        } catch (error) {
            console.error('An error occurred:', error)
        }
    }

    startScanner() {
        const config = {
            fps: 10,
            qrbox: { width: 200, height: 200 },
        };
        this.htmlQrCode.start(
            { facingMode: "environment" },
            config,
            this.onScanSuccess
        );
        this.state.buttonLabel = 'Stop'
    }

    stopScanner() {
        this.htmlQrCode?.stop().catch((error) => {
            console.error('Failed to stop scanner:', error);
        });
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
            this.startScanner()
        }
        this.state.scanEnabled = !this.state.scanEnabled;
    }
}

export const qrCodeWidget = {
    ...charField,
    component: QRCodeWidget,
};

registry.category('fields').add('qr_scanner', qrCodeWidget);
