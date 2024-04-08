/** @odoo-module **/
const {Component, useState} = owl;
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { BadgeSelectionField } from "@web/views/fields/badge_selection/badge_selection_field";
import { FloatField } from "@web/views/fields/float/float_field";
import { CharField } from "@web/views/fields/char/char_field";
import { BinaryField } from "@web/views/fields/binary/binary_field";

const createCustomRecord = (test, selectionOptions, orm, triggerUpdate) => {
  return {
    id: parseInt(test.data.id),
    fields: {
      [test.data.name]: {
        type: 'selection',
        selection: selectionOptions.map(option => [option.value, option.name]),
      },
    },
    data: {
      [test.data.name]: test.data.selection_result || test.data.yes_no_result,
    },
    update: async function (values) {
      const value = Object.values(values)[0];
      let updateData = {};
      updateData[test.data.result_type + "_result"] = value;

      this.data[test.data.name] = value;

      triggerUpdate(test.data.id, updateData);
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
        customRecord = createCustomRecord(test, selectionOptions, this.orm, this.triggerUpdate.bind(this));
      } else if (test.data.result_type === 'yes_no') {
        const selectionOptions = [{name: "Yes", value: "yes"}, {name: "No", value: "no"}];
        customRecord = createCustomRecord(test, selectionOptions, this.orm, this.triggerUpdate.bind(this));
      }

      const section = test.data.section[1];
      if (!this.motorTestsBySection[section]) {
        this.motorTestsBySection[section] = [];
      }
      this.motorTestsBySection[section].push({
        id: test.id,
        odoo_id: test.data.id,
        name: test.data.name,
        result_type: test.data.result_type,
        yes_no_result: test.data.yes_no_result,
        selection_result: test.data.selection_result,
        numeric_result: test.data.numeric_result,
        text_result: test.data.text_result,
        file_result: test.data.file_result,
        custom_record: customRecord,
        record: test,
      });
    }
  }

  async triggerUpdate(testId, updateData) {
    console.log(`triggerUpdate called with testId: ${testId} and updateData:`, updateData);
    const result = await this.orm.call("motor.test", "write", [[testId], updateData]);
    console.log('Result of orm.call:', result);
  }


}

MotorTestWidget.template = "product_connect.MotorTestWidget";
MotorTestWidget.components = {BadgeSelectionField, FloatField, CharField, BinaryField};

export const motorTestWidget = {
  component: MotorTestWidget,
};

registry.category("fields").add("motor_test_widget", motorTestWidget);