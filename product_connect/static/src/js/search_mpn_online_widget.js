/** @odoo-module **/
import { registry } from '@web/core/registry'
import { CharField, charField } from '@web/views/fields/char/char_field'

export class SearchMpnOnlineWidget extends CharField {
  searchOnline() {
    const mpns = this.props.record.data[this.props.name]
    if (!mpns) {
      alert('No MPN entered')
      return
    }
    const mpnArray = mpns.split(',').map((mpn) => mpn.trim())
    for (const mpn of mpnArray) {
      window.open(`https://www.ebay.com/sch/i.html?_nkw=${mpn}`, '_blank')
      window.open(`https://www.google.com/search?q=${mpn}`, '_blank')
    }
  }
}

SearchMpnOnlineWidget.template = 'SearchMpnOnlineWidget'

export const searchMpnOnline = {
  ...charField,
  component: SearchMpnOnlineWidget,
}

registry.category('fields').add('search_mpn_online', searchMpnOnline)
