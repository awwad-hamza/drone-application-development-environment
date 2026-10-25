# Shared shortcuts for the X650 development environment.

X650_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

drone-arm() {
    ros2 service call /mavros/set_mode mavros_msgs/srv/SetMode \
      "{base_mode: 0, custom_mode: 'ALT_HOLD'}"
    ros2 service call /mavros/cmd/arming mavros_msgs/srv/CommandBool \
      "{value: true}"
}

drone-status() {
    ros2 topic echo /mavros/state \
      --qos-durability volatile --qos-depth 1
}

drone-rc() {
    python3 "$X650_REPO_ROOT/scripts/keyboard_rc.py" "$@"
}

drone-takeoff-land() {
    if (( $# > 1 )); then
        printf 'Usage: drone-takeoff-land [hover-seconds]\n' >&2
        return 2
    fi

    python3 "$X650_REPO_ROOT/scripts/takeoff_land.py" \
        --hover-seconds "${1:-5}"
}
