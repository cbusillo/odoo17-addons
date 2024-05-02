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

            const uploadPromises = sortedFiles.map((file, index) => {
                return new Promise((resolve, reject) => {
                    if (file instanceof Blob) {
                        const formData = new FormData();
                        formData.append('file', file);
                        formData.append('index', index);

                        fetch('/upload', {
                            method: 'POST',
                            body: formData,
                        })
                            .then((response) => {
                                if (response.ok) {
                                    return response.json();
                                } else {
                                    throw new Error('Upload failed');
                                }
                            })
                            .then((data) => {
                                resolve(data);
                            })
                            .catch((error) => {
                                reject(error);
                            });
                    } else {
                        reject(new Error('File is not a Blob'));
                    }
                });
            });

            Promise.all(uploadPromises)
                .then((results) => {
                    results.forEach((result) => {
                        const { index, url } = result;
                        this.props.record.update({ [this.props.name]: { index, url } });
                    });
                })
                .catch((error) => {
                    console.error('Error uploading files:', error);
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
