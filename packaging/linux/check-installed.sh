#!/bin/sh
# Run as a normal desktop user after installing the DEB or RPM.
set -eu
app_id=io.github.boxu_pku.MULTI1Dvisual
desktop="/usr/share/applications/$app_id.desktop"
desktop-file-validate "$desktop"
appstreamcli validate --no-net "/usr/share/metainfo/$app_id.metainfo.xml"
test -x /usr/bin/multi1dvisual
cmp /usr/share/multi1dvisual/resources/icons/multi1dvisual.png \
    "/usr/share/icons/hicolor/512x512/apps/$app_id.png"

# Launch the real menu entry from outside the source tree, with a fresh profile.
profile=$(mktemp -d)
trap 'rm -rf -- "$profile"' EXIT
HOME="$profile" XDG_CONFIG_HOME="$profile/config" XDG_CACHE_HOME="$profile/cache" QT_QPA_PLATFORM=xcb \
    xvfb-run -a dbus-run-session -- sh -eu -c '
        cd /
        gio launch "$1"
        window=$(timeout 90 xdotool search --sync --onlyvisible --class "^multi1dvisual$" | head -n 1)
        test -n "$window"
        xdotool getwindowname "$window"
        xprop -id "$window" -len 32 -f _NET_WM_ICON 32c _NET_WM_ICON | grep -Eq "= [1-9][0-9]*, [1-9][0-9]*"
        test -d "$HOME/.MULTI1D可视化工具/logs"
        pid=$(xdotool getwindowpid "$window")
        xdotool windowfocus --sync "$window" key ctrl+q
        timeout 10 tail --pid="$pid" -f /dev/null
    ' sh "$desktop"
