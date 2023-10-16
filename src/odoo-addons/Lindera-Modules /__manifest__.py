# -*- coding: utf-8 -*-
{
    'name': "Lindera",
    'summary': """
        Lindera intern Module""",

    'description': """
        Backend Integration
        Ofice365 Integration
        and various other things
    """,

    'author': "Lindera Developers",
    'website': "https://www.lindera.de",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'crm', 'sale', 'sale_subscription'],

    # always loaded
    'data': [
        'security/lindera_security.xml',
        'security/ir.model.access.csv',
        'views/lindera_menu.xml',
        'views/promocode_view.xml',
        'views/office_auth.xml',
        'views/office_mail.xml',
        'views/home.xml',
        'views/lead.xml',
        'views/stage.xml',
        'views/subscription.xml',
        'data/scheduler.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
