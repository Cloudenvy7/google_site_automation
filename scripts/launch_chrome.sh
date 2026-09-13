#!/usr/bin/env bash
# Launch the Chrome that the Site build path drives, with remote debugging on.
#
# RUN THIS YOURSELF, FROM YOUR OWN TERMINAL. Not from an agent, not over ssh.
#
# WHY (2026-08, recorded in the DEVLOG): Chrome started from a non-desktop shell
# cannot reach the system keyring. It then presents as signed out even though the
# profile holds a valid Google session -- and the failure looks like expired
# credentials, which sends you off re-authenticating something that was never
# broken. If DBUS_SESSION_BUS_ADDRESS is missing, you are in that situation.
#
# The profile is separate from your everyday Chrome, so this opens its own window
# and conflicts with nothing. Sign in once and it persists.

set -u
PORT="${CHROME_PORT:-9222}"
PROFILE="${CHROME_PROFILE:-$HOME/.chrome-debug-profile}"

for c in google-chrome google-chrome-stable chromium chromium-browser; do
  if command -v "$c" >/dev/null 2>&1; then CHROME="$c"; break; fi
done
if [ -z "${CHROME:-}" ]; then
  echo "No Chrome or Chromium on PATH. Install one, or set CHROME= yourself." >&2
  exit 1
fi

if curl -s --max-time 3 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
  echo "Already listening on $PORT:"
  curl -s "http://127.0.0.1:$PORT/json/version" | grep -o '"Browser": *"[^"]*"'
  echo "Nothing to do. Close that Chrome first if you want a fresh one."
  exit 0
fi

if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
  echo "WARNING: DBUS_SESSION_BUS_ADDRESS is not set."
  echo "  Chrome will not reach the keyring and will look signed out even if it"
  echo "  is not. Run this from a terminal inside your desktop session."
  echo
fi

echo "Launching $CHROME on port $PORT with profile $PROFILE"
nohup "$CHROME" \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$PROFILE" \
  --remote-allow-origins='*' \
  >/dev/null 2>&1 &

for _ in $(seq 1 20); do
  sleep 0.5
  if curl -s --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    echo "Up. Verify the account with:"
    echo "  python scripts/site_survey.py <site_id> <u_index>"
    echo "It prints the signed-in account -- check it is the right one before building."
    exit 0
  fi
done
echo "Chrome did not open a debug port within 10s. Check it is not already running" >&2
echo "against $PROFILE under a different flag set." >&2
exit 1
