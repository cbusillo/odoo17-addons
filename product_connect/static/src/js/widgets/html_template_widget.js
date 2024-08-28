/** @odoo-module **/
import { Component, onWillStart, useState, xml } from "@odoo/owl"
import { useService } from "@web/core/utils/hooks"
import { Dialog } from "@web/core/dialog/dialog"
import { HtmlField, htmlField } from "@web_editor/js/backend/html_field"
import { registry } from "@web/core/registry"

class TagsDialog extends Component {
    static template = 'product_connect.TagsDialog';
    static components = { Dialog };
    static props = {
        close: Function,
        title: String,
        tags: Object,
        onInsertTag: Function,
    };

    setup() {
        this.tags = this.props.tags;
    }

    onTagClick(value) {
        this.props.onInsertTag(value);
        this.props.close();
    }
}

TagsDialog.template = xml`
    <Dialog title="props.title" size="'md'">
        <div class="p-3">
            <t t-foreach="tags" t-as="tag" t-key="tag">
                <button class="btn btn-secondary m-1" t-on-click="() => this.onTagClick(tag)">
                    <t t-esc="tag" />
                </button>
            </t>
        </div>
        <t t-set-slot="footer">
            <button class="btn btn-secondary" t-on-click="props.close">Close</button>
        </t>
    </Dialog>
`;

export class HtmlTemplateWidget extends HtmlField {
    static template = "web_editor.HtmlField"
    static props = {
        ...HtmlField.props,
        propTags: { type: Array, optional: true },
        serverTagModel: { type: String, optional: true },
        serverTagMethod: { type: String, optional: true },
    }

    setup() {
        super.setup()
        this.orm = useService("orm")
        this.dialogService = useService("dialog");
        this.serverTagModel = this.props.serverTagModel || this.props.record.resModel
        this.serverTagMethod = this.props.serverTagMethod || "get_template_tags"
        this.state = useState({
            propTags: this.props.propTags || [],
            tags: [],
        })

        onWillStart(async () => {
            await this.loadTags()
        })
    }

    async loadTags() {
        try {
            const serverTags = await this.orm.call(
                this.serverTagModel,
                this.serverTagMethod,
                [],
            )
            this.state.tags = [...serverTags, ...this.state.propTags]
            console.log("Tags loaded", this.state.tags)
        } catch (error) {
            console.error(`Error while loading tags from ${this.serverTagModel}.${this.serverTagMethod}`, error)
        }
    }

    async startWysiwyg(wysiwyg) {
        await super.startWysiwyg(wysiwyg);

        // Add custom button for inserting tags
        const insertTagsButton = document.createElement('button');
        insertTagsButton.className = 'o_insert_tags_btn btn btn-secondary';
        insertTagsButton.title = 'Insert Tags';
        insertTagsButton.innerHTML = '<i class="fa fa-tags"></i>';
        insertTagsButton.addEventListener('click', this.openTagsDialog.bind(this));

        const buttonGroup = document.createElement('div');
        buttonGroup.className = 'btn-group';
        buttonGroup.appendChild(insertTagsButton);

        // Append the button to the toolbar
        if (this.wysiwyg.toolbarEl) {
            this.wysiwyg.toolbarEl.appendChild(buttonGroup);
        }
    }

    openTagsDialog() {
        this.dialogService.add(TagsDialog, {
            title: "Insert Template Tag",
            tags: this.state.tags,
            onInsertTag: this.insertTag.bind(this),
        });
    }

    insertTag(value) {
        this.wysiwyg.odooEditor.execCommand('insert', `{{ ${value} }}`);
    }
}

export const htmlTemplateWidget = {
    ...htmlField,
    component: HtmlTemplateWidget,
}


registry.category("fields").add("html_template", htmlTemplateWidget)