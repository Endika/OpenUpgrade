{
    'name' : 'Odoo Live Support',
    'version': '1.0',
    'summary': 'Chat with the Odoo collaborators',
    'category': 'Tools',
    'complexity': 'medium',
    'website': 'https://www.odoo.com/',
    'description':
        """
Odoo Live Support
=================

Ask your functional question directly to the Odoo Operators with the livechat support.

        """,
    'data': [
        "views/im_odoo_support.xml"
    ],
    'depends' : ["web", "mail"],
    'qweb': [
        'static/src/xml/im_odoo_support.xml'
    ],
    'installable': True,
<<<<<<< HEAD
    'auto_install': False,
    'application': True,
=======
    'auto_install': True,
    'application': False,
>>>>>>> df6128781645b0295db7169bbb27b434a1ea4bb0
}
