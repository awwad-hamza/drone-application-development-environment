#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${DISPLAY:?Run this script in your Linux graphical desktop terminal}"
command -v xauth >/dev/null || { echo 'Install xauth on the HOST first (Ubuntu/Debian: sudo apt-get install xauth).'; exit 1; }
cookies=$(xauth nlist "$DISPLAY")
if [[ -z "$cookies" ]]; then
    echo 'No X11 cookie found. Check DISPLAY and XAUTHORITY in your desktop terminal.' >&2
    exit 1
fi
tmp_cookie=$(mktemp "$PWD/.Xauthority.XXXXXX")
trap 'rm -f "$tmp_cookie"' EXIT
printf '%s\n' "$cookies" | sed 's/^..../ffff/' | xauth -f "$tmp_cookie" nmerge -
chmod 600 "$tmp_cookie"
# Keep an existing mounted file's inode on subsequent runs.
cat "$tmp_cookie" > .Xauthority
chmod 600 .Xauthority
printf 'DISPLAY=%s\n' "$DISPLAY" > .env
echo 'Display ready. Open the project in VS Code and rebuild the dev container.'
