/** @odoo-module **/
const {Component, useState} = owl;
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { BadgeSelectionField } from "@web/views/fields/badge_selection/badge_selection_field";
import { FloatField } from "@web/views/fields/float/float_field";
import { CharField } from "@web/views/fields/char/char_field";
import { BinaryField } from "@web/views/fields/binary/binary_field";

export class MotorTestWidget extends Component {
  static props = standardFieldProps;

  setup() {
    super.setup();
    this.motorTestsBySection = useState({});
    this.selectionFieldDomains = useState({});
    this.orm = useService("orm");

    const motorTestsRecords = this.props.record.data[this.props.name].records;
    this.sortMotorTests(motorTestsRecords);
    this.groupMotorTestsBySection(motorTestsRecords);
  }

  sortMotorTests(motorTests) {
    motorTests.sort((a, b) => {
      const sectionSequenceA = a.data.section_sequence || Infinity;
      const sectionSequenceB = b.data.section_sequence || Infinity;
      return sectionSequenceA - sectionSequenceB || (a.data.sequence || 0) - (b.data.sequence || 0);
    });
  }

  groupMotorTestsBySection(motorTests) {
    for (const test of motorTests) {
      this.setSelectionFieldDomain(test);
      this.addTestToSection(test);
    }
    console.log('Motor tests by section:', this.motorTestsBySection);
  }

  setSelectionFieldDomain(test) {
    if (test.data.result_type === 'selection') {
      this.selectionFieldDomains[test.id] = [
        ['id', '=', test.data.selection_options.currentIds],
      ];
      console.log('Selection Field Domain:', this.selectionFieldDomains[test.id]);
    } else {
      console.log('No selection options found for test:', test.data.name);
    }
  }

  addTestToSection(test) {
    const section = test.data.section[1];
    if (!this.motorTestsBySection[section]) {
      this.motorTestsBySection[section] = [];
    }
    this.motorTestsBySection[section].push(test);
    console.log(`Added test ${test} to section ${section}`);
  }

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