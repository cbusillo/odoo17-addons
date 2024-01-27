/** @odoo-module **/
const { xml } = owl;
import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";


export class SearchMpnOnlineWidget extends CharField {

    // noinspection JSUnusedGlobalSymbols
    searchOnline() {
        const mpns = this.props.value;
        const mpn = mpns.split(',')[0].trim();
        window.open(`https://www.ebay.com/sch/i.html?_nkw=${mpn}`, '_blank');
        window.open(`https://www.google.com/search?q=${mpn}`, '_blank');
    }
}

SearchMpnOnlineWidget.template = xml`
<t t-name="web.SearchMpnOnlineWidget" owl="1">
    <t t-if="props.readonly">
        <span t-esc="formattedValue" />
    </t>
    <t t-else="">
        <!--suppress HtmlUnknownAttribute -->
        <button t-on-click="searchOnline" tabindex="-1">S</button>
        <!--suppress HtmlUnknownAttribute -->
            <input 
            class="o_input" 
            t-att-class="{'o_field_translate': props.isTranslatable}" 
            t-att-id="props.id" 
            t-att-type="props.isPassword ? 'password' : 'text'" 
            t-att-autocomplete="props.autocomplete or (props.isPassword ? 'new-password' : 'off')" 
            t-att-maxlength="props.maxLength > 0 and props.maxLength" 
            t-att-placeholder="props.placeholder"
            t-ref="input" 
        />
        <t t-if="props.isTranslatable">
            <TranslationButton 
                fieldName="props.name" 
                record="props.record"
            />
        </t>
    </t>
</t>`;

registry.category("fields").add("search_mpn_online", SearchMpnOnlineWidget);