#!/bin/bash
set -e

# Wait for Odoo to start up
until pg_isready -h db -U odoo; do
  sleep 1
done


INIT_FILE="/mnt/filestore/init_done.flag"

# Check if initialization has already been done
if [ ! -f "$INIT_FILE" ]; then

    # Wait for Odoo to start up
    until pg_isready -h db -U odoo; do
      sleep 1
    done

    # Run Odoo to initialize the database if needed and start the server
    /opt/odoo/odoo17/odoo-bin --stop-after-init -i product_connect

    # Set system parameters using odoo shell
    /opt/odoo/odoo17/odoo-bin shell -d odoo --no-http -c /etc/odoo/odoo.conf <<EOF
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

start_odoo() {
    if [ $# -eq 0 ]; then
        echo "Starting Odoo in normal mode..."
        exec /opt/odoo/odoo17/odoo-bin -c /etc/odoo/odoo.conf
    else
        echo "Executing command: $@"
        exec "$@"
    fi
}

# Function to start Odoo in debug mode
start_odoo_debug() {
    if [ $# -eq 0 ]; then
        echo "Starting Odoo in debug mode..."
        exec python -m debugpy --listen 0.0.0.0:5678 --wait-for-client /opt/odoo/odoo17/odoo-bin -c /etc/odoo/odoo.conf --dev=all
    else
        echo "Starting Odoo in debug mode with additional arguments: $@"
        # Modify or add the logic here to handle arguments appropriately in debug mode
        exec python -m debugpy --listen 0.0.0.0:5678 --wait-for-client "$@" --dev=all
    fi
}

# Decide whether to start in debug mode or normal mode based on ODOO_DEBUG flag
if [ "$ODOO_DEBUG" = "true" ]; then
    start_odoo_debug "$@"
else
    start_odoo "$@"
fi