#!/bin/bash
set -e

# Wait for Odoo to start up
until pg_isready -h db -U odoo; do
  sleep 1
done


INIT_FILE="/var/lib/odoo/init_done.flag"

# Check if initialization has already been done
if [ ! -f "$INIT_FILE" ]; then

    # Wait for Odoo to start up
    until pg_isready -h db -U odoo; do
      sleep 1
    done

    # Run Odoo to initialize the database if needed and start the server
    odoo --stop-after-init -i product_connect

    # Set system parameters using odoo shell
    odoo shell -d odoo --no-http -c /etc/odoo/odoo.conf <<EOF
from passlib.context import CryptContext
from odoo import api, SUPERUSER_ID
from odoo.tools import config

db_registry = odoo.modules.registry.Registry(odoo.tools.config['db_name'])
with db_registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.config_parameter'].sudo().set_param('shopify.api_token', config.get('shopify_api_token'))
    env['ir.config_parameter'].sudo().set_param('shopify.shop_url', config.get('shopify_url'))
    admin_user = config.get('default_admin_user')
    admin_password = config.get('default_admin_passwd')

    if admin_password:
        pwd_context = CryptContext(schemes=["pbkdf2_sha512"], deprecated="auto")
        admin_password_hashed = pwd_context.hash(admin_password)
        cr.execute("UPDATE res_users SET password=%s WHERE login='admin'", (admin_password_hashed,))

    if admin_user:
        cr.execute("UPDATE res_users SET login=%s WHERE login='admin'", (admin_user,))

    cr.commit()
EOF

    # Mark initialization as done
    touch "$INIT_FILE"
fi

# Start Odoo normally
exec "$@"
