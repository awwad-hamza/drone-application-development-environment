#!/usr/bin/env python3
"""Configure the running SITL while connected and disarmed; never arms it."""
import json
from pathlib import Path
import time

import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from mavros_msgs.msg import State
from mavros_msgs.srv import ParamPull, ParamSetV2
from rcl_interfaces.msg import ParameterValue
from rcl_interfaces.srv import GetParameters

PARAMS = {
    "FLTMODE_CH": 5,
    "RC5_OPTION": 0,
    "FLTMODE1": 4,
    **{f"FLTMODE{i}": 2 for i in range(2, 7)},
}

rclpy.init()
node = rclpy.create_node("configure_sim_modes")
state = None
state_time = 0.0

def receive(msg):
    global state, state_time
    state, state_time = msg, time.monotonic()

qos = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
)
sub = node.create_subscription(State, "/mavros/state", receive, qos)

def check():
    if state is None or not state.connected or time.monotonic() - state_time > 3:
        raise RuntimeError("Fresh SITL connection required")
    if state.armed:
        raise RuntimeError("Disarm SITL before changing mode mappings")

def call(kind, name, request, timeout=90.0):
    client = node.create_client(kind, name)
    deadline = time.monotonic() + timeout
    while not client.service_is_ready():
        rclpy.spin_once(node, timeout_sec=0.1)
        check()
        if time.monotonic() > deadline:
            raise TimeoutError(f"Missing service: {name}")
    check()
    future = client.call_async(request)
    while not future.done():
        rclpy.spin_once(node, timeout_sec=0.1)
        check()
        if time.monotonic() > deadline:
            raise TimeoutError(name)
    result = future.result()
    node.destroy_client(client)
    return result

def number(value):
    if value.type == 2:
        return value.integer_value
    if value.type == 3:
        return value.double_value
    raise RuntimeError("Expected a numeric FCU parameter")

try:
    deadline = time.monotonic() + 40
    while state is None or not state.connected:
        rclpy.spin_once(node, timeout_sec=0.1)
        if time.monotonic() > deadline:
            raise TimeoutError("No SITL connection")
    check()

    print("Reading SITL parameters...", flush=True)
    result = call(
        ParamPull, "/mavros/param/pull",
        ParamPull.Request(force_pull=True),
    )
    if not result.success:
        raise RuntimeError("Parameter download failed")

    current = call(
        GetParameters, "/mavros/param/get_parameters",
        GetParameters.Request(names=list(PARAMS)),
    )
    previous = {
        key: number(value)
        for key, value in zip(PARAMS, current.values)
    }
    if len(previous) != len(PARAMS):
        raise RuntimeError("Incomplete parameter response")

    backup = Path(__file__).with_name("sim_modes.before.json")
    if not backup.exists():
        backup.write_text(json.dumps(previous, indent=2) + "\n")

    for name, value in PARAMS.items():
        result = call(
            ParamSetV2, "/mavros/param/set",
            ParamSetV2.Request(
                force_set=False,
                param_id=name,
                value=ParameterValue(type=2, integer_value=value),
            ),
        )
        if not result.success or number(result.value) != value:
            raise RuntimeError(
                f"Setting {name} failed; rerun setup while disarmed"
            )
        print(f"Confirmed {name} = {value}", flush=True)

    print("Ready: RC CH5 low = GUIDED; other positions = ALT_HOLD.")
finally:
    node.destroy_node()
    rclpy.try_shutdown()
