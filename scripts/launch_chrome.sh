#!/usr/bin/env bash
# Launch the Chrome that the Site build path drives, with remote debugging on.
#
# RUN THIS YOURSELF, FROM YOUR OWN TERMINAL. Not from an agent, not over ssh.
#
# WHY (2026-08, recorded in the DEVLOG): Chrome started from a shell with no
# desktop session cannot reach the system keyring. It then presents as signed out
# even though the profile holds a valid Google session -- and the failure looks
# like expired credentials, which sends you off re-authenticating something that
# was never broken.
#
# The profile is separate from your everyday Chrome, so this opens its own window
# and conflicts with nothing. Sign in once and it persists.
#
# macOS SUPPORT (2026-09-18): the first version searched PATH for google-chrome,
# google-chrome-stable, chromium and chromium-browser -- NONE of which exist on a
# Mac, where Chrome ships as an .app bundle and is not on PATH at all. It failed
# at step one on the very machine it was written to make this portable for.
# Linux-only assumptions are the same defect class as the hard-coded home
# directories removed on 2026-09-13; this one hid in a shell script.

set -u
PORT="${CHROME_PORT:-9222}"
PROFILE="${CHROME_PROFILE:-$HOME/.chrome-debug-profile}"
OS="$(uname -s)"

# CHROME may be set explicitly; otherwise look in the right places for this OS.
if [ -z "${CHROME:-}" ]; then
  if [ "$OS" = "Darwin" ]; then
    for c in \
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
      "$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
      "/Applications/Chromium.app/Contents/MacOS/Chromium" \
      "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary"
    do
      [ -x "$c" ] && { CHROME="$c"; break; }
    done
  else
    for c in google-chrome google-chrome-stable chromium chromium-browser; do
      command -v "$c" >/dev/null 2>&1 && { CHROME="$c"; break; }
    done
  fi
fi

if [ -z "${CHROME:-}" ]; then
  echo "No Chrome or Chromium found." >&2
  if [ "$OS" = "Darwin" ]; then
    echo "  Looked in /Applications and ~/Applications. Install Chrome, or set:" >&2
    echo '    export CHROME="/path/to/Google Chrome"' >&2
  else
    echo "  Nothing on PATH. Install Chrome, or set CHROME= yourself." >&2
  fi
  exit 1
fi

if curl -s --max-time 3 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
  echo "Already listening on $PORT:"
  curl -s "http://127.0.0.1:$PORT/json/version" | grep -o '"Browser": *"[^"]*"'
  echo "Nothing to do. Quit that Chrome first if you want a fresh one."
  exit 0
fi

# The keyring warning is Linux-specific. On macOS the Keychain is reached
# normally from a Terminal.app shell, and printing a DBUS warning there would be
# a false alarm about a variable that does not exist on the platform.
if [ "$OS" != "Darwin" ] && [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
  echo "WARNING: DBUS_SESSION_BUS_ADDRESS is not set."
  echo "  Chrome will not reach the keyring and will look signed out even if it"
  echo "  is not. Run this from a terminal inside your desktop session."
  echo
fi

echo "Launching Chrome on port $PORT"
echo "  binary:  $CHROME"
echo "  profile: $PROFILE"
nohup "$CHROME" \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$PROFILE" \
  --remote-allow-origins='*' \
  >/dev/null 2>&1 &

for _ in $(seq 1 30); do
  sleep 0.5
  if curl -s --max-time 2 "http://127.0.0.1:$PORT/json/version" >/dev/null 2>&1; then
    echo
    echo "Up. Sign in to the Google account that can edit the Site, then verify:"
    echo "  python scripts/site_survey.py <site_id> <u_index>"
    echo "It prints the signed-in account -- check it is the right one BEFORE building."
    exit 0
  fi
done
echo "Chrome did not open a debug port within 15s." >&2
echo "Check it is not already running against $PROFILE under a different flag set." >&2
if [ "$OS" = "Darwin" ]; then
  echo "On macOS, quit Chrome fully (Cmd-Q) first -- a running instance ignores" >&2
  echo "the debugging flag and the new invocation just opens a window in it." >&2
fi
exit 1
