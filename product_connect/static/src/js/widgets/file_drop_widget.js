/** @odoo-module **/
import { useState } from '@odoo/owl'
import { useService } from '@web/core/utils/hooks'
import { registry } from '@web/core/registry'
import { BinaryField, binaryField } from '@web/views/fields/binary/binary_field'

import { resizeImage } from '@product_connect/js/utils/image_utils'


export class FileDropWidget extends BinaryField {
    static template = 'product_connect.FileDropWidget'
    static props = {
        ...BinaryField.props,
    }

    setup() {
        super.setup()
        this.orm = useService('orm')
        this.notification = useService('notification')
        this.action = useService('action')

        this.state = useState({
            message: ""
        })
        this.updateDropMessage()

        this.imageModelName = this.props.record.data[this.props.name].resModel
    }

    updateDropMessage(countToAdd = 0) {
        const { count } = this.props.record.data[this.props.name]
        const total = count + countToAdd

        let message
        if (total > 1) {
            message = total + ' Images'
        } else if (total === 1) {
            message = '1 Image'
        } else {
            message = 'Drop...'
        }

        this.state.message = message
    }

    async getHighestIndex(productId) {
        const existingImages = await this.orm.searchRead(this.imageModelName, [['product', '=', productId]], ['index']);
        if (!existingImages.length) return -1

        return Math.max(...existingImages.map(record => record.index));

    }


    async onDrop(ev) {
        ev.target.classList.add('drag-over')
        ev.preventDefault()
        ev.stopPropagation()
        if (ev.dataTransfer) {
            const { files } = ev.dataTransfer
            const sortedUploadFiles = [...files].sort((a, b) =>
                a.name.localeCompare(b.name),
            )
            try {
                this.notification.add(`Resizing ${sortedUploadFiles.length} Image(s)`, {
                    title: 'Image(s) resizing.',
                    type: 'success',
                })
                const sortedUploadedImageBase = await Promise.all(
                    sortedUploadFiles.map(async (file) => {
                        if (!(file instanceof Blob)) {
                            throw new Error("The file is not a Blob.")
                        }
                        return await resizeImage(file, 1920, 1920)
                    })
                )
                const highestIndex = await this.getHighestIndex(this.props.record.resId);

                const recordsToSend = sortedUploadedImageBase.map((image, index) => ({
                    product: this.props.record.resId,
                    image_1920: image,
                    index: index + highestIndex + 1,
                }))
                this.notification.add(`Uploading ${recordsToSend.length} Image(s)`, {
                    title: 'Image(s) uploading.',
                    type: 'success',
                })
                await this.batchUpload(recordsToSend)
                this.props.record.load()
                this.notification.add(`${recordsToSend.length} Images uploaded successfully`, {
                    title: 'Images uploaded',
                    type: 'success',
                })

                this.updateDropMessage(recordsToSend.length)

            } catch (error) {
                console.error('Error uploading images:', error)
                this.notification.add('Failed to upload images', {
                    title: 'Error',
                    type: 'danger',
                })
            }
        } else {
            console.error('dataTransfer is not available')
        }
    }

    async batchUpload(records, batchSize = 5, maxConcurrent = 5) {
        const batchPromises = [];
        const activePromises = new Set();  // Track active uploads

        for (let i = 0; i < records.length; i += batchSize) {
            const batch = records.slice(i, i + batchSize);

            const uploadPromise = this.orm.create(this.imageModelName, batch)
                .then((createResult) => {
                    activePromises.delete(uploadPromise);

                    this.notification.add(`${createResult.length} Images uploaded successfully`, {
                        title: 'Success',
                        type: 'success',
                    });

                    this.updateDropMessage(createResult.length);
                })
                .catch((error) => {
                    activePromises.delete(uploadPromise);

                    console.error("Error uploading images:", error);
                    this.notification.add('Failed to upload images', {
                        title: 'Error',
                        type: 'danger',
                    });
                });

            batchPromises.push(uploadPromise);
            activePromises.add(uploadPromise);

            // Wait for an active promise to resolve if limit is reached
            if (activePromises.size >= maxConcurrent) {
                await Promise.race(activePromises);
            }
        }

        await Promise.all(batchPromises);  // Wait for all uploads to finish
    }


    onDragEnter(ev) {
        ev.preventDefault()
        ev.target.classList.remove('drag-over')
    }

    onDragLeave(ev) {
        ev.preventDefault()
        ev.target.classList.add('drag-over')

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
