/** @odoo-module **/
import { FormController } from '@web/views/form/form_controller'
import { registry } from '@web/core/registry'

class MotorFormController extends FormController {
  setup() {
    super.setup()
  }

  async onchangeSave() {
    if (this.props.record.isDirty()) {
      await this.props.record.save()
      await this.props.record.load()
    }
  }

}

registry.category('views').add('motor_form', {
  ...registry.category('views').get('form'),
  Controller: MotorFormController,
})