/** @odoo-module **/
import { registry } from '@web/core/registry'
import { BinaryField, binaryField } from '@web/views/fields/binary/binary_field'

export class FileDropWidget extends BinaryField {
    static template = 'product_connect.FileDropWidget'
    static props = {
        ...BinaryField.props,
    }

    setup() {
        super.setup()
    }

    onDrop(ev) {
        ev.target.classList.add('drag-over');
        ev.target.textContent = 'Drop...';

        ev.preventDefault();
        ev.stopPropagation();

        if (ev.dataTransfer) {
            const { files } = ev.dataTransfer;
            const sortedFiles = [...files].sort((a, b) => a.name.localeCompare(b.name));

            const filePromises = sortedFiles.map((file, index) => {
                return new Promise((resolve, reject) => {
                    if (file instanceof Blob) {
                        const reader = new FileReader();
                        reader.onload = async (e) => {
                            const { result } = e.target;
                            const splitResult = result.split(',');
                            if (splitResult.length > 1) {
                                const baseData = splitResult[1];
                                const imageData = {
                                    image: baseData,
                                    index: index,
                                };
                                resolve(imageData);
                            } else {
                                reject(new Error('Unable to split result into data and mime type'));
                            }
                        };
                        reader.onerror = (error) => {
                            reject(error);
                        };
                        reader.readAsDataURL(file);
                    } else {
                        reject(new Error('File is not a Blob'));
                    }
                });
            });

            Promise.all(filePromises)
                .then((imageDatas) => {
                    imageDatas.forEach((imageData) => {
                        this.props.record.update({ [this.props.name]: imageData });
                    });
                })
                .catch((error) => {
                    console.error('Error processing files:', error);
                });
        } else {
            console.error('dataTransfer is not available');
        }
    }

    onDragEnter(ev) {
        ev.preventDefault()
        ev.target.classList.remove('drag-over')
        ev.target.textContent = 'Release'
    }

    onDragLeave(ev) {
        ev.preventDefault()
        ev.target.classList.add('drag-over')
        ev.target.textContent = 'Drop...'
    }

    onDragOver(ev) {
        ev.preventDefault()
    }
}


export const fileDropWidget = {
    ...binaryField,
    component: FileDropWidget
}

registry.category('fields').add('file_drop', fileDropWidget)
