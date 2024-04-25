/** @odoo-module **/
import { registry } from '@web/core/registry'
import { ImageField } from '@web/views/fields/image/image_field'

class ImageUploadWidget extends ImageField {
  setup() {
    this.props.reload = false
    super.setup()
  }

  onClick(ev) {
    // ev.stopPropagation()
    console.log(`clicked ${ev}`)
  }
}

ImageUploadWidget.template = 'product_connect.ImageUploadWidget'
ImageUploadWidget.components = { ImageField }

export const imageUploadWidget = {
  component: ImageUploadWidget,
}

registry.category('fields').add('image_upload', imageUploadWidget)