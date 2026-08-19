#!/usr/bin/env bash
# Install a per-user launchd agent that runs speedtester.py in the background
# on macOS, independent of any IDE or terminal session.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "launchd is macOS-only. On Linux, use a systemd timer or cron; on" >&2
    echo "Windows, use Task Scheduler, running: python speedtester.py --once" >&2
    exit 1
fi

INTERVAL_MINUTES=15
CSV_PATH=""
SERVER_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --interval)
            INTERVAL_MINUTES="$2"
            shift 2
            ;;
        --csv)
            CSV_PATH="$2"
            shift 2
            ;;
        --server-id)
            SERVER_ID="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: $0 [--interval MINUTES] [--csv PATH] [--server-id ID]" >&2
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
SCRIPT_PATH="$PROJECT_DIR/speedtester.py"
TEMPLATE="$PROJECT_DIR/launchd/com.speedtester.agent.plist.template"
LABEL="com.speedtester.agent"
PLIST_DEST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$PROJECT_DIR/logs"

if [[ -z "$CSV_PATH" ]]; then
    CSV_PATH="$PROJECT_DIR/speedtest_log.csv"
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "No virtualenv found at $PROJECT_DIR/.venv" >&2
    echo "Run this first:" >&2
    echo "  python3 -m venv \"$PROJECT_DIR/.venv\"" >&2
    exit 1
fi

if ! command -v speedtest >/dev/null 2>&1; then
    echo "Warning: the 'speedtest' CLI isn't on PATH. Install it with:" >&2
    echo "  brew tap teamookla/speedtest && brew install speedtest" >&2
fi

INTERVAL_SECONDS=$(( INTERVAL_MINUTES * 60 ))
mkdir -p "$LOG_DIR"

sed \
    -e "s#__LABEL__#${LABEL}#g" \
    -e "s#__PYTHON_BIN__#${PYTHON_BIN}#g" \
    -e "s#__SCRIPT_PATH__#${SCRIPT_PATH}#g" \
    -e "s#__CSV_PATH__#${CSV_PATH}#g" \
    -e "s#__WORKING_DIR__#${PROJECT_DIR}#g" \
    -e "s#__INTERVAL_SECONDS__#${INTERVAL_SECONDS}#g" \
    -e "s#__LOG_OUT__#${LOG_DIR}/speedtester.out.log#g" \
    -e "s#__LOG_ERR__#${LOG_DIR}/speedtester.err.log#g" \
    "$TEMPLATE" > "$PLIST_DEST.tmp"

if [[ -n "$SERVER_ID" ]]; then
    sed -e "s#__SERVER_ID_ARG__#--server-id=${SERVER_ID}#g" "$PLIST_DEST.tmp" > "$PLIST_DEST"
else
    sed "/__SERVER_ID_ARG__/d" "$PLIST_DEST.tmp" > "$PLIST_DEST"
fi
rm -f "$PLIST_DEST.tmp"

plutil -lint "$PLIST_DEST"

if launchctl list | grep -q "$LABEL"; then
    launchctl unload -w "$PLIST_DEST" || true
fi
launchctl load -w "$PLIST_DEST"

echo "Installed and loaded $LABEL (every $INTERVAL_MINUTES min)."
echo "Plist:  $PLIST_DEST"
echo "CSV:    $CSV_PATH"
echo "Logs:   $LOG_DIR"
if [[ -n "$SERVER_ID" ]]; then
    echo "Server: pinned to ID $SERVER_ID"
else
    echo "Server: auto-selected each run"
fi
echo
echo "To remove: scripts/uninstall_launchd.sh"
