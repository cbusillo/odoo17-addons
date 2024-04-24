/** @odoo-module **/
import { FormController } from '@web/views/form/form_controller'
import { registry } from '@web/core/registry'
import { patch } from '@web/core/utils/patch'

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
      // this.env.services.action.doAction({
      //   type: 'ir.actions.server',
      //   name: 'Print Motor Labels',
      //   model: 'motor',
      //   method: 'print_motor_labels',
      //   args: [this.model.root.resId],
      // })
    })
  }
}

registry.category('views').add('motor_form', {
  ...registry.category('views').get('form'),
  Controller: MotorFormController,
})