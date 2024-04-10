#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

TAILSCALE_PATH="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
FLAG="${1:-}"

is_tailscale_up() {
    $TAILSCALE_PATH status > /dev/null 2>&1
    return $?
}

INITIAL_STATE=$(is_tailscale_up || echo 0)

if (( INITIAL_STATE != 0 )); then
    echo "Starting Tailscale..."
    sudo $TAILSCALE_PATH up
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ -z "$CURRENT_BRANCH" ]; then
    echo "Error: Cannot find the current Git branch. Are you in a Git repository?"
    exit 1
fi

ssh opw-dev "bash -s" -- "$FLAG" "$CURRENT_BRANCH" << 'EOF'
FLAG=$1
CURRENT_BRANCH=$2

cd /opt/odoo/odoo17-addons
service odoo stop

git pull origin $CURRENT_BRANCH
if [ "$FLAG" = "init" ]; then
    rm -f init-done.flag
    ./init-and-run-odoo-dev.sh sync-prod testing
fi

service odoo start
EOF

if [ "$INITIAL_STATE" -ne 0 ]; then
    echo "Stopping Tailscale..."
    sudo $TAILSCALE_PATH down
fi
