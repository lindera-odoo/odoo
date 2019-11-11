# -*- coding: utf-8 -*-
{
    'name': "Lindera",
    'summary': """
        Contacts/CRM/Promo_Codes""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Lindera Developers",
    'website': "https://www.lindera.de",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'crm'],

    # always loaded
    'data': [
        'security/lindera_security.xml',
        'views/lindera_menu.xml',
        'views/promocode_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
