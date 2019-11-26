# odoo
$ git clone https://github.com/odoo/odoo.git
checkout a version 12 branch
needs at least python 3.5

$ sudo apt-get install postgresql postgresql-contrib
might need adding the repository first...

Making postgres user for odoo since default is not allowed
$ sudo -u postgres createuser -s $USER
$ createdb $USER

install requirements of odoo
$ pip3 install -r requirements.txt