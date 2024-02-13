#!/bin/bash
set -e

INIT_FILE="init_done.flag"
ODOO_CONFIG_FILE="odoo.dev.cfg"
ODOO_DB_SERVER="localhost"
ODOO_USER="odoo"
ODOO_BIN="../odoo/odoo-bin"
ODOO_RUN="$ODOO_BIN -c $ODOO_CONFIG_FILE --addons-path=../odoo/addons,../odoo/odoo/addons,."
ODOO_SHELL="$ODOO_BIN shell -c $ODOO_CONFIG_FILE --addons-path=../odoo/addons,../odoo/odoo/addons,."

until pg_isready -h "$ODOO_DB_SERVER" -U "$ODOO_USER"; do
  sleep 1
done

if [ ! -f "$INIT_FILE" ]; then
    dropdb -U odoo odoo
    createdb -U odoo odoo
    rm -rf ../filestore

    $ODOO_RUN --stop-after-init -i product_connect
    $ODOO_SHELL --no-http <<EOF
from passlib.context import CryptContext
from odoo import api, SUPERUSER_ID
from odoo.tools import config

db_registry = odoo.modules.registry.Registry(odoo.tools.config['db_name'])
with db_registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.config_parameter'].sudo().set_param('shopify.api_token', config.get('shopify_api_token'))
    env['ir.config_parameter'].sudo().set_param('shopify.shop_url', config.get('shopify_shop_url'))
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
    touch "$INIT_FILE"
fi

start_odoo() {
    if [ $# -eq 0 ]; then
        echo "Starting Odoo in normal mode..."
        eval exec "$ODOO_RUN"
    else
        echo "Executing command: $ODOO_RUN $@"
        eval exec "$ODOO_RUN '$@'"
    fi
}

start_odoo_debug() {
    if [ $# -eq 0 ]; then
        echo "Starting Odoo in debug mode..."
        exec python -m debugpy --listen 0.0.0.0:5678 --wait-for-client "$ODOO_RUN" --dev=all
    else
        echo "Starting Odoo in debug mode with additional arguments: $ODOO_RUN $@"
        exec python -m debugpy --listen 0.0.0.0:5678 --wait-for-client "$ODOO_RUN '$@'" --dev=all
    fi
}

if [ "$ODOO_DEBUG" = "true" ]; then
    start_odoo_debug "$@"
else
    start_odoo "$@"
fi
