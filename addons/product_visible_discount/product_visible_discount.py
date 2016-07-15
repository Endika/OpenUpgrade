# -*- encoding: utf-8 -*-
<<<<<<< HEAD
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import SUPERUSER_ID
=======
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api
>>>>>>> df6128781645b0295db7169bbb27b434a1ea4bb0
from openerp.osv import fields, osv
from openerp.tools.translate import _

class product_pricelist(osv.osv):
    _inherit = 'product.pricelist'

    _columns = {
        'discount_policy': fields.selection([('with_discount', 'Discount included in the price'), ('without_discount', 'Show discount in the sale order')], string="Discount Policy"),
    }
    _defaults = {'discount_policy': 'with_discount'}


class sale_order_line(osv.osv):
    _inherit = "sale.order.line"

    def _get_real_price_currency(self, cr, uid, product_id, res_dict, qty, uom, pricelist, context=None):
        """Retrieve the price before applying the pricelist"""
        item_obj = self.pool['product.pricelist.item']
        product_obj = self.pool['product.product']
        field_name = 'list_price'
        currency_id = None
        if res_dict.get(pricelist):
            rule_id = res_dict[pricelist][1]
        else:
            rule_id = False
        if rule_id:
            item = item_obj.browse(cr, uid, rule_id, context=context)
            if item.base == 'standard_price':
                field_name = 'standard_price'
            currency_id = item.pricelist_id.currency_id.id

        product = product_obj.browse(cr, uid, product_id, context=context)
        if not currency_id:
            currency_id = product.company_id.currency_id.id
        factor = 1.0
        if uom and uom != product.uom_id.id:
            # the unit price is in a different uom
            factor = self.pool['product.uom']._compute_price(cr, uid, uom, 1.0, product.uom_id.id)
        return product[field_name] * factor, currency_id

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(sale_order_line, self).product_id_change()
        for line in self:
            context_partner = dict(self.env.context, partner_id=line.order_id.partner_id.id)
            if line.product_id and line.order_id.pricelist_id and self.env.user.has_group('sale.group_discount_per_so_line'):
                pricelist_context = dict(context_partner, uom=line.product_uom.id, date=line.order_id.date_order)
                list_price = line.order_id.pricelist_id.with_context(pricelist_context).price_rule_get(line.product_id.id, line.product_uom_qty or 1.0, line.order_id.partner_id)

<<<<<<< HEAD
        context = {'lang': lang, 'partner_id': partner_id}
        result=res['value']
        pricelist_obj=self.pool.get('product.pricelist')
        product_obj = self.pool.get('product.product')
        account_tax_obj = self.pool.get('account.tax')
        if product and pricelist and self.pool.get('res.users').has_group(cr, uid, 'sale.group_discount_per_so_line'):
            if result.get('price_unit',False):
                price=result['price_unit']
=======
                new_list_price, currency_id = line.with_context(context_partner)._get_real_price_currency(line.product_id.id, list_price, line.product_uom_qty, line.product_uom.id, line.order_id.pricelist_id.id)
                if line.order_id.pricelist_id.discount_policy == 'without_discount' and list_price[line.order_id.pricelist_id.id][0] != 0 and new_list_price != 0:
                    if line.product_id.company_id and line.order_id.pricelist_id.currency_id.id != line.product_id.company_id.currency_id.id:
                        # new_list_price is in company's currency while price in pricelist currency
                        ctx = dict(context_partner, date=self.order_id.date_order)
                        new_list_price = self.env['res.currency'].browse(currency_id).with_context(ctx).compute(new_list_price, line.order_id.pricelist_id.currency_id.id)
                    discount = (new_list_price - line.price_unit) / new_list_price * 100
                    if discount > 0:
                        line.price_unit = new_list_price
                        line.discount = discount
                    else:
                        line.discount = 0.0
                else:
                    line.discount = 0.0
>>>>>>> df6128781645b0295db7169bbb27b434a1ea4bb0
            else:
                line.discount = 0.0
        return res

<<<<<<< HEAD
            new_list_price, currency_id = get_real_price_curency(list_price, product.id, qty, uom, pricelist)

            # The superuser is used by website_sale in order to create a sale order. We need to make
            # sure we only select the taxes related to the company of the partner. This should only
            # apply if the partner is linked to a company.
            if uid == SUPERUSER_ID and context.get('company_id'):
                taxes = product.taxes_id.filtered(lambda r: r.company_id.id == context['company_id'])
            else:
                taxes = product.taxes_id
            new_list_price = account_tax_obj._fix_tax_included_price(cr, uid, new_list_price, taxes, result.get('tax_id', []))

            if so_pricelist.visible_discount and list_price[pricelist][0] != 0 and new_list_price != 0:
                if product.company_id and so_pricelist.currency_id.id != product.company_id.currency_id.id:
=======
    @api.onchange('product_uom')
    def product_uom_change(self):
        res = super(sale_order_line, self).product_uom_change()
        if not self.product_uom:
            self.price_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id and self.env.user.has_group('sale.group_discount_per_so_line'):
            context_partner = dict(self.env.context, partner_id=self.order_id.partner_id.id)
            pricelist_context = dict(context_partner, uom=self.product_uom.id, date=self.order_id.date_order)
            list_price = self.order_id.pricelist_id.with_context(pricelist_context).price_rule_get(self.product_id.id, self.product_uom_qty or 1.0, self.order_id.partner_id)
            new_list_price, currency_id = self.with_context(context_partner)._get_real_price_currency(self.product_id.id, list_price, self.product_uom_qty, self.product_uom.id, self.order_id.pricelist_id.id)
            if self.order_id.pricelist_id.discount_policy == 'without_discount' and list_price[self.order_id.pricelist_id.id][0] != 0 and new_list_price != 0:
                if self.product_id.company_id and self.order_id.pricelist_id.currency_id.id != self.product_id.company_id.currency_id.id:
>>>>>>> df6128781645b0295db7169bbb27b434a1ea4bb0
                    # new_list_price is in company's currency while price in pricelist currency
                    ctx = dict(context_partner, date=self.order_id.date_order)
                    new_list_price = self.env['res.currency'].browse(currency_id).with_context(ctx).compute(new_list_price, self.order_id.pricelist_id.currency_id.id)
                discount = (new_list_price - self.price_unit) / new_list_price * 100
                if discount > 0:
                    self.price_unit = new_list_price
                    self.discount = discount
                else:
                    self.discount = 0.0
            else:
                self.discount = 0.0
        else:
            self.discount = 0.0
        return res
