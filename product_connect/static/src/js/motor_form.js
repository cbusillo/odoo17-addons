/** @odoo-module **/
import { FormController } from '@web/views/form/form_controller'
import { registry } from '@web/core/registry'

class MotorFormController extends FormController {
  setup() {
    super.setup()

    this.model.hooks.onRecordChanged = (editedRecord, editedFields) => {
      const editedData = editedRecord.data
      const editedFieldNames = Object.keys(editedFields)
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
      ]
      const combinedRequiredFields = [
        ...requiredFieldsToSave,
        ...requiredFieldsToPrint]

      const allPrintFieldsHaveValues = this.allFieldsHaveValues(editedData,
        combinedRequiredFields)

      const changedFieldInFieldsToPrint = requiredFieldsToPrint.some(
        field => editedFieldNames.includes(field))

      const allSaveFieldsHaveValues = this.allFieldsHaveValues(editedData,
        requiredFieldsToSave)

      if (allPrintFieldsHaveValues && allSaveFieldsHaveValues &&
        changedFieldInFieldsToPrint) {
        this.printMotorLabels()
        return
      }

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