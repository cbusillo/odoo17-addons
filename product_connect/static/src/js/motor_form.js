/** @odoo-module **/
import { FormController } from '@web/views/form/form_controller'
import { registry } from '@web/core/registry'

class MotorFormController extends FormController {
  setup() {
    super.setup()
    this.model.hooks.onRecordChanged = (editedRecord, editedField) => {
      const editedData = editedRecord.data
      const editedFieldName = Object.keys(editedField)[0]
      const requiredFieldsToSave = [
        'manufacturer',
        'motor_stroke',
        'motor_configuration',
        'color',
      ]
      const requiredFieldsToPrint = [
        'horsepower',
        'model',
        'serial_number',
        'year',
        ...requiredFieldsToSave,
      ]

      const allPrintFieldsHaveValues = this.allFieldsHaveValues(editedData,
        requiredFieldsToPrint)

      const changedFieldInFieldsToPrint = requiredFieldsToPrint.includes(
        editedFieldName)

      if (allPrintFieldsHaveValues && changedFieldInFieldsToPrint) {
        this.printMotorLabels()
        return
      }

      const allSaveFieldsHaveValues = this.allFieldsHaveValues(editedData,
        requiredFieldsToSave)

      if (allSaveFieldsHaveValues) {
        this.model.root.save()
      }
    }
  }

  allFieldsHaveValues(data, fields) {
    return fields.every(
      field => data[field] !== undefined && data[field] !== null &&
        data[field] !== '' && data[field] !== 0 && data[field] !== false)
  }

  printMotorLabels() {
    this.model.root.save().then(() => {
      this.model.action.doActionButton({
        name: 'print_motor_labels',
        type: 'object',
        resModel: 'motor',
        resId: this.model.root.resId,
        resIds: [this.model.root.resId],
      }).then(() => {
        console.log('Motor labels printed')
      })

    })
  }
}

registry.category('views').add('motor_form', {
  ...registry.category('views').get('form'),
  Controller: MotorFormController,
})