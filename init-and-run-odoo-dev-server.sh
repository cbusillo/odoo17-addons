#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

TAILSCALE_PATH="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
FLAG="${1:-}"

set +e  # Temporarily disable 'exit on error'
$TAILSCALE_PATH status > /dev/null 2>&1
INITIAL_STATE=$?
set -e  # Re-enable 'exit on error'

if ! ($TAILSCALE_PATH status > /dev/null 2>&1); then
    echo "Starting Tailscale..."
    $TAILSCALE_PATH up
else
    INITIAL_STATE=0  # Tailscale was already running
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
    $TAILSCALE_PATH down
fi
