/** @odoo-module **/
import { registry } from '@web/core/registry'
import { BadgeSelectionField, } from '@web/views/fields/badge_selection/badge_selection_field'

export class ResettableBadgeSelectionField extends BadgeSelectionField {
    resetValue() {
        this.props.record.update({ [this.props.name]: false })
    }
}

ResettableBadgeSelectionField.template = 'product_connect.ResettableBadgeSelectionWidget'

export const resettableBadgeSelectionField = { component: ResettableBadgeSelectionField }

registry.category('fields').add('resettable_selection_badge', resettableBadgeSelectionField)