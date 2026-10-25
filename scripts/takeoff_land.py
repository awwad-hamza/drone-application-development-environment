#!/usr/bin/env python3
import argparse
import math
from pilot_takeover import PilotTakeover, PilotTakeoverGuard
import time

import rclpy
from rclpy.qos import (
    QoSProfile, ReliabilityPolicy, DurabilityPolicy,
)
from mavros_msgs.msg import State
from mavros_msgs.srv import SetMode, CommandBool, CommandTOL, StreamRate
from std_msgs.msg import Float64

TARGET_ALTITUDE = 5.0
parser = argparse.ArgumentParser()
parser.add_argument("--hover-seconds", type=float, default=5.0)
HOVER_SECONDS = parser.parse_args().hover_seconds
if not math.isfinite(HOVER_SECONDS) or HOVER_SECONDS < 0:
    parser.error("--hover-seconds must be finite and non-negative")

rclpy.init()
node = rclpy.create_node("takeoff_hover_land")
guard = PilotTakeoverGuard(node)

state = None
altitude = None
state_time = 0.0
altitude_time = 0.0
arm_attempted = False

# Receive fresh telemetry rather than historical state samples.
qos = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
)


def receive_state(msg):
    global state, state_time
    state = msg
    guard.observe_state(msg)
    state_time = time.monotonic()


def receive_altitude(msg):
    global altitude, altitude_time
    if math.isfinite(msg.data):
        altitude = msg.data
        altitude_time = time.monotonic()


node.create_subscription(State, "/mavros/state", receive_state, qos)
node.create_subscription(
    Float64, "/mavros/global_position/rel_alt",
    receive_altitude, qos,
)

mode_client = node.create_client(SetMode, "/mavros/set_mode")
arm_client = node.create_client(CommandBool, "/mavros/cmd/arming")
takeoff_client = node.create_client(CommandTOL, "/mavros/cmd/takeoff")


def telemetry_ok():
    now = time.monotonic()
    return (
        state is not None
        and state.connected
        and altitude is not None
        and now - state_time < 3.0
        and now - altitude_time < 3.0
    )


def wait_for(condition, timeout, description, check_link=False):
    deadline = time.monotonic() + timeout
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.1)
        guard.check()
        if check_link and not telemetry_ok():
            raise RuntimeError("Telemetry stopped or connection was lost")
        if condition():
            return
        if time.monotonic() >= deadline:
            raise TimeoutError(description)
    raise RuntimeError("ROS stopped")


def call(client, request):
    wait_for(client.service_is_ready, 10.0,
             f"Service unavailable: {client.srv_name}")
    guard.check()

    future = client.call_async(request)
    wait_for(future.done, 15.0, f"Service timeout: {client.srv_name}")
    response = future.result()
    if response is None:
        raise RuntimeError(f"No response: {client.srv_name}")
    return response


def set_mode(name):
    if name == "LAND":
        guard.expect_land()
    return call(
        mode_client,
        SetMode.Request(base_mode=0, custom_mode=name),
    )


try:
    print("Waiting for a fresh autopilot connection...", flush=True)
    wait_for(
        lambda: (
            state is not None
            and state.connected
            and time.monotonic() - state_time < 3.0
        ),
        40.0, "No fresh connected state received",
    )

    if state.armed:
        raise RuntimeError("Already armed; start while disarmed")

    print("Requesting position/altitude telemetry at 5 Hz...", flush=True)
    stream_client = node.create_client(
        StreamRate, "/mavros/set_stream_rate"
    )
    call(
        stream_client,
        StreamRate.Request(stream_id=6, message_rate=5, on_off=True),
    )

    print("Requesting RC telemetry at 10 Hz...", flush=True)
    call(stream_client, StreamRate.Request(
        stream_id=3, message_rate=10, on_off=True))

    print("Waiting for fresh altitude...", flush=True)
    wait_for(
        telemetry_ok, 30.0,
        "Altitude telemetry missing or connection lost. "
        "Check /mavros/global_position/rel_alt and /mavros/state",
    )
    print(f"Telemetry ready. Altitude: {altitude:.2f} m", flush=True)

    if state.armed:
        raise RuntimeError("Already armed; start this script while disarmed")

    print("Select 1: GUIDED in drone-rc...", flush=True)
    wait_for(
        guard.ready, 60.0,
        "No fresh RC CH5 GUIDED selection and confirmed GUIDED mode",
        check_link=True,
    )
    guard.begin()

    print("Arming...", flush=True)
    arm_attempted = True
    response = call(arm_client, CommandBool.Request(value=True))
    print(f"Arm response: {response}", flush=True)
    if not response.success:
        raise RuntimeError(f"Arming rejected: {response}")
    wait_for(
        lambda: state.armed and state.mode == "GUIDED",
        10.0, "Arming was not confirmed", check_link=True,
    )

    print("Taking off to 5 metres...", flush=True)
    response = call(
        takeoff_client,
        CommandTOL.Request(
            min_pitch=0.0, yaw=0.0,
            latitude=0.0, longitude=0.0,
            altitude=TARGET_ALTITUDE,
        ),
    )
    if not response.success:
        raise RuntimeError(f"Takeoff failed: {response}")

    wait_for(
        lambda: abs(altitude - TARGET_ALTITUDE) <= 0.3,
        60.0, "Target altitude was not reached", check_link=True,
    )

    print(f"At {altitude:.2f} m. Holding for {HOVER_SECONDS:g} seconds...", flush=True)
    hover_end = time.monotonic() + HOVER_SECONDS
    while time.monotonic() < hover_end:
        rclpy.spin_once(node, timeout_sec=0.1)
        guard.check()
        if not telemetry_ok() or not state.armed or state.mode != "GUIDED":
            raise RuntimeError("Connection, arming, or flight mode changed")

    print("Landing...", flush=True)
    set_mode("LAND")
    wait_for(
        lambda: not state.armed,
        90.0, "Landing/disarming was not confirmed", check_link=True,
    )
    print("Finished: landed and disarmed.", flush=True)

except PilotTakeover as error:
    print(
        f"Pilot takeover: {error}. Autonomy cancelled; no further commands.",
        flush=True,
    )
    raise SystemExit(0)

except (Exception, KeyboardInterrupt) as error:
    print(f"Stopped: {error}", flush=True)
    if arm_attempted and state is not None and state.armed and rclpy.ok():
        try:
            guard.check()
            print("Requesting LAND as a fallback...", flush=True)
            set_mode("LAND")
        except Exception as landing_error:
            print(f"Fallback LAND skipped or failed: {landing_error}", flush=True)
    raise SystemExit(1)

finally:
    node.destroy_node()
    rclpy.try_shutdown()
