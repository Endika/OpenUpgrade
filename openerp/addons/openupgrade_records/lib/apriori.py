""" Encode any known changes to the database here
to help the matching process
"""

renamed_modules = {
<<<<<<< HEAD
    'base_calendar': 'calendar',
    'mrp_jit': 'procurement_jit',
    'project_mrp': 'sale_service',
    # OCA/account-invoicing
    'invoice_validation_wkfl': 'account_invoice_validation_workflow',
    'account_invoice_zero': 'account_invoice_zero_autopay',
    # OCA/server-tools
    'audittrail': 'auditlog',
    # OCA/bank-statement-import
    'account_banking': 'account_bank_statement_import',
    'account_banking_camt': 'account_bank_statement_import_camt',
    'account_banking_mt940':
        'account_bank_statement_import_mt940_base',
    'account_banking_nl_ing_mt940':
        'account_bank_statement_import_mt940_nl_ing',
    'account_banking_nl_rabo_mt940':
        'account_bank_statement_import_mt940_nl_rabo',
=======
    # OCA/product-attribute
    'product_m2m_categories': 'product_multi_category',
    # OCA/e-commerce
    'product_links': 'product_multi_link',
    # OCA/sale-workflow
    'sale_exceptions': 'sale_exception',
    # OCA/partner-contact
    'partner_external_maps': 'partner_external_map',
    # OCA/server-tools
    'disable_openerp_online': 'disable_odoo_online',
    # OCA/runbot-addons
    'runbot_secure': 'runbot_relative',
>>>>>>> df6128781645b0295db7169bbb27b434a1ea4bb0
}

renamed_models = {
}
