/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { groupBy, sortBy } from "@web/core/utils/arrays"
import { BadgeSelectionField } from "@web/views/fields/badge_selection/badge_selection_field";
import { FloatField } from "@web/views/fields/float/float_field";
import { CharField } from "@web/views/fields/char/char_field";
import { BinaryField } from "@web/views/fields/binary/binary_field";

export class MotorTestWidget extends Component {
  setup() {
    this.motorTestsBySection = useState({});
    this.selectionFieldDomains = useState({});
    this.orm = useService("orm");

    this.updateMotorTests();
  }

  onPatched() {
    this.updateMotorTests();
  }

  updateMotorTests() {
    const {name, record} = this.props;

    const motorTestsRecords = record.data[name].records;
    this.sortMotorTests(motorTestsRecords);
    this.groupMotorTestsBySection(motorTestsRecords);  
  }

  sortMotorTests(motorTests) {
    sortBy(motorTests, ({data: {section_sequence = Infinity, sequence = 0}}) => section_sequence - sequence);
  }

  groupMotorTestsBySection(motorTests) {
    this.motorTestsBySection = groupBy(motorTests, test => test.data.section[1]);
    for (const tests of Object.values(this.motorTestsBySection)) {
      for (const test of tests) {
        this.setSelectionFieldDomain(test);
      }
    }
  }


  setSelectionFieldDomain({data: {result_type: resultType, selection_options: selectionOptions}, id}) {
    if (resultType === 'selection') {
      this.selectionFieldDomains[id] = [
        ['id', '=', selectionOptions.currentIds],
      ];
    }
  }

  // noinspection JSUnusedGlobalSymbols
  getSelectionFieldDomain(testId) {
    return this.selectionFieldDomains[testId] || false;
  }
}

MotorTestWidget.template = "product_connect.MotorTestWidget";
MotorTestWidget.components = {BadgeSelectionField, FloatField, CharField, BinaryField};

export const motorTestWidget = {
  component: MotorTestWidget,
};

registry.category("fields").add("motor_test_widget", motorTestWidget);