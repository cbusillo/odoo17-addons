/** @odoo-module **/

const { Component, xml } = owl;
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class OpenRecordButtonWidget extends Component {
  setup() {
    super.setup();
    this.actionService = useService('action');
  }

  async openRecord() {
    await this.actionService.doAction({
      type: 'ir.actions.act_window',
      name: 'Open Record',
      res_model: this.props.model,
      view_mode: 'form',
      views: [[false, 'form']],
      target: 'current',
      res_id: this.props.recordId,
    });
  }
}

OpenRecordButtonWidget.template = xml`<button class="btn btn-primary" t-on-click="openRecord">Open</button>`;
OpenRecordButtonWidget.props = {
  recordId: {type: Number},
  model: {type: String},
};

export const openRecordButton = {
  name: "open_record_button",
  widget: OpenRecordButtonWidget,
};

registry.category("fields").add("open_record_button", OpenRecordButtonWidget);
