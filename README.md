# odoo
$ git clone https://github.com/odoo/odoo.git
checkout a version 12 branch
needs at least python 3.5

$ sudo apt-get install postgresql postgresql-contrib
might need adding the repository first...

Making postgres user for odoo since default is not allowed
$ sudo -u postgres createuser -s $USER
$ createdb $USER

install requirements of odoo. Don't try to do it via conda/pycharm... the requirements mess up the python version for whatever reason
$ sudo apt-get install libsasl2-dev python-dev libldap2-dev libssl-dev
$ pip3 install -r requirements.txt
do the same for the requirements of lindera-odoo-integration

Needed System Parameter, that need to be set in Odoo!
'lindera.backend'
'lindera.internal_authentication_token'
'lindera.raven_client'
'lindera.client_id'
'lindera.client_secret'
'lindera.callback_url'