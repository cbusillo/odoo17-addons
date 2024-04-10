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

  updateMotorTests() {
    const {name, record} = this.props;

    const motorTestsRecords = record.data[name].records;
    const missingParts = record.data.parts.records.filter(part => part.data.missing);

    // Filter out hidden tests based on missing parts
    const visibleTests = motorTestsRecords.filter(test => {
      const hiddenByParts = missingParts.some(part =>
        part.data.hidden_tests.records.some(hiddenTest =>
          hiddenTest.data.id === test.data.template[0]
        )
      );
      return !hiddenByParts;
    });

    // Add or remove tests based on previous test results
    const conditionalTests = visibleTests.flatMap(test => {
      const result = test.data[`${test.data.result_type}_result`];
      return test.data.conditional_tests.records.filter(conditionalTest =>
        this.evaluateCondition(result, conditionalTest)
      );
    });

    const finalTests = [...visibleTests, ...conditionalTests];
    this.sortMotorTests(finalTests);
    this.groupMotorTestsBySection(finalTests);
  }

  evaluateCondition(result, test) {
    const conditions = test.data.conditions.records;
    const resultType = test.data.result_type;

    for (const condition of conditions) {
      const {condition_value: conditionValue, action_type: actionType, conditional_test: conditionalTest} = condition.data;

      let conditionMet = false;

      if (resultType === "selection") {
        conditionMet = result.toLowerCase() === conditionValue.toLowerCase();
      } else if (resultType === "numeric") {
        // Perform numeric comparison based on your requirements
        // For example, checking if the result is greater than the condition value
        conditionMet = parseFloat(result) > parseFloat(conditionValue);
      } else if (resultType === "yes_no") {
        conditionMet = result.toLowerCase() === conditionValue.toLowerCase();
      }

      if (conditionMet) {
        const conditionalTestId = conditionalTest.data.id;
        const conditionalTestInstance = this.env.model.root.data.tests.records.find(
          (t) => t.data.template.data.id === conditionalTestId
        );

        if (conditionalTestInstance) {
          conditionalTestInstance.data.is_applicable = actionType === "show";
        }
      }
    }
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