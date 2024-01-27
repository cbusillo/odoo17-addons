/** @odoo-module **/
const { xml, Component } = owl;
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class FileDropWidget extends Component {
    setup() {
        super.setup();
    }

    // noinspection JSUnusedGlobalSymbols
    _onDrop(ev) {
        ev.target.classList.remove('drag-over');
        ev.target.textContent = "Drop files here...";
        ev.preventDefault();
        ev.stopPropagation();
        if (ev.dataTransfer) {
            const { files } = ev.dataTransfer;
            const sortedFiles = [...files].sort((a, b) => a.name.localeCompare(b.name));
            sortedFiles.forEach((file, index) => {
                const reader = new FileReader();
                reader.onload = async (e) => {
                    const { result } = e.target;
                    const splitResult = result.split(",");
                    if (splitResult.length > 1) {
                        const base64Data = splitResult[1];
                        // Pass the data as an object including the index
                        this.props.update({ image: base64Data, index: index });
                    } else {
                        console.error("Unable to split result into data and mime type");
                    }
                };
                // noinspection JSCheckFunctionSignatures
                reader.readAsDataURL(file);
            });
        } else {
            console.error("dataTransfer is not available");
        }
    }



    // noinspection JSUnusedGlobalSymbols
    _onDragEnter(ev) {
        ev.preventDefault();
        ev.target.classList.add('drag-over');
        ev.target.textContent = "Release to upload file";
    }

    // noinspection JSUnusedGlobalSymbols
    _onDragLeave(ev) {
        ev.preventDefault();
        ev.target.classList.remove('drag-over');
        ev.target.textContent = "Drop files here...";
    }
    // noinspection JSUnusedGlobalSymbols
    _onDragOver(ev) {
        ev.preventDefault();
    }


}

FileDropWidget.template = xml`
<!--suppress HtmlUnknownAttribute -->
<div class="o_field_file_drop" t-on-drop="_onDrop" t-on-dragover="_onDragOver" t-on-dragenter="_onDragEnter" t-on-dragleave="_onDragLeave" t-att-allowDrop="true">
    Drop files here...
</div>`;

FileDropWidget.props = standardFieldProps;

// Add the field to the correct category
registry.category("fields").add("file_drop", FileDropWidget);

