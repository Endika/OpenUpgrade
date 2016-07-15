# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from openerp import api, fields, models, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids

    incoterm = fields.Many2one('stock.incoterms', 'Incoterms', help="International Commercial Terms are a series of predefined commercial terms used in international transactions.")
    picking_policy = fields.Selection([
        ('direct', 'Deliver each product when available'),
        ('one', 'Deliver all products at once')],
        string='Shipping Policy', required=True, readonly=True, default='direct',
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=_default_warehouse_id)
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string='Picking associated to this sale')
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')

    @api.multi
    @api.depends('procurement_group_id')
    def _compute_picking_ids(self):
        for order in self:
            order.picking_ids = self.env['stock.picking'].search([('group_id', '=', order.procurement_group_id.id)]) if order.procurement_group_id else []
            order.delivery_count = len(order.picking_ids)

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        if self.warehouse_id.company_id:
            self.company_id = self.warehouse_id.company_id.id

    @api.multi
    def action_view_delivery(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env.ref('stock.action_picking_tree_all')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }

        pick_ids = sum([order.picking_ids.ids for order in self], [])

        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',["+','.join(map(str, pick_ids))+"])]"
        elif len(pick_ids) == 1:
            form = self.env.ref('stock.view_picking_form', False)
            form_id = form.id if form else False
            result['views'] = [(form_id, 'form')]
            result['res_id'] = pick_ids[0]
        return result

    @api.multi
    def action_cancel(self):
        self.order_line.mapped('procurement_ids').cancel()
        super(SaleOrder, self).action_cancel()

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['incoterms_id'] = self.incoterm.id or False
        return invoice_vals

    @api.model
    def _prepare_procurement_group(self):
        res = super(SaleOrder, self)._prepare_procurement_group()
        res.update({'move_type': self.picking_policy, 'partner_id': self.partner_shipping_id.id})
        return res

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_packaging = fields.Many2one('product.packaging', string='Packaging', default=False)
    route_id = fields.Many2one('stock.location.route', string='Route', domain=[('sale_selectable', '=', True)])
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id', string='Product Template', readonly=True)

    @api.multi
    @api.depends('product_id')
    def _compute_qty_delivered_updateable(self):
        for line in self:
            if line.product_id.type not in ('consu', 'product'):
                return super(SaleOrderLine, self)._compute_qty_delivered_updateable()
            line.qty_delivered_updateable = False

    @api.onchange('product_id')
    def _onchange_product_id_set_customer_lead(self):
        self.customer_lead = self.product_id.sale_delay
        return {}

    @api.onchange('product_packaging')
    def _onchange_product_packaging(self):
        if self.product_packaging:
            return self._check_package()
        return {}

    @api.onchange('product_id', 'product_uom_qty')
    def _onchange_product_id_check_availability(self):
        if not self.product_id:
            self.product_packaging = False
            return {}
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        if self.product_id.type == 'product':
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner_id=self.order_id.partner_id.id,
                date_order=self.order_id.date_order,
                pricelist_id=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                warehouse_id=self.order_id.warehouse_id.id
            )
            if float_compare(product.virtual_available, self.product_uom_qty, precision_digits=precision) == -1:
                # Check if MTO, Cross-Dock or Drop-Shipping
                is_available = False
                for route in self.route_id+self.product_id.route_ids:
                    for pull in route.pull_ids:
                        if pull.location_id.id == self.order_id.warehouse_id.lot_stock_id.id:
                            is_available = True
                if not is_available:
                    warning_mess = {
                        'title': _('Not enough inventory!'),
                        'message' : _('You plan to sell %.2f %s but you only have %.2f %s available!\nThe stock on hand is %.2f %s.') % \
                            (self.product_uom_qty, self.product_uom.name or self.product_id.uom_id.name, product.virtual_available, self.product_uom.name or self.product_id.uom_id.name, product.qty_available, self.product_uom.name or self.product_id.uom_id.name)
                    }
                    return {'warning': warning_mess}
        return {}

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        if self.state == 'sale' and self.product_id.type != 'service' and self.product_uom_qty < self._origin.product_uom_qty:
            warning_mess = {
                'title': _('Ordered quantity decreased!'),
                'message' : _('You are decreasing the ordered quantity! Do not forget to manually update the delivery order if needed.'),
            }
            return {'warning': warning_mess}
        return {}

    @api.multi
    def _prepare_order_line_procurement(self, group_id=False):
        vals = super(SaleOrderLine, self)._prepare_order_line_procurement(group_id=group_id)
        date_planned = datetime.strptime(self.order_id.date_order, DEFAULT_SERVER_DATETIME_FORMAT)\
            + timedelta(days=self.customer_lead or 0.0) - timedelta(days=self.order_id.company_id.security_lead)
        vals.update({
            'date_planned': date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'location_id': self.order_id.partner_shipping_id.property_stock_customer.id,
            'route_ids': self.route_id and [(4, self.route_id.id)] or [],
            'warehouse_id': self.order_id.warehouse_id and self.order_id.warehouse_id.id or False,
            'partner_dest_id': self.order_id.partner_shipping_id.id,
            'sale_line_id': self.id,
        })
        return vals

    @api.multi
    def _get_delivered_qty(self):
        self.ensure_one()
        super(SaleOrderLine, self)._get_delivered_qty()
        qty = 0.0
        for move in self.procurement_ids.mapped('move_ids').filtered(lambda r: r.state == 'done' and not r.scrapped):
            if move.location_dest_id.usage == "customer":
                qty += self.env['product.uom']._compute_qty_obj(move.product_uom, move.product_uom_qty, self.product_uom)
        return qty

    @api.multi
    def _check_package(self):
        default_uom = self.product_id.uom_id
        pack = self.product_packaging
        qty = self.product_uom_qty
        q = self.env['product.uom']._compute_qty_obj(default_uom, pack.qty, self.product_uom)
        if qty and q and (qty % q):
            newqty = qty - (qty % q) + q
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _("This product is packaged by %d . You should sell %d .") % (pack.qty, newqty),
                },
            }
        return {}


class StockLocationRoute(models.Model):
    _inherit = "stock.location.route"

    sale_selectable = fields.Boolean(string="Selectable on Sales Order Line")


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

<<<<<<< HEAD
    _columns = {
        'product_packaging': fields.many2one('product.packaging', 'Packaging'),
        'number_packages': fields.function(_number_packages, type='integer', string='Number Packages'),
        'route_id': fields.many2one('stock.location.route', 'Route', domain=[('sale_selectable', '=', True)]),
        'product_tmpl_id': fields.related('product_id', 'product_tmpl_id', type='many2one', relation='product.template', string='Product Template'),
    }

    _defaults = {
        'product_packaging': False,
    }

    def product_packaging_change(self, cr, uid, ids, pricelist, product, qty=0, uom=False,
                                   partner_id=False, packaging=False, flag=False, context=None):
        if not product:
            return {'value': {'product_packaging': False}}
        product_obj = self.pool.get('product.product')
        product_uom_obj = self.pool.get('product.uom')
        pack_obj = self.pool.get('product.packaging')
        warning = {}
        result = {}
        warning_msgs = ''
        if flag:
            res = self.product_id_change(cr, uid, ids, pricelist=pricelist,
                    product=product, qty=qty, uom=uom, partner_id=partner_id,
                    packaging=packaging, flag=False, context=context)
            warning_msgs = res.get('warning') and res['warning'].get('message', '') or ''

        products = product_obj.browse(cr, uid, product, context=context)
        if not products.packaging_ids:
            packaging = result['product_packaging'] = False

        if packaging:
            default_uom = products.uom_id and products.uom_id.id
            pack = pack_obj.browse(cr, uid, packaging, context=context)
            q = product_uom_obj._compute_qty(cr, uid, uom, pack.qty, default_uom)
#            qty = qty - qty % q + q
            if qty and (q and not (qty % q) == 0):
                ean = pack.ean or _('(n/a)')
                qty_pack = pack.qty
                type_ul = pack.ul
                if not warning_msgs:
                    warn_msg = _("You selected a quantity of %d Units.\n"
                                "But it's not compatible with the selected packaging.\n"
                                "Here is a proposition of quantities according to the packaging:\n"
                                "EAN: %s Quantity: %s Type of ul: %s") % \
                                    (qty, ean, qty_pack, type_ul.name)
                    warning_msgs += _("Picking Information ! : ") + warn_msg + "\n\n"
                warning = {
                       'title': _('Configuration Error!'),
                       'message': warning_msgs
                }
            result['product_uom_qty'] = qty

        return {'value': result, 'warning': warning}

    def _check_routing(self, cr, uid, ids, product, warehouse_id, context=None):
        """ Verify the route of the product based on the warehouse
            return True if the product availibility in stock does not need to be verified
        """
        is_available = False
        if warehouse_id:
            warehouse = self.pool['stock.warehouse'].browse(cr, uid, warehouse_id, context=context)
            for product_route in product.route_ids:
                if warehouse.mto_pull_id and warehouse.mto_pull_id.route_id and warehouse.mto_pull_id.route_id.id == product_route.id:
                    is_available = True
                    break
        else:
            try:
                mto_route_id = self.pool['stock.warehouse']._get_mto_route(cr, uid, context=context)
            except osv.except_osv:
                # if route MTO not found in ir_model_data, we treat the product as in MTS
                mto_route_id = False
            if mto_route_id:
                for product_route in product.route_ids:
                    if product_route.id == mto_route_id:
                        is_available = True
                        break
        if not is_available:
            product_routes = product.route_ids + product.categ_id.total_route_ids
            for pull_rule in product_routes.mapped('pull_ids'):
                if pull_rule.picking_type_id.sudo().default_location_src_id.usage == 'supplier' and\
                        pull_rule.picking_type_id.sudo().default_location_dest_id.usage == 'customer':
                    is_available = True
                    break
        return is_available

    def product_id_change_with_wh(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False, context=None):
        context = context or {}
        product_uom_obj = self.pool.get('product.uom')
        product_obj = self.pool.get('product.product')
        warning = {}
        #UoM False due to hack which makes sure uom changes price, ... in product_id_change
        res = self.product_id_change(cr, uid, ids, pricelist, product, qty=qty,
            uom=False, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)

        if not product:
            res['value'].update({'product_packaging': False})
            return res

        # set product uom in context to get virtual stock in current uom
        if 'product_uom' in res.get('value', {}):
            # use the uom changed by super call
            context = dict(context, uom=res['value']['product_uom'])
        elif uom:
            # fallback on selected
            context = dict(context, uom=uom)

        #update of result obtained in super function
        product_obj = product_obj.browse(cr, uid, product, context=context)
        res['value'].update({'product_tmpl_id': product_obj.product_tmpl_id.id, 'delay': (product_obj.sale_delay or 0.0)})

        # Calling product_packaging_change function after updating UoM
        res_packing = self.product_packaging_change(cr, uid, ids, pricelist, product, qty, uom, partner_id, packaging, context=context)
        res['value'].update(res_packing.get('value', {}))
        warning_msgs = res_packing.get('warning') and res_packing['warning']['message'] or ''

        if product_obj.type == 'product':
            #determine if the product needs further check for stock availibility
            is_available = self._check_routing(cr, uid, ids, product_obj, warehouse_id, context=context)

            #check if product is available, and if not: raise a warning, but do this only for products that aren't processed in MTO
            if not is_available:
                uom_record = False
                if uom:
                    uom_record = product_uom_obj.browse(cr, uid, uom, context=context)
                    if product_obj.uom_id.category_id.id != uom_record.category_id.id:
                        uom_record = False
                if not uom_record:
                    uom_record = product_obj.uom_id
                compare_qty = float_compare(product_obj.virtual_available, qty, precision_rounding=uom_record.rounding)
                if compare_qty == -1:
                    warn_msg = _('You plan to sell %.2f %s but you only have %.2f %s available !\nThe real stock is %.2f %s. (without reservations)') % \
                        (qty, uom_record.name,
                         max(0,product_obj.virtual_available), uom_record.name,
                         max(0,product_obj.qty_available), uom_record.name)
                    warning_msgs += _("Not enough stock ! : ") + warn_msg + "\n\n"

        #update of warning messages
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        res.update({'warning': warning})
        return res
=======
    incoterms_id = fields.Many2one('stock.incoterms', string="Incoterms",
        help="Incoterms are series of sales terms. They are used to divide transaction costs and responsibilities between buyer and seller and reflect state-of-the-art transportation practices.",
        readonly=True, states={'draft': [('readonly', False)]})
>>>>>>> df6128781645b0295db7169bbb27b434a1ea4bb0


class ProcurementOrder(models.Model):
    _inherit = "procurement.order"

    @api.model
    def _run_move_create(self, procurement):
        vals = super(ProcurementOrder, self)._run_move_create(procurement)
        if self.sale_line_id:
            vals.update({'sequence': self.sale_line_id.sequence})
        return vals

<<<<<<< HEAD
class stock_picking(osv.osv):
    _inherit = "stock.picking"

    def _get_partner_to_invoice(self, cr, uid, picking, context=None):
        """ Inherit the original function of the 'stock' module
            We select the partner of the sales order as the partner of the customer invoice
        """
        if context.get('inv_type') and context['inv_type'] in ('out_invoice', 'out_refund'):
            if picking.sale_id:
                saleorder_ids = self.pool['sale.order'].search(cr, uid, [('procurement_group_id' ,'=', picking.group_id.id)], context=context)
                saleorders = self.pool['sale.order'].browse(cr, uid, saleorder_ids, context=context)
                if saleorders and saleorders[0] and saleorders[0].order_policy == 'picking':
                    saleorder = saleorders[0]
                    return saleorder.partner_invoice_id.id
        return super(stock_picking, self)._get_partner_to_invoice(cr, uid, picking, context=context)
    
    def _get_sale_id(self, cr, uid, ids, name, args, context=None):
        sale_obj = self.pool.get("sale.order")
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = False
            if picking.group_id:
                sale_ids = sale_obj.search(cr, uid, [('procurement_group_id', '=', picking.group_id.id)], context=context)
                if sale_ids:
                    res[picking.id] = sale_ids[0]
        return res
    
    _columns = {
        'sale_id': fields.function(_get_sale_id, type="many2one", relation="sale.order", string="Sale Order"),
    }

    def _create_invoice_from_picking(self, cr, uid, picking, vals, context=None):
        sale_obj = self.pool.get('sale.order')
        sale_line_obj = self.pool.get('sale.order.line')
        invoice_line_obj = self.pool.get('account.invoice.line')
        invoice_id = super(stock_picking, self)._create_invoice_from_picking(cr, uid, picking, vals, context=context)
        return invoice_id

    def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
        inv_vals = super(stock_picking, self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)
        sale = move.picking_id.sale_id
        if sale and inv_type in ('out_invoice', 'out_refund'):
            inv_vals.update({
                'fiscal_position': sale.fiscal_position.id,
                'payment_term': sale.payment_term.id,
                'user_id': sale.user_id.id,
                'section_id': sale.section_id.id,
                'name': sale.client_order_ref or '',
                'comment': sale.note,
                })
        return inv_vals
=======

class StockMove(models.Model):
    _inherit = "stock.move"

    @api.multi
    def action_done(self):
        result = super(StockMove, self).action_done()

        # Update delivered quantities on sale order lines
        todo = self.env['sale.order.line']
        for move in self:
            if (move.procurement_id.sale_line_id) and (move.product_id.invoice_policy in ('order', 'delivery')):
                todo |= move.procurement_id.sale_line_id
        for line in todo:
            line.qty_delivered = line._get_delivered_qty()
        return result


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.depends('move_lines')
    def _compute_sale_id(self):
        for picking in self:
            sale_order = False
            for move in picking.move_lines:
                if move.procurement_id.sale_line_id:
                    sale_order = move.procurement_id.sale_line_id.order_id
                    break
            picking.sale_id = sale_order.id if sale_order else False

    sale_id = fields.Many2one(comodel_name='sale.order', string="Sale Order", compute='_compute_sale_id')


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    def _get_anglo_saxon_price_unit(self):
        price_unit = super(AccountInvoiceLine,self)._get_anglo_saxon_price_unit()
        # in case of anglo saxon with a product configured as invoiced based on delivery, with perpetual
        # valuation and real price costing method, we must find the real price for the cost of good sold
        uom_obj = self.env['product.uom']
        if self.product_id.invoice_policy == "delivery":
            for s_line in self.sale_line_ids:
                # qtys already invoiced
                qty_done = sum([uom_obj._compute_qty_obj(x.uom_id, x.quantity, x.product_id.uom_id) for x in s_line.invoice_lines if x.invoice_id.state in ('open', 'paid')])
                quantity = uom_obj._compute_qty_obj(self.uom_id, self.quantity, self.product_id.uom_id)
                # Put moves in fixed order by date executed
                moves = self.env['stock.move']
                for procurement in s_line.procurement_ids:
                    moves |= procurement.move_ids
                moves.sorted(lambda x: x.date)
                # Go through all the moves and do nothing until you get to qty_done
                # Beyond qty_done we need to calculate the average of the price_unit
                # on the moves we encounter.
                average_price_unit = 0
                qty_delivered = 0
                invoiced_qty = 0
                for move in moves:
                    if move.state != 'done':
                        continue
                    invoiced_qty += move.product_qty
                    if invoiced_qty <= qty_done:
                        continue
                    qty_to_consider = move.product_qty
                    if invoiced_qty - move.product_qty < qty_done:
                        qty_to_consider = invoiced_qty - qty_done
                    qty_to_consider = min(qty_to_consider, quantity - qty_delivered)
                    qty_delivered += qty_to_consider
                    average_price_unit = (average_price_unit * (qty_delivered - qty_to_consider) + move.price_unit * qty_to_consider) / qty_delivered
                    if qty_delivered == quantity:
                        break
                price_unit = average_price_unit or price_unit
                price_unit = uom_obj._compute_qty_obj(self.uom_id, price_unit, self.product_id.uom_id)
        return price_unit
>>>>>>> df6128781645b0295db7169bbb27b434a1ea4bb0
