/** @odoo-module **/
const {Component, useState} = owl;
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { BadgeSelectionField } from "@web/views/fields/badge_selection/badge_selection_field";

const createCustomRecord = (test, selectionOptions) => {
  return {
    id: test.id,
    fields: {
      [test.data.name]: {
        type: 'selection',
        selection: selectionOptions.map(option => [option.value, option.name]),
      },
    },
    data: {
      [test.data.name]: test.data.selection_result || test.data.yes_no_result,
    },
    update: function (values) {
      Object.assign(this.data, values);
    },
  };
};

export class MotorTestWidget extends Component {
  static props = standardFieldProps;

  async setup() {
    super.setup();
    this.motorTestsBySection = useState({});
    this.orm = useService("orm");
    let motorTestsRecords = this.props.record.data[this.props.name].records;
    motorTestsRecords.sort((a, b) => {
      // noinspection JSUnresolvedVariable
      const sectionSequenceA = a.data.section_sequence || Infinity;
      // noinspection JSUnresolvedVariable
      const sectionSequenceB = b.data.section_sequence || Infinity;
      return sectionSequenceA - sectionSequenceB || (a.data.sequence || 0) - (b.data.sequence || 0);
    });

    const allSelectionOptions = await this.orm.call("motor.test.selection", "search_read", [], {
      fields: ['name', 'value', 'templates'],
    });

    for (let test of motorTestsRecords) {
      let customRecord = null;
      if (test.data.result_type === 'selection') {
        const selectionOptions = allSelectionOptions.filter(option => option.templates.includes(test.data.template[0]));
        customRecord = createCustomRecord(test, selectionOptions);
      } else if (test.data.result_type === 'yes_no') {
        const selectionOptions = [{name: "Yes", value: "yes"}, {name: "No", value: "no"}];
        customRecord = createCustomRecord(test, selectionOptions);
      }

      const section = test.data.section[1];
      if (!this.motorTestsBySection[section]) {
        this.motorTestsBySection[section] = [];
      }
      this.motorTestsBySection[section].push({
        id: test.id,
        name: test.data.name,
        result_type: test.data.result_type,
        yes_no_result: test.data.yes_no_result,
        selection_result: test.data.selection_result,
        numeric_result: test.data.numeric_result,
        text_result: test.data.text_result,
        file_result: test.data.file_result,
        custom_record: customRecord,
      });
    }
  }

onBadgeSelectionUpdate(value, test) {
  const testIdStr = test.id.toString();
  if (isNaN(parseInt(testIdStr))) {
    console.error(`Invalid test ID: ${testIdStr}`);
    return;
  }
  this.onChangeMotorTestField({
    target: {
      closest: () => ({ getAttribute: () => testIdStr }),
      dataset: { fieldName: test.result_type === 'yes_no' ? 'yes_no_result' : 'selection_result' },
      value: value
    }
  });
}

  async onChangeMotorTestField(event) {
    const testIdStr = event.target.closest('.o_motor_test').getAttribute('data-test-id');
    const testId = parseInt(testIdStr);

    if (isNaN(testId)) {
      console.error(`Invalid test ID: ${testIdStr}`);
      return;
    }

    const fieldName = event.target.dataset.fieldName;
    const value = event.target.value;

    let foundTest = null;
    for (const section of Object.keys(this.motorTestsBySection)) {
      const test = this.motorTestsBySection[section].find(test => test.id === testId);

      if (test) {
        foundTest = test;
        break;
      }
    }

    if (foundTest) {
      // Update the foundTest object
      foundTest[fieldName] = value;

      // Update the custom record if it exists
      if (foundTest.custom_record) {
        foundTest.custom_record.update({[foundTest.name]: value});
      }

      // Save the changes to the database
      await this.orm.write('motor.test', [foundTest.id], {
        [fieldName]: value,
      });

      // Trigger a re-render of the component
      await this.render();
    } else {
      console.error(`Test with id ${testId} not found`);
    }
  }
}

MotorTestWidget.template = "product_connect.MotorTestWidget";
MotorTestWidget.components = {BadgeSelectionField};

export const motorTestWidget = {
  component: MotorTestWidget,
};

registry.category("fields").add("motor_test_widget", motorTestWidget);