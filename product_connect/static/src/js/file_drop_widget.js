/** @odoo-module **/
const { Component } = owl
import { registry } from '@web/core/registry'
import { binaryField } from '@web/views/fields/binary/binary_field'

export class FileDropWidget extends Component {
    setup() {
        super.setup()
    }

    onDrop(ev) {
        ev.target.classList.add('drag-over')
        ev.target.textContent = 'Drop...'
        ev.preventDefault()
        ev.stopPropagation()
        if (ev.dataTransfer) {
            const { files } = ev.dataTransfer
            const sortedFiles = [...files].sort((a, b) =>
                a.name.localeCompare(b.name),
            )
            sortedFiles.forEach((file, index) => {
                if (file instanceof Blob) {
                    const reader = new FileReader()
                    reader.onload = async (e) => {
                        const { result } = e.target
                        const splitResult = result.split(',')
                        if (splitResult.length > 1) {
                            const baseData = splitResult[1]
                            const imageData = {
                                image: baseData,
                                index: index,
                            }
                            console.log(this.props)
                            this.props.record.update({ [this.props.name]: imageData })
                        } else {
                            console.error('Unable to split result into data and mime type')
                        }
                    }
                    reader.readAsDataURL(file)
                } else {
                    console.error('File is not a Blob')
                }
            })
        } else {
            console.error('dataTransfer is not available')
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

FileDropWidget.template = 'FileDropWidget'

export const fileDropWidget = {
    ...binaryField,
    component: FileDropWidget,
}

registry.category('fields').add('file_drop', fileDropWidget)
