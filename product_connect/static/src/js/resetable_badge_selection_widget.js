/** @odoo-module **/
import { registry } from '@web/core/registry'
import {
  BadgeSelectionField,
} from '@web/views/fields/badge_selection/badge_selection_field'

export class ResetableBadgeSelectionField extends BadgeSelectionField {
  resetValue() {
    this.props.record.update({ [this.props.name]: false })
  }
}

ResetableBadgeSelectionField.template = 'product_connect.ResetableBadgeSelectionWidget'

export const resetableBadgeSelectionField = { component: ResetableBadgeSelectionField }

registry.category('fields').
  add('resetable_selection_badge', resetableBadgeSelectionField)