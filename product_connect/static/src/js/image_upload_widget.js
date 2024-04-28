/** @odoo-module **/
import { useRef } from '@odoo/owl'
import { registry } from '@web/core/registry'
import { BinaryField } from '@web/views/fields/binary/binary_field'
import { ImageField } from '@web/views/fields/image/image_field'

export class ImageUploadWidget extends BinaryField {


    setup() {
        super.setup()
        this.fileInputRef = useRef('fileInput')

    }

    // noinspection JSUnusedGlobalSymbols
    getPreviewImageSize() {
        const viewportWidth = window.innerWidth
        if (viewportWidth <= 512) {
            return 'image_128'
        } else if (viewportWidth <= 1024) {
            return 'image_256'
        } else if (viewportWidth <= 1920) {
            return 'image_512'
        } else {
            return 'image_1024'
        }
    }

    async onImageUpload() {
        this.fileInputRef.el.click()
    }

    async onFileChange(ev) {
        if (!ev.target.files.length) {
            return
        }
        const file = ev.target.files[0]
        const data = await this.getBaseData(file)
        this.props.record.update({ image_1920: data })
        ev.target.value = null
    }

    // noinspection JSNonCamelCaseFunctionNames
    async getBaseData(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader()
            reader.onload = () => {
                resolve(reader.result.split(',')[1])
            }
            reader.onerror = () => {
                reject(new Error('Failed to read the file'))
            }
            reader.readAsDataURL(file)
        })
    }

    onClick() {
        console.log('ImageUploadWidget.onClick')
        this.onImageUpload().then()
    }
}

ImageUploadWidget.template = 'product_connect.ImageUploadWidget'
ImageUploadWidget.components = { ImageField }

export const imageUploadWidget = { component: ImageUploadWidget }

registry.category('fields').add('image_upload', imageUploadWidget)