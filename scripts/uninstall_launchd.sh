#!/usr/bin/env bash
# Unload and remove the speedtester launchd agent installed by install_launchd.sh.
set -euo pipefail

LABEL="com.speedtester.agent"
PLIST_DEST="$HOME/Library/LaunchAgents/${LABEL}.plist"

if [[ -f "$PLIST_DEST" ]]; then
    launchctl unload -w "$PLIST_DEST" 2>/dev/null || true
    rm -f "$PLIST_DEST"
    echo "Removed $LABEL ($PLIST_DEST)"
else
    echo "No agent installed at $PLIST_DEST"
fi
