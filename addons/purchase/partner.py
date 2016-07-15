# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

<<<<<<< HEAD
    def _purchase_invoice_count(self, cr, uid, ids, field_name, arg, context=None):
        PurchaseOrder = self.pool['purchase.order']
        Invoice = self.pool['account.invoice']
        res = {}

        for partner_id in ids:
            res[partner_id] = {}

            if 'purchase_order_count' in field_name:
                res[partner_id]['purchase_order_count'] = PurchaseOrder.search_count(cr,uid, [('partner_id', 'child_of', partner_id)], context=context)
            if 'supplier_invoice_count' in field_name:
                res[partner_id]['supplier_invoice_count'] = Invoice.search_count(cr,uid, [('partner_id', 'child_of', partner_id), ('type','=','in_invoice')], context=context)

        return res
=======
    @api.multi
    def _purchase_invoice_count(self):
        PurchaseOrder = self.env['purchase.order']
        Invoice = self.env['account.invoice']
        for partner in self:
            partner.purchase_order_count = PurchaseOrder.search_count([('partner_id', 'child_of', partner.id)])
            partner.supplier_invoice_count = Invoice.search_count([('partner_id', 'child_of', partner.id), ('type', '=', 'in_invoice')])
>>>>>>> df6128781645b0295db7169bbb27b434a1ea4bb0

    @api.model
    def _commercial_fields(self):
        return super(res_partner, self)._commercial_fields()

    property_purchase_currency_id = fields.Many2one(
        'res.currency', string="Supplier Currency", company_dependent=True,
        help="This currency will be used, instead of the default one, for purchases from the current partner")
    purchase_order_count = fields.Integer(compute='_purchase_invoice_count', string='# of Purchase Order')
    supplier_invoice_count = fields.Integer(compute='_purchase_invoice_count', string='# Vendor Bills')
